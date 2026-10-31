"""Staging için anonim tenant kopyası (S20, ADR-0041).

Staging "prod'a denk" olmalı (aynı şema, aynı hacim, aynı dağılım) ama gerçek kişisel veri
taşımamalı (KVKK; envanter: ``docs/uyum/kisisel-veri-envanteri.md``). Akış:

1. Prod tenant'ın yedeği alınır (``yedek.tenant_yedekle``).
2. Staging'de adı ``staging`` içeren bir hedef tenant'a geri yüklenir (``tenant_geri_yukle``).
3. Bu modül hedef şemadaki kişisel veriyi **yerinde ve geri dönüşsüz** maskeler.

Maskeleme deterministiktir (satır kimliğinden üretilir): aynı kayıt her koşuda aynı takma adı
alır, kayıtlar arası ilişki (kim kimin yöneticisi, hangi kullanıcı hangi işlemi yaptı) korunur.
Staging'in dışarıya konuşmaması da bu adımın işidir: webhook abonelikleri kapatılır, bekleyen
outbox olayları gönderilmiş sayılır, prod API anahtarları ve oturumları silinir.

**Kapsam dışı (bilinen artık risk):** operasyonel serbest metin alanları (malzeme/iş emri
açıklamaları, duyuru içeriği) taranmaz; envanterde kişisel veri kategorisi olarak geçen alanlar
ve iş emri yorumları maskelenir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import asyncpg

from app.core.db.tenancy import sema_adi
from app.core.security.parola import parola_ozetle

KULLANILAMAZ_PAROLA = "!anonim"  # argon2 özeti değil → parola_dogrula her zaman False


class AnonimHatasi(RuntimeError):
    pass


@dataclass
class AnonimRaporu:
    sema: str
    guncellenen: dict[str, int] = field(default_factory=dict)
    silinen: dict[str, int] = field(default_factory=dict)
    yonetici: str | None = None


def _sayi(durum: str) -> int:
    """asyncpg komut etiketi ("UPDATE 12", "DELETE 3") → etkilenen satır."""
    return int(durum.rsplit(" ", 1)[-1])


# (tablo, SET ifadesi) — ``id`` her tabloda birincil anahtardır.
_MASKELER: list[tuple[str, str]] = [
    (
        "kullanici",
        "eposta = 'kullanici-' || id || '@anonim.invalid', ad_soyad = 'Kullanıcı ' || id, "
        f"parola_ozet = '{KULLANILAMAZ_PAROLA}', totp_sirri = NULL, iki_asama_aktif = false",
    ),
    (
        "personel",
        "ad = 'Personel', soyad = id::text, "
        # 11 hane, '9' ile başlar ve sağlama toplamı tutmaz → gerçek bir TCKN olamaz.
        "tc_kimlik_no = '9' || lpad((id % 10000000000)::text, 10, '0'), "
        "dogum_tarihi = NULL, telefon = '', eposta = 'personel-' || id || '@anonim.invalid'",
    ),
    (
        "ortaklar",
        "ad_soyad = 'Kişi ' || id, eposta = 'kisi-' || id || '@anonim.invalid', "
        "telefon = '', aciklama = ''",
    ),
    (
        "firmalar",
        # Şahıs firmasında unvan = kişinin adı, vergi no = TCKN olabilir.
        "ad = 'Firma ' || id, eposta = 'firma-' || id || '@anonim.invalid', telefon = '', "
        "adres = '', vergi_no = lpad(id::text, 10, '0'), web_sitesi = ''",
    ),
    ("consent_kayitlari", "ip_adresi = NULL"),
    ("is_kazalari", "aciklama = '[anonimleştirildi]'"),
    ("izin_talepleri", "aciklama = '', red_nedeni = ''"),
    ("fazla_mesailer", "aciklama = ''"),
    ("is_emri_yorumlari", "metin = '[anonimleştirildi]', yazan_eposta = 'anonim@anonim.invalid'"),
    ("bildirimler", "govde = '', veri = '{}'::jsonb"),
    # Staging dışarı konuşmaz: müşteri uçlarına webhook gitmez.
    (
        "webhook_abonelikleri",
        "aktif = false, url = 'https://staging.invalid/webhook/' || id, "
        "gizli_anahtar = 'staging-' || id",
    ),
]
# Denetim izi ekleme-yalnız (``denetim_izi_koru`` tetikleyicisi); staging kopyasında maskelemek
# için tetikleyici bu işlem süresince kapatılır.
_DENETIM_MASKESI = "kullanici_eposta = 'anonim@anonim.invalid', ip_adresi = NULL, detay = NULL"
_SILINECEKLER = ["oturumlar", "kurtarma_kodlari", "api_anahtarlari", "kvkk_ihraclari"]


async def _tablo_var(conn: asyncpg.Connection, sema: str, tablo: str) -> bool:
    return bool(
        await conn.fetchval(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = $1 AND table_name = $2",
            sema,
            tablo,
        )
    )


async def tenant_anonimlestir(
    dsn: str,
    slug: str,
    *,
    yonetici: tuple[str, str] | None = None,
) -> AnonimRaporu:
    """``tenant_<slug>`` şemasındaki kişisel veriyi maskeler (geri dönüşsüz).

    Yalnız adında ``staging`` geçen tenant'larda çalışır: prod şemasına yanlışlıkla
    uygulanması veri kaybıdır. ``yonetici=(eposta, parola)`` verilirse en eski yönetici
    hesabı bu kimlikle açılır (staging'e giriş için); diğer herkesin parolası kullanılamaz.
    """
    if "staging" not in slug:
        raise AnonimHatasi(f"Anonimleştirme yalnız staging tenant'ında çalışır: {slug!r}")
    sema = sema_adi(slug)
    rapor = AnonimRaporu(sema=sema)
    conn = await asyncpg.connect(dsn)
    try:
        async with conn.transaction():
            for tablo, ifade in _MASKELER:
                if await _tablo_var(conn, sema, tablo):
                    rapor.guncellenen[tablo] = _sayi(
                        await conn.execute(f'UPDATE "{sema}"."{tablo}" SET {ifade}')
                    )
            if await _tablo_var(conn, sema, "denetim_izi"):
                await conn.execute(f'ALTER TABLE "{sema}".denetim_izi DISABLE TRIGGER USER')
                rapor.guncellenen["denetim_izi"] = _sayi(
                    await conn.execute(f'UPDATE "{sema}".denetim_izi SET {_DENETIM_MASKESI}')
                )
                await conn.execute(f'ALTER TABLE "{sema}".denetim_izi ENABLE TRIGGER USER')
            for tablo in _SILINECEKLER:
                if await _tablo_var(conn, sema, tablo):
                    rapor.silinen[tablo] = _sayi(
                        await conn.execute(f'DELETE FROM "{sema}"."{tablo}"')
                    )
            if await _tablo_var(conn, sema, "giden_olaylar"):
                # Bekleyen olaylar staging relay'inden prod'un abonelerine gitmesin.
                rapor.guncellenen["giden_olaylar"] = _sayi(
                    await conn.execute(
                        f"UPDATE \"{sema}\".giden_olaylar SET durum = 'gonderildi' "
                        "WHERE durum <> 'gonderildi'"
                    )
                )
            if yonetici is not None:
                eposta, parola = yonetici
                kimlik = await conn.fetchval(
                    f"""SELECT k.id FROM "{sema}".kullanici k
                        JOIN "{sema}".kullanici_rol kr ON kr.kullanici_id = k.id
                        JOIN "{sema}".rol r ON r.id = kr.rol_id
                        WHERE r.ad = 'admin' ORDER BY k.id LIMIT 1"""
                )
                if kimlik is None:
                    raise AnonimHatasi("Kopyada yönetici rolüne sahip kullanıcı yok")
                await conn.execute(
                    f'UPDATE "{sema}".kullanici SET eposta = $1, parola_ozet = $2, aktif = true '
                    "WHERE id = $3",
                    eposta,
                    parola_ozetle(parola),
                    kimlik,
                )
                rapor.yonetici = eposta
    finally:
        await conn.close()
    return rapor
