"""Tedarikçi performans skoru (S-VB / ADR-0021) — saf fonksiyon, 0–100, birim testli.

``oee_hesapla`` tarzı: hesap çekirdeği DB'siz saf fonksiyondur; sinyaller ayrı
toplanır. Skor **dürüsttür** — sinyali olmayan bileşen nötr (0.5) sayılır ve
gerekçede "yetersiz veri" işaretlenir; bölme/NaN hatası imkânsızdır.

Bileşenler (ağırlıklar sabit, toplam 100; S25-B'de teslim bileşeni eklendi):

    skor = 30 * kalite_gecme_orani   # firmanın malzemelerine bağlı kalite kontrolleri
         + 20 * sozlesme_uyumu        # sözleşmelerin sağlıklı (feshedilmemiş) oranı
         + 20 * talep_cozum_orani     # firmayla ilişkili taleplerin çözülme oranı
         + 30 * zamaninda_teslim      # beklenen tarihli PO teslimlerinin zamanında oranı

``zamaninda_teslim`` sinyal yoksa ``None`` döner, formülde nötr (0.5) sayılır ve
``yetersiz_veri``ye ``"teslim"`` olarak düşer. Ölçü teslim (irsaliye) başınadır, iade sayılmaz.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.kalite.models import KaliteKontrol
from app.modules.sozlesme.models import Sozlesme
from app.modules.stok.models import Malzeme, SatinalmaSiparisi, TeslimAlma
from app.modules.talep.models import Talep

# Sinyalsiz bileşenin nötr değeri (taraf tutmaz; gerekçede işaretlenir).
NOTR = 0.5


@dataclass(frozen=True)
class SkorSinyalleri:
    """DB'den toplanan ham sayımlar (saf çekirdeğin girdisi)."""

    kalite_gecen: int = 0
    kalite_toplam: int = 0
    sozlesme_saglikli: int = 0
    sozlesme_toplam: int = 0
    talep_cozulen: int = 0
    talep_toplam: int = 0
    teslim_zamaninda: int = 0
    teslim_toplam: int = 0


@dataclass(frozen=True)
class SkorDetay:
    """0–100 toplam skor + bileşen kırılımı + dürüstlük notları."""

    skor: float
    kalite_gecme_orani: float
    sozlesme_uyumu: float
    talep_cozum_orani: float
    zamaninda_teslim: float | None  # PO teslimi yoksa None (formülde nötr)
    yetersiz_veri: list[str]


def _oran(pay: int, payda: int) -> tuple[float, bool]:
    """(oran, sinyal_var_mi) — payda 0 ise nötr değer ve sinyalsiz işareti."""
    if payda <= 0:
        return NOTR, False
    return pay / payda, True


def tedarikci_skoru(sinyaller: SkorSinyalleri) -> SkorDetay:
    """Ham sayımlardan deterministik skor üretir (saf, sınır 0–100 garantili)."""
    kalite, kalite_var = _oran(sinyaller.kalite_gecen, sinyaller.kalite_toplam)
    sozlesme, sozlesme_var = _oran(sinyaller.sozlesme_saglikli, sinyaller.sozlesme_toplam)
    talep, talep_var = _oran(sinyaller.talep_cozulen, sinyaller.talep_toplam)
    teslim, teslim_var = _oran(sinyaller.teslim_zamaninda, sinyaller.teslim_toplam)

    yetersiz = [
        ad
        for ad, var in (
            ("kalite", kalite_var),
            ("sozlesme", sozlesme_var),
            ("talep", talep_var),
            ("teslim", teslim_var),
        )
        if not var
    ]
    skor = round(30 * kalite + 20 * sozlesme + 20 * talep + 30 * teslim, 1)
    skor = min(max(skor, 0.0), 100.0)
    return SkorDetay(
        skor=skor,
        kalite_gecme_orani=round(kalite, 4),
        sozlesme_uyumu=round(sozlesme, 4),
        talep_cozum_orani=round(talep, 4),
        zamaninda_teslim=round(teslim, 4) if teslim_var else None,
        yetersiz_veri=yetersiz,
    )


async def sinyal_topla(db: AsyncSession, firma_id: int) -> SkorSinyalleri:
    """Firmanın skor sinyallerini toplar (tenant izole — aktif ``search_path``).

    Kalite bağlantısı iki yoldan kurulur: kontrolün doğrudan ``malzeme_id``'si veya
    malzemenin ``tedarikci_firma_id``'si bu firmaysa sayılır.
    """
    kalite_kosul = KaliteKontrol.malzeme_id.in_(
        select(Malzeme.id).where(Malzeme.tedarikci_firma_id == firma_id)
    )
    kalite_toplam = (
        await db.execute(select(func.count()).select_from(KaliteKontrol).where(kalite_kosul))
    ).scalar_one()
    kalite_gecen = (
        await db.execute(
            select(func.count())
            .select_from(KaliteKontrol)
            .where(kalite_kosul, KaliteKontrol.sonuc == "gecti")
        )
    ).scalar_one()

    sozlesme_toplam = (
        await db.execute(
            select(func.count()).select_from(Sozlesme).where(Sozlesme.firma_id == firma_id)
        )
    ).scalar_one()
    # Sağlıklı = feshedilmemiş/iptal edilmemiş (aktif, taslak ve normal sonlanan dahil).
    sozlesme_saglikli = (
        await db.execute(
            select(func.count())
            .select_from(Sozlesme)
            .where(Sozlesme.firma_id == firma_id, Sozlesme.durum.notin_(("feshedildi", "iptal")))
        )
    ).scalar_one()

    talep_toplam = (
        await db.execute(
            select(func.count())
            .select_from(Talep)
            .where(Talep.firma_id == firma_id, Talep.durum != "iptal")
        )
    ).scalar_one()
    talep_cozulen = (
        await db.execute(
            select(func.count())
            .select_from(Talep)
            .where(Talep.firma_id == firma_id, Talep.durum.in_(("cozuldu", "kapandi")))
        )
    ).scalar_one()

    teslim_kosul = (
        TeslimAlma.tur == "teslim",
        TeslimAlma.zamaninda.is_not(None),
        TeslimAlma.siparis_id.in_(
            select(SatinalmaSiparisi.id).where(SatinalmaSiparisi.tedarikci_firma_id == firma_id)
        ),
    )
    teslim_toplam = (
        await db.execute(select(func.count()).select_from(TeslimAlma).where(*teslim_kosul))
    ).scalar_one()
    teslim_zamaninda = (
        await db.execute(
            select(func.count())
            .select_from(TeslimAlma)
            .where(*teslim_kosul, TeslimAlma.zamaninda.is_(True))
        )
    ).scalar_one()

    return SkorSinyalleri(
        kalite_gecen=int(kalite_gecen),
        kalite_toplam=int(kalite_toplam),
        sozlesme_saglikli=int(sozlesme_saglikli),
        sozlesme_toplam=int(sozlesme_toplam),
        talep_cozulen=int(talep_cozulen),
        talep_toplam=int(talep_toplam),
        teslim_zamaninda=int(teslim_zamaninda),
        teslim_toplam=int(teslim_toplam),
    )
