"""S18 webhook relay testleri — fan-out, imzalı teslimat, backoff/terminal, izolasyon.

HTTP katmanı ``httpx.MockTransport`` ile taklit edilir: alıcı, imzayı abonelik gizli
anahtarıyla ham gövde üzerinden doğrular (alıcı tarafın gerçek reçetesi).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
import pytest_asyncio
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.olaylar import GidenOlay, olay_yayinla
from app.modules.entegrasyon.imza import IMZA_BASLIGI, OLAY_BASLIGI, TESLIMAT_BASLIGI, imza_dogrula
from app.modules.entegrasyon.models import WebhookAboneligi, WebhookTeslimati
from app.modules.entegrasyon.relay import tenant_relay_turu

GIZLI_A = "whs_relay-test-anahtari-a"
GIZLI_B = "whs_relay-test-anahtari-b"

type _SM = async_sessionmaker[AsyncSession]


@pytest_asyncio.fixture
async def sm(test_engine: AsyncEngine) -> _SM:
    return async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def temiz(sm: _SM) -> AsyncIterator[_SM]:
    """Webhook tablolarını boşaltır, diğer testlerden kalan bekleyen olayları tüketir."""
    for slug in ("alfa", "beta"):
        async with sm() as s, s.begin():
            await search_path_ayarla(s, slug)
            await s.execute(delete(WebhookTeslimati))
            await s.execute(delete(WebhookAboneligi))
            await s.execute(
                update(GidenOlay).where(GidenOlay.durum == "beklemede").values(durum="gonderildi")
            )
    yield sm


async def _abonelik_ekle(sm: _SM, slug: str, **alanlar: object) -> int:
    async with sm() as s, s.begin():
        await search_path_ayarla(s, slug)
        a = WebhookAboneligi(**alanlar)  # type: ignore[arg-type]
        s.add(a)
        await s.flush()
        return a.id


async def _olay_ekle(sm: _SM, slug: str, *, olay_turu: str, govde: dict) -> int:
    async with sm() as s, s.begin():
        await search_path_ayarla(s, slug)
        olay = await olay_yayinla(s, olay_turu=olay_turu, govde=govde)
        return olay.id


async def _teslimatlar(sm: _SM, slug: str) -> list[WebhookTeslimati]:
    async with sm() as s:
        await search_path_ayarla(s, slug)
        sonuc = await s.execute(select(WebhookTeslimati).order_by(WebhookTeslimati.id))
        return list(sonuc.scalars())


def _imza_zamani(baslik: str) -> int:
    return int(dict(p.split("=", 1) for p in baslik.split(","))["t"])


async def test_fanout_ve_imzali_teslimat(temiz: _SM) -> None:
    sm = temiz
    await _abonelik_ekle(
        sm,
        "alfa",
        ad="stok-alicisi",
        url="https://alici-a.test/hook",
        gizli_anahtar=GIZLI_A,
        olay_turleri=["stok.kritik"],
    )
    await _abonelik_ekle(
        sm,
        "alfa",
        ad="hepsi-alicisi",
        url="https://alici-b.test/hook",
        gizli_anahtar=GIZLI_B,
        olay_turleri=[],  # boş = tüm olaylar
    )
    olay_id = await _olay_ekle(sm, "alfa", olay_turu="stok.kritik", govde={"malzeme_id": 7})

    alinan: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        alinan.append(request)
        # Alıcı reçetesi: ham gövde + imza başlığı + abonelik anahtarı ile doğrula.
        gizli = GIZLI_A if request.url.host == "alici-a.test" else GIZLI_B
        baslik = request.headers[IMZA_BASLIGI]
        assert imza_dogrula(gizli, baslik, request.content, simdi=_imza_zamani(baslik))
        return httpx.Response(200, text="ok")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        fanout, islenen = await tenant_relay_turu(sm, "alfa", http=http)

    assert fanout == 2 and islenen == 2
    assert len(alinan) == 2
    for istek in alinan:
        assert istek.headers[OLAY_BASLIGI] == "stok.kritik"
        assert istek.headers[TESLIMAT_BASLIGI]  # tüketici idempotency anahtarı
        import json

        zarf = json.loads(istek.content)
        assert zarf["surum"] == "v1"
        assert zarf["olay_turu"] == "stok.kritik"
        assert zarf["veri"] == {"malzeme_id": 7}

    teslimatlar = await _teslimatlar(sm, "alfa")
    assert all(t.durum == "basarili" and t.yanit_kodu == 200 for t in teslimatlar)
    assert all(t.deneme_sayisi == 1 for t in teslimatlar)

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        olay = (await s.execute(select(GidenOlay).where(GidenOlay.id == olay_id))).scalar_one()
        assert olay.durum == "gonderildi"
        assert olay.gonderim_tarihi is not None


async def test_eslesmeyen_tur_ve_pasif_abonelik_teslimat_uretmez(temiz: _SM) -> None:
    sm = temiz
    await _abonelik_ekle(
        sm,
        "alfa",
        ad="yalniz-isemri",
        url="https://alici.test/hook",
        gizli_anahtar=GIZLI_A,
        olay_turleri=["is_emri.kapandi"],
    )
    await _abonelik_ekle(
        sm,
        "alfa",
        ad="pasif",
        url="https://pasif.test/hook",
        gizli_anahtar=GIZLI_B,
        olay_turleri=[],
        aktif=False,
    )
    olay_id = await _olay_ekle(sm, "alfa", olay_turu="stok.kritik", govde={"malzeme_id": 1})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200))
    ) as http:
        fanout, islenen = await tenant_relay_turu(sm, "alfa", http=http)

    assert fanout == 0 and islenen == 0
    assert await _teslimatlar(sm, "alfa") == []
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        olay = (await s.execute(select(GidenOlay).where(GidenOlay.id == olay_id))).scalar_one()
        assert olay.durum == "gonderildi"  # abone yok ama olay tüketildi


async def test_hata_yaniti_backoff_ve_vade(temiz: _SM) -> None:
    sm = temiz
    await _abonelik_ekle(
        sm,
        "alfa",
        ad="bozuk-alici",
        url="https://bozuk.test/hook",
        gizli_anahtar=GIZLI_A,
        olay_turleri=[],
    )
    await _olay_ekle(sm, "alfa", olay_turu="ariza.olustu", govde={"makine_id": 3})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(500, text="patladı"))
    ) as http:
        await tenant_relay_turu(sm, "alfa", http=http)

        (t,) = await _teslimatlar(sm, "alfa")
        assert t.durum == "yeniden_denenecek"
        assert t.deneme_sayisi == 1
        assert t.yanit_kodu == 500 and "patladı" in t.yanit_ozeti
        assert t.sonraki_deneme_tarihi > datetime.now(UTC) + timedelta(seconds=30)  # ~60 sn

        # Vadesi gelmeden ikinci tur: satıra DOKUNULMAZ (retry korunur).
        await tenant_relay_turu(sm, "alfa", http=http)
        (t2,) = await _teslimatlar(sm, "alfa")
        assert t2.deneme_sayisi == 1

        # Vadeyi geçmişe çek → ikinci deneme yapılır, backoff büyür (~300 sn).
        async with sm() as s, s.begin():
            await search_path_ayarla(s, "alfa")
            await s.execute(
                update(WebhookTeslimati).values(
                    sonraki_deneme_tarihi=datetime.now(UTC) - timedelta(seconds=1)
                )
            )
        await tenant_relay_turu(sm, "alfa", http=http)
        (t3,) = await _teslimatlar(sm, "alfa")
        assert t3.deneme_sayisi == 2
        assert t3.durum == "yeniden_denenecek"
        assert t3.sonraki_deneme_tarihi > datetime.now(UTC) + timedelta(seconds=200)


async def test_baglanti_hatasi_da_backoff(temiz: _SM) -> None:
    sm = temiz
    await _abonelik_ekle(
        sm,
        "alfa",
        ad="ulasilmaz",
        url="https://ulasilmaz.test/hook",
        gizli_anahtar=GIZLI_A,
        olay_turleri=[],
    )
    await _olay_ekle(sm, "alfa", olay_turu="isg.kaza", govde={"kaza_id": 1})

    def patlat(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("bağlanamadı", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(patlat)) as http:
        await tenant_relay_turu(sm, "alfa", http=http)

    (t,) = await _teslimatlar(sm, "alfa")
    assert t.durum == "yeniden_denenecek"
    assert t.yanit_kodu is None
    assert "bağlantı hatası" in t.yanit_ozeti


async def test_terminal_basarisiz_ve_manuel_yeniden_dene(
    temiz: _SM, kurulu_istemci: object
) -> None:
    from httpx import AsyncClient

    from tests.conftest import ALFA
    from tests.test_s16_entitlement import _giris

    assert isinstance(kurulu_istemci, AsyncClient)
    sm = temiz
    await _abonelik_ekle(
        sm,
        "alfa",
        ad="son-sans",
        url="https://sonsans.test/hook",
        gizli_anahtar=GIZLI_A,
        olay_turleri=[],
    )
    await _olay_ekle(sm, "alfa", olay_turu="oee.dustu", govde={"makine_id": 9})

    # 5 deneme tükenmiş gibi kur → sıradaki deneme (6.) son şans.
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(503))
    ) as bozuk_http:
        await tenant_relay_turu(sm, "alfa", http=bozuk_http)
        async with sm() as s, s.begin():
            await search_path_ayarla(s, "alfa")
            await s.execute(
                update(WebhookTeslimati).values(
                    deneme_sayisi=5,
                    sonraki_deneme_tarihi=datetime.now(UTC) - timedelta(seconds=1),
                )
            )
        await tenant_relay_turu(sm, "alfa", http=bozuk_http)

    (t,) = await _teslimatlar(sm, "alfa")
    assert t.durum == "basarisiz"  # terminal
    assert t.deneme_sayisi == 6

    # Terminal satır vadesi geçmiş olsa bile relay artık DOKUNMAZ.
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200))
    ) as http:
        await tenant_relay_turu(sm, "alfa", http=http)
        (t2,) = await _teslimatlar(sm, "alfa")
        assert t2.durum == "basarisiz" and t2.deneme_sayisi == 6

        # Manuel yeniden-dene (API) → bir sonraki turda bir deneme daha → başarılı.
        h = await _giris(kurulu_istemci, ALFA)
        r = await kurulu_istemci.post(
            f"/api/v1/webhooklar/teslimatlar/{t2.id}/yeniden-dene", headers=h
        )
        assert r.status_code == 200, r.text

        await tenant_relay_turu(sm, "alfa", http=http)
        (t3,) = await _teslimatlar(sm, "alfa")
        assert t3.durum == "basarili"
        assert t3.deneme_sayisi == 7


async def test_tenant_izolasyonu_relay(temiz: _SM) -> None:
    sm = temiz
    # Abonelik yalnız BETA'da; olay yalnız ALFA'da.
    await _abonelik_ekle(
        sm,
        "beta",
        ad="beta-alicisi",
        url="https://beta.test/hook",
        gizli_anahtar=GIZLI_B,
        olay_turleri=[],
    )
    await _olay_ekle(sm, "alfa", olay_turu="stok.kritik", govde={"malzeme_id": 42})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200))
    ) as http:
        await tenant_relay_turu(sm, "alfa", http=http)
        await tenant_relay_turu(sm, "beta", http=http)

    # Alfa'nın olayı beta'nın aboneliğine AKMAZ; iki şemada da teslimat yok.
    assert await _teslimatlar(sm, "alfa") == []
    assert await _teslimatlar(sm, "beta") == []
