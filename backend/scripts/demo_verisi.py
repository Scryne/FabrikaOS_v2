"""FabrikaOS demo verisi — tenant provizyonlar ve TÜM modülleri gerçekçi veriyle doldurur.

Amaç: arayüzü "dolu" hâlde göstermek (pano, ticari pano, listeler, grafikler, onay akışları).
Veri API üzerinden girilir; böylece iş kuralları (stok bakiyesi, durum makineleri, OEE,
outbox olayları, MinIO nesne depolama) gerçek akışla çalışır.

Kullanım (repo kökünden; DB+Redis+MinIO ve API ayakta olmalı):

    docker compose up -d db redis minio
    ./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000   # ayrı terminal
    ./.venv/Scripts/python.exe backend/scripts/demo_verisi.py --tenant demo

Aynı tenant'a ikinci kez çalıştırma kayıtları çoğaltır; betik bunu fark edip durur
(``--force`` ile yine de devam eder). Temiz demo için yeni slug verin.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

VARSAYILAN_ADMIN_EPOSTA = "admin@demo.test"
VARSAYILAN_ADMIN_PAROLA = "Demo1234!"

rng = random.Random(42)  # tekrarlanabilir demo


def _gun(gun_once: int, saat: int = 8, dakika: int = 0) -> str:
    """``gun_once`` gün öncesi (negatifse sonrası) ISO **datetime** — date-time alanları için."""
    t = datetime.now(UTC).replace(hour=saat, minute=dakika, second=0, microsecond=0)
    return (t - timedelta(days=gun_once)).isoformat()


def _tarih(gun_once: int) -> str:
    """``gun_once`` gün öncesi (negatifse sonrası) ISO **date** — date alanları için."""
    return (datetime.now(UTC) - timedelta(days=gun_once)).date().isoformat()


class Istemci:
    """Zarf-farkında küçük HTTP yardımcıs — hata olursa mesajla birlikte patlar."""

    def __init__(self, base: str, tenant: str) -> None:
        self.http = httpx.Client(base_url=base, timeout=60)
        self.tenant = tenant
        self.token: str | None = None

    def _basliklar(self) -> dict[str, str]:
        h = {"X-Tenant": self.tenant}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def giris(self, eposta: str, parola: str) -> None:
        r = self.http.post(
            "/api/v1/kimlik/token",
            data={"username": eposta, "password": parola},
            headers={"X-Tenant": self.tenant},
        )
        r.raise_for_status()
        self.token = r.json()["data"]["access_token"]

    def istek(self, yontem: str, yol: str, govde: Any | None = None, **kw: Any) -> Any:
        # Not: API'de commit yanıt gönderildikten sonra kapanır; art arda hızlı isteklerde
        # yeni kayıt milisaniyelik pencerede henüz görünmeyebilir. 404'te kısa bekleyip
        # birkaç kez yeniden dene (yalnızca bu betiğin hızlı ardışık akışı için).
        for deneme in range(4):
            r = self.http.request(yontem, yol, json=govde, headers=self._basliklar(), **kw)
            if r.status_code != 404 or deneme == 3:
                break
            time.sleep(0.25)
        if r.status_code >= 400:
            raise RuntimeError(f"{yontem} {yol} -> {r.status_code}: {r.text[:300]}")
        j = r.json()
        return j.get("data")

    def post(self, yol: str, govde: Any) -> Any:
        return self.istek("POST", yol, govde)

    def patch(self, yol: str, govde: Any) -> Any:
        return self.istek("PATCH", yol, govde)

    def put(self, yol: str, govde: Any) -> Any:
        return self.istek("PUT", yol, govde)

    def get(self, yol: str) -> Any:
        return self.istek("GET", yol)


# ---------------------------------------------------------------- modüller


def kullanicilar(c: Istemci) -> None:
    for eposta, ad, roller in [
        ("uretim.sefi@demo.test", "Mehmet Yılmaz", ["izleyici"]),
        ("depo@demo.test", "Ayşe Demir", ["depo"]),
        ("satinalma.onay@demo.test", "Hakan Koç", ["satinalma-onaylayan"]),
        ("kalite@demo.test", "Elif Şahin", ["kalite"]),
        ("ik@demo.test", "Zeynep Arslan", ["ik"]),
        ("ik.yonetici@demo.test", "Murat Çelik", ["ik-onaylayan"]),
        ("crm@demo.test", "Deniz Aydın", ["crm"]),
    ]:
        c.post(
            "/api/v1/kullanicilar",
            {"eposta": eposta, "parola": "Demo1234!", "ad_soyad": ad, "roller": roller},
        )
    print("  kullanıcılar: 7")


# Gerçekçi metal işleme hattı — soldan sağa akış (Kesim → Büküm → Talaşlı İmalat →
# Kaynak → Pres → Montaj → Boya). Her makinenin OEE profili (yuksek/orta/dusuk) ve
# dijital ikiz şemasındaki yüzde koordinatı (x, y ∈ 0-100) + bölge etiketi.
# Alanlar: (kod, ad, durum, oee_profil, x, y, bolge)
MAKINE_TANIMLARI = [
    ("LAZER-1", "Fiber Lazer Kesim 1", "calisiyor", "yuksek", 10.0, 22.0, "Kesim"),
    ("LAZER-2", "Fiber Lazer Kesim 2", "calisiyor", "orta", 10.0, 55.0, "Kesim"),
    ("ABKANT-1", "Abkant Pres Büküm", "calisiyor", "yuksek", 25.0, 38.0, "Büküm"),
    ("CNC-1", "CNC Dik İşleme Merkezi 1", "calisiyor", "yuksek", 40.0, 18.0, "Talaşlı İmalat"),
    ("CNC-2", "CNC Dik İşleme Merkezi 2", "calisiyor", "orta", 40.0, 46.0, "Talaşlı İmalat"),
    ("TORNA-1", "CNC Torna Tezgahı", "calisiyor", "orta", 53.0, 18.0, "Talaşlı İmalat"),
    ("FREZE-1", "Üniversal Freze", "durdu", "dusuk", 53.0, 46.0, "Talaşlı İmalat"),
    ("KAYNAK-1", "Robot Kaynak Hücresi 1", "calisiyor", "orta", 68.0, 22.0, "Kaynak"),
    ("KAYNAK-2", "Robot Kaynak Hücresi 2", "bakimda", "orta", 68.0, 52.0, "Kaynak"),
    ("PRES-1", "Hidrolik Pres 250t", "ariza", "dusuk", 82.0, 22.0, "Pres"),
    ("MONTAJ-1", "Montaj Hattı A", "calisiyor", "yuksek", 82.0, 52.0, "Montaj"),
    ("BOYA-1", "Toz Boya Hattı", "calisiyor", "orta", 93.0, 38.0, "Boya"),
]

# OEE profili → (durus_dk_min, durus_dk_max, perf_min, perf_max, kalite_min, kalite_max).
# Duruş = kullanılabilirlik kaybı; perf = performans oranı; kalite = sağlam oranı.
PROFIL_PARAM = {
    "yuksek": (10, 35, 0.90, 0.99, 0.985, 0.999),
    "orta": (30, 70, 0.82, 0.93, 0.965, 0.992),
    "dusuk": (60, 130, 0.70, 0.85, 0.930, 0.980),
}


def makineler(c: Istemci) -> list[dict]:
    kayitlar = []
    for kod, ad, durum, profil, x, y, bolge in MAKINE_TANIMLARI:
        m = c.post("/api/v1/makineler", {"kod": kod, "ad": ad, "oee_hedefi": 0.85})
        # Varsayılan durum "durdu"; hedef durumu her zaman açıkça ayarla.
        c.patch(f"/api/v1/makineler/{m['id']}/durum", {"durum": durum})
        m.update(durum=durum, profil=profil, x=x, y=y, bolge=bolge)
        kayitlar.append(m)
    print(f"  makineler: {len(kayitlar)}")
    return kayitlar


def ikiz_yerlesim(c: Istemci, makineler: list[dict]) -> None:
    """Dijital ikiz şemasına tüm makineleri yerleştir (/ikiz + /kiosk dolu görünsün)."""
    dugumler = [
        {"makine_id": m["id"], "x": m["x"], "y": m["y"], "bolge": m["bolge"]} for m in makineler
    ]
    c.put("/api/v1/ikiz/yerlesim", {"dugumler": dugumler})
    print(f"  dijital ikiz yerleşimi: {len(dugumler)} düğüm")


def uretim_verileri(c: Istemci, makineler: list[dict], gun_sayisi: int = 14) -> None:
    n = 0
    for m in makineler:
        cevrim = rng.choice([24, 36, 45, 60, 75])
        d_lo, d_hi, p_lo, p_hi, k_lo, k_hi = PROFIL_PARAM[m["profil"]]
        for gun in range(gun_sayisi, 0, -1):
            for vardiya, saat in [("Gündüz", 8), ("Gece", 20)]:
                planlanan = 480
                durus = rng.randint(d_lo, d_hi)
                calisma_dk = planlanan - durus
                toplam = int(calisma_dk * 60 / cevrim * rng.uniform(p_lo, p_hi))
                saglam = int(toplam * rng.uniform(k_lo, k_hi))
                c.post(
                    "/api/v1/uretim-verileri",
                    {
                        "makine_id": m["id"],
                        "zaman": _gun(gun, saat),
                        "vardiya": vardiya,
                        "planlanan_sure_dk": planlanan,
                        "durus_sure_dk": durus,
                        "toplam_adet": toplam,
                        "saglam_adet": saglam,
                        "ideal_cevrim_sn": cevrim,
                    },
                )
                n += 1
    print(f"  üretim verileri: {n} ({gun_sayisi} gün × 2 vardiya × {len(makineler)} makine)")


def saha(c: Istemci) -> None:
    for kod, ad, protokol in [
        ("GW-1", "Saha Ağ Geçidi (hat A)", "simulasyon"),
        ("PLC-PRES", "Pres Hattı PLC", "modbus"),
        ("OPC-CNC", "CNC OPC-UA Sunucusu", "opcua"),
    ]:
        c.post("/api/v1/saha/cihazlar", {"kod": kod, "ad": ad, "protokol": protokol})
    print("  saha cihazları: 3")


def is_emirleri(c: Istemci, makineler: list[dict], admin_id: int) -> None:
    koda_gore = {m["kod"]: m for m in makineler}
    # (başlık, makine_kod, öncelik, hedef_durum) — başlık makineyle tutarlı.
    kayitlar = [
        ("PRES-1 hidrolik pompa arızası — hat durdu", "PRES-1", "kritik", "devam_ediyor"),
        ("KAYNAK-2 periyodik bakım uygulaması", "KAYNAK-2", "yuksek", "devam_ediyor"),
        ("FREZE-1 mil rulmanı değişimi", "FREZE-1", "yuksek", "atandi"),
        ("LAZER-1 optik lens temizliği ve kalibrasyon", "LAZER-1", "orta", "kapandi"),
        ("CNC-1 takım tezgahı ofset ayarı", "CNC-1", "orta", "kapandi"),
        ("MONTAJ-1 konveyör bandı gerginlik ayarı", "MONTAJ-1", "orta", "atandi"),
        ("CNC-2 soğutma sıvısı değişimi", "CNC-2", "dusuk", "atandi"),
        ("TORNA-1 ayna çenesi yenileme", "TORNA-1", "orta", "acik"),
        ("ABKANT-1 büküm bıçağı aşınma kontrolü", "ABKANT-1", "dusuk", "acik"),
        ("BOYA-1 fırın sıcaklık kalibrasyonu", "BOYA-1", "orta", "kapandi"),
        ("LAZER-2 kesim kafası nozul değişimi", "LAZER-2", "dusuk", "kapandi"),
        ("KAYNAK-1 torç nozulu tıkanması", "KAYNAK-1", "orta", "iptal"),
    ]
    hedef_yol = {
        "atandi": ["atandi"],
        "devam_ediyor": ["atandi", "devam_ediyor"],
        "kapandi": ["atandi", "devam_ediyor", "kapandi"],
        "iptal": ["iptal"],
        "acik": [],
    }
    for baslik, kod, oncelik, durum in kayitlar:
        m = koda_gore[kod]
        ie = c.post(
            "/api/v1/is-emirleri",
            {
                "baslik": baslik,
                "makine_id": m["id"],
                "oncelik": oncelik,
                "aciklama": "Demo iş emri — vardiya amiri bildirimi.",
            },
        )
        for hedef in hedef_yol[durum]:
            govde: dict[str, Any] = {"durum": hedef}
            if hedef == "atandi":
                govde["atanan_kullanici_id"] = admin_id
            c.patch(f"/api/v1/is-emirleri/{ie['id']}/durum", govde)
        if durum == "kapandi":
            c.post(
                f"/api/v1/is-emirleri/{ie['id']}/yorum",
                {"metin": "Müdahale tamamlandı, makine devrede."},
            )
    print(f"  iş emirleri: {len(kayitlar)}")


def bakim(c: Istemci, makineler: list[dict]) -> None:
    n = 0
    for i, m in enumerate(makineler):
        tip = ["onleyici", "kestirimci", "periyodik"][i % 3]
        periyot = [30, 60, 90][i % 3]
        is_adi = "yağlama" if tip == "periyodik" else "kontrol"
        # İki plan bilinçli gecikmiş (sonraki bakım geçmişte) — panoda uyarı görünsün.
        gecikme = -rng.randint(2, 9) if i < 2 else rng.randint(5, periyot)
        c.post(
            "/api/v1/bakim-planlari",
            {
                "makine_id": m["id"],
                "ad": f"{m['kod']} {periyot} günlük {is_adi}",
                "tip": tip,
                "periyot_gun": periyot,
                "son_bakim_tarihi": _gun(
                    periyot - gecikme if gecikme > 0 else periyot + abs(gecikme)
                ),
                "sonraki_bakim_tarihi": _gun(-gecikme) if gecikme > 0 else _gun(abs(gecikme)),
                "aciklama": "Demo bakım planı.",
            },
        )
        n += 1
    print(f"  bakım planları: {n}")


def stok(c: Istemci) -> list[dict]:
    tanimlar = [
        ("SAC-2MM", "DKP Sac 2mm", "kg", "hammadde", 500, 200),
        ("SAC-3MM", "DKP Sac 3mm", "kg", "hammadde", 500, 150),
        ("PROFIL-40", "Kutu Profil 40x40", "metre", "hammadde", 300, 100),
        ("ELEKTROT-308", "Paslanmaz Elektrot 308L", "kg", "sarf", 50, 20),
        ("BOYA-RAL7016", "Toz Boya RAL7016", "kg", "sarf", 80, 30),
        ("HIDROLIK-46", "Hidrolik Yağ 46", "litre", "sarf", 120, 60),
        ("RULMAN-6205", "Rulman 6205-2RS", "adet", "yedek", 40, 15),
        ("CIVATA-M8", "Cıvata M8x30 8.8", "adet", "sarf", 2000, 500),
        ("CONTA-NBR", "NBR Conta Seti", "adet", "yedek", 25, 10),
        ("KESKI-10", "Karbür Kesici Uç 10mm", "adet", "sarf", 60, 25),
        ("AMBALAJ-KOLI", "Koli 60x40x40", "adet", "ambalaj", 400, 150),
        ("GAZ-ARGON", "Argon Tüpü", "adet", "sarf", 12, 5),
    ]
    kayitlar = []
    for kod, ad, birim, kategori, mmax, kritik in tanimlar:
        mkayit = c.post(
            "/api/v1/malzemeler",
            {
                "kod": kod,
                "ad": ad,
                "birim": birim,
                "kategori": kategori,
                "min_stok": kritik,
                "max_stok": mmax * 2,
                "kritik_stok": kritik,
            },
        )
        kayitlar.append(mkayit)
        # Giriş + tüketim hareketleri; ilk 3 malzeme kritik eşiğin ALTINA insin.
        hedef = kritik * (0.6 if len(kayitlar) <= 3 else rng.uniform(1.6, 3.0))
        giris = max(hedef + rng.uniform(0.2, 0.5) * mmax, hedef)
        c.post(
            "/api/v1/stok-hareketleri",
            {
                "malzeme_id": mkayit["id"],
                "tur": "giris",
                "miktar": round(giris, 1),
                "aciklama": "Açılış sayımı",
                "kaynak": "sayim",
            },
        )
        c.post(
            "/api/v1/stok-hareketleri",
            {
                "malzeme_id": mkayit["id"],
                "tur": "cikis",
                "miktar": round(giris - hedef, 1),
                "aciklama": "Üretim tüketimi",
                "kaynak": "uretim",
            },
        )
    print(f"  malzemeler: {len(kayitlar)} (3'ü kritik eşik altında)")
    return kayitlar


def satinalma(c: Istemci, malzemeler: list[dict]) -> None:
    def kalem(i: int, miktar: float, fiyat: float) -> dict:
        m = malzemeler[i]
        return {
            "malzeme_id": m["id"],
            "miktar": miktar,
            "birim": m["birim"],
            "tahmini_birim_fiyat": fiyat,
            "aciklama": "",
        }

    senaryolar = [
        ("Kritik sac stoğu ikmali", [kalem(0, 800, 32.5), kalem(1, 500, 38.0)], "onaylandi"),
        ("Kaynak sarf malzemeleri", [kalem(3, 40, 950.0), kalem(11, 6, 1400.0)], "onay_bekliyor"),
        ("Bakım yedek parça talebi", [kalem(6, 20, 210.0), kalem(8, 10, 320.0)], "reddedildi"),
        ("Ambalaj yenileme", [kalem(10, 600, 9.75)], "taslak"),
    ]
    for baslik, kalemler, durum in senaryolar:
        t = c.post(
            "/api/v1/satinalma-talepleri",
            {
                "baslik": baslik,
                "aciklama": "Demo talebi",
                "para_birimi": "TRY",
                "kalemler": kalemler,
            },
        )
        if durum != "taslak":
            c.post(f"/api/v1/satinalma-talepleri/{t['id']}/gonder", {})
        if durum == "onaylandi":
            c.post(f"/api/v1/satinalma-talepleri/{t['id']}/onayla", {})
        elif durum == "reddedildi":
            c.post(
                f"/api/v1/satinalma-talepleri/{t['id']}/reddet",
                {"red_nedeni": "Bütçe onayı bekliyor; sonraki döneme ertelendi."},
            )
    print("  satınalma talepleri: 4")


def kalite(c: Istemci, makineler: list[dict]) -> None:
    for i in range(28):
        m = makineler[i % len(makineler)]
        sonuc = rng.choices(["gecti", "kaldi", "sartli"], weights=[10, 2, 2])[0]
        hedef = 25.0
        olculen = round(rng.uniform(24.4, 25.6) if sonuc == "gecti" else rng.uniform(25.7, 26.4), 2)
        c.post(
            "/api/v1/kalite-kontrolleri",
            {
                "makine_id": m["id"],
                "kontrol_turu": rng.choice(["uretim", "giris", "final"]),
                "sonuc": sonuc,
                "olculen_deger": olculen,
                "alt_limit": hedef - 0.5,
                "ust_limit": hedef + 0.5,
                "numune_adedi": 5,
                "uygunsuz_adet": 0 if sonuc == "gecti" else rng.randint(1, 3),
                "aciklama": "Demo ölçümü",
                "zaman": _gun(rng.randint(0, 6), rng.randint(8, 18)),
            },
        )
    # CAPA: farklı aşamalarda 4 uygunsuzluk.
    senaryolar = [
        (
            "Çap ölçüsü tolerans dışı (CNC-1)",
            "yuksek",
            ["kok_neden", "aksiyon_plani", "uygulama", "dogrulama", "kapandi"],
        ),
        ("Boya kalınlığı düşük", "orta", ["kok_neden", "aksiyon_plani", "uygulama"]),
        ("Kaynak dikişinde gözenek", "kritik", ["kok_neden", "aksiyon_plani"]),
        ("Ambalaj etiket hatası", "dusuk", []),
    ]
    for i, (baslik, onem, yol) in enumerate(senaryolar):
        u = c.post(
            "/api/v1/uygunsuzluklar",
            {
                "baslik": baslik,
                "onem": onem,
                "makine_id": makineler[i % len(makineler)]["id"],
                "aciklama": "Demo uygunsuzluk kaydı.",
            },
        )
        if yol:
            c.post(
                f"/api/v1/uygunsuzluklar/{u['id']}/aksiyonlar",
                {
                    "tur": "duzeltici",
                    "aciklama": "Kök neden analizi ve düzeltici aksiyon.",
                    "termin_tarihi": _gun(-14),
                },
            )
        for hedef in yol:
            govde: dict[str, Any] = {"hedef": hedef}
            if hedef == "kok_neden":
                govde["kok_neden"] = "Takım aşınması / parametre sapması (demo)."
            if hedef == "dogrulama":
                govde["dogrulama_notu"] = "Numune ölçümleri tolerans içinde (demo)."
            c.patch(f"/api/v1/uygunsuzluklar/{u['id']}/durum", govde)
    print("  kalite kontrolleri: 28 + CAPA: 4")


def enerji(c: Istemci, makineler: list[dict]) -> None:
    n = 0
    for gun in range(7, 0, -1):
        for saat in range(0, 24, 2):
            taban = 42 if 7 <= saat <= 19 else 18  # mesai profili
            c.post(
                "/api/v1/enerji-tuketimleri",
                {
                    "enerji_turu": "elektrik",
                    "tuketim": round(taban * rng.uniform(0.85, 1.2), 1),
                    "birim": "kWh",
                    "zaman": _gun(gun, saat),
                },
            )
            n += 1
    for gun in range(7, 0, -1):
        c.post(
            "/api/v1/enerji-tuketimleri",
            {
                "enerji_turu": "dogalgaz",
                "tuketim": round(rng.uniform(60, 140), 1),
                "birim": "m3",
                "zaman": _gun(gun, 12),
            },
        )
        c.post(
            "/api/v1/enerji-tuketimleri",
            {
                "makine_id": makineler[0]["id"],
                "enerji_turu": "hava",
                "tuketim": round(rng.uniform(200, 400), 0),
                "birim": "m3",
                "zaman": _gun(gun, 14),
            },
        )
        n += 2
    print(f"  enerji ölçümleri: {n}")


def isg(c: Istemci, makineler: list[dict]) -> None:
    kazalar = [
        ("kaza", "orta", "Pres hattı", "El sıkışması — koruyucu eldivenle atlatıldı", 3),
        ("kaza", "hafif", "Depo", "Ayak burkulması (palet kenarı)", 1),
        ("ramak_kala", "hafif", "Kaynak hücresi", "Askıdaki parça salınımı — kimse etkilenmedi", 0),
        ("ramak_kala", "orta", "CNC alanı", "Talaş fırlaması — siperlik sayesinde atlatıldı", 0),
        ("meslek_hastaligi", "orta", "Boyahane", "Solunum yolu tahrişi şüphesi", 5),
    ]
    for i, (tur, agirlik, yer, aciklama, kayip) in enumerate(kazalar):
        c.post(
            "/api/v1/is-kazalari",
            {
                "tur": tur,
                "agirlik": agirlik,
                "yer": yer,
                "aciklama": aciklama,
                "kaybedilen_gun": kayip,
                "yaralanma_turu": "—",
                "olay_tarihi": _gun(rng.randint(2, 25), rng.randint(8, 18)),
                "makine_id": makineler[i % len(makineler)]["id"],
            },
        )
    riskler = [
        ("Pres kalıp değişiminde el sıkışması", "Pres hattı", 4, 4),
        ("Yüksekte çalışma — vinç bakımı", "Bakım", 3, 5),
        ("Kimyasal maruziyet — boyahane", "Boyahane", 3, 3),
        ("Forklift-yaya çarpışması", "Depo", 2, 4),
        ("Gürültü maruziyeti", "Üretim sahası", 4, 2),
        ("Kablo takılma-düşme", "Ofis", 2, 1),
    ]
    for baslik, bolum, olasilik, siddet in riskler:
        c.post(
            "/api/v1/risk-degerlendirmeleri",
            {
                "baslik": baslik,
                "bolum": bolum,
                "tehlike": baslik,
                "olasilik": olasilik,
                "siddet": siddet,
                "onlem": "Prosedür + KKD + eğitim",
                "durum": "acik",
                "gecerlilik_tarihi": _tarih(-180),
            },
        )
    print("  İSG: 5 kaza + 6 risk")


def ik(c: Istemci) -> None:
    personel_tanimlari = [
        ("P-001", "Mehmet", "Yılmaz", "Üretim", "Vardiya Amiri"),
        ("P-002", "Ayşe", "Demir", "Depo", "Depo Sorumlusu"),
        ("P-003", "Elif", "Şahin", "Kalite", "Kalite Mühendisi"),
        ("P-004", "Murat", "Çelik", "Bakım", "Bakım Teknisyeni"),
        ("P-005", "Zeynep", "Arslan", "İK", "İK Uzmanı"),
        ("P-006", "Deniz", "Aydın", "Satış", "Satış Temsilcisi"),
        ("P-007", "Hakan", "Koç", "Satınalma", "Satınalma Uzmanı"),
        ("P-008", "Selin", "Kaya", "Üretim", "CNC Operatörü"),
        ("P-009", "Emre", "Öztürk", "Üretim", "Kaynak Operatörü"),
        ("P-010", "Fatma", "Güneş", "Muhasebe", "Muhasebe Uzmanı"),
    ]
    personeller = []
    for i, (sicil, ad, soyad, dep, unvan) in enumerate(personel_tanimlari):
        p = c.post(
            "/api/v1/personeller",
            {
                "sicil_no": sicil,
                "ad": ad,
                "soyad": soyad,
                "tc_kimlik_no": f"1000000{i:02d}46",
                "departman": dep,
                "unvan": unvan,
                "eposta": f"{sicil.lower()}@demo.test",
                "telefon": f"0532 000 00 {i:02d}",
                "ise_giris_tarihi": _tarih(365 * (i % 5) + 90),
                "yillik_izin_hakki": 14,
            },
        )
        personeller.append(p)

    izinler = [
        (0, "yillik", 10, 5, "onaylandi"),
        (1, "yillik", 30, 4, "onaylandi"),
        (2, "mazeret", -3, 1, "onay_bekliyor"),
        (3, "hastalik", 2, 3, "onay_bekliyor"),
        (4, "yillik", -10, 7, "reddedildi"),
        (5, "ucretsiz", -20, 15, "taslak"),
    ]
    for pi, tur, basla_gun_once, sure, durum in izinler:
        z = c.post(
            "/api/v1/izin-talepleri",
            {
                "personel_id": personeller[pi]["id"],
                "izin_turu": tur,
                "baslangic_tarihi": _tarih(basla_gun_once),
                "bitis_tarihi": _tarih(basla_gun_once - sure),
                "aciklama": "Demo izin talebi",
            },
        )
        if durum != "taslak":
            c.post(f"/api/v1/izin-talepleri/{z['id']}/gonder", {})
        if durum == "onaylandi":
            c.post(f"/api/v1/izin-talepleri/{z['id']}/onayla", {})
        elif durum == "reddedildi":
            c.post(
                f"/api/v1/izin-talepleri/{z['id']}/reddet",
                {"red_nedeni": "Dönem yoğunluğu nedeniyle uygun değil."},
            )

    for pi, gun_once, saat in [(0, 3, 2.5), (3, 5, 4.0), (7, 2, 3.0), (8, 1, 2.0)]:
        fm = c.post(
            "/api/v1/fazla-mesailer",
            {
                "personel_id": personeller[pi]["id"],
                "tarih": _tarih(gun_once),
                "saat": saat,
                "aciklama": "Sipariş yetiştirme",
            },
        )
        if pi in (0, 3):
            c.post(f"/api/v1/fazla-mesailer/{fm['id']}/onayla", {})

    zimmetler = [
        (0, "Dizüstü bilgisayar Dell 5540", "DL5540-071"),
        (1, "El terminali Zebra TC26", "ZB-TC26-114"),
        (3, "Tork anahtarı seti", "TK-SET-09"),
        (7, "Kumpas Mitutoyo 150mm", "MT-150-233"),
        (8, "Kaynak maskesi otomatik", "KM-AUTO-41"),
    ]
    for i, (pi, demirbas, seri) in enumerate(zimmetler):
        z = c.post(
            "/api/v1/zimmetler",
            {
                "personel_id": personeller[pi]["id"],
                "demirbas": demirbas,
                "seri_no": seri,
                "zimmet_tarihi": _tarih(120 - i * 20),
            },
        )
        if i == 2:
            c.post(f"/api/v1/zimmetler/{z['id']}/iade", {})

    sertifikalar = [
        (3, "Yüksekte Çalışma Eğitimi", "İSG Akademi"),
        (8, "MIG/MAG Kaynakçı Sertifikası", "TSE"),
        (7, "CNC Operatörlüğü Seviye 4", "MYK"),
        (0, "İlk Yardım Sertifikası", "Kızılay"),
        (2, "ISO 9001 İç Denetçi", "TÜV"),
        (1, "Forklift Operatör Belgesi", "MEB"),
    ]
    for pi, ad, kurum in sertifikalar:
        c.post(
            "/api/v1/sertifikalar",
            {
                "personel_id": personeller[pi]["id"],
                "ad": ad,
                "kurum": kurum,
                "alinma_tarihi": _tarih(rng.randint(100, 700)),
                "gecerlilik_tarihi": _tarih(-rng.randint(100, 900)),
            },
        )
    print("  İK: 10 personel + 6 izin + 4 mesai + 5 zimmet + 6 sertifika")


def crm(c: Istemci, admin_id: int) -> None:
    firmalar_tanim = [
        ("Aksa Makina San. A.Ş.", "musteri", "İstanbul", "Otomotiv yan sanayi"),
        ("Demir Çelik Ltd. Şti.", "tedarikci", "Kocaeli", "Metal tedarik"),
        ("Nova Beyaz Eşya A.Ş.", "musteri", "Manisa", "Beyaz eşya"),
        ("Ege Profil Sanayi", "tedarikci", "İzmir", "Profil/boru tedarik"),
        ("Kuzey Enerji Sistemleri", "her_ikisi", "Ankara", "Enerji ekipmanları"),
        ("Marmara Savunma Teknolojileri", "musteri", "Bursa", "Savunma sanayi"),
    ]
    firmalar = []
    for ad, tip, il, sektor in firmalar_tanim:
        f = c.post(
            "/api/v1/firmalar",
            {
                "ad": ad,
                "tip": tip,
                "il": il,
                "sektor": sektor,
                "eposta": "info@" + ad.split()[0].lower() + ".example",
                "telefon": "0212 000 00 00",
                "sorumlu_kullanici_id": admin_id,
            },
        )
        firmalar.append(f)
        c.post(
            "/api/v1/ortaklar",
            {
                "firma_id": f["id"],
                "ad_soyad": f"{ad.split()[0]} Yetkilisi",
                "unvan": "Satınalma Müdürü",
                "eposta": "yetkili@" + ad.split()[0].lower() + ".example",
                "birincil": True,
            },
        )

    sozlesmeler = [
        (0, "Yıllık parça tedarik çerçeve sözleşmesi", "satis", -300, 65, 2_450_000, "aktif"),
        (2, "Beyaz eşya sac parça üretimi", "satis", -120, 12, 880_000, "aktif"),  # yaklaşan bitiş!
        (1, "Hammadde alım sözleşmesi", "alis", -200, 165, 1_200_000, "aktif"),
        (5, "Savunma projesi gizlilik sözleşmesi", "nda", -90, 275, 0, "aktif"),
        (4, "Enerji panosu üretim teklifi", "satis", -10, 355, 640_000, "taslak"),
        (3, "Eski profil tedarik sözleşmesi", "alis", -700, -30, 350_000, "sonlandi"),
    ]
    for fi, baslik, tur, basla, bitis_gun_sonra, tutar, durum in sozlesmeler:
        s = c.post(
            "/api/v1/sozlesmeler",
            {
                "firma_id": firmalar[fi]["id"],
                "baslik": baslik,
                "tur": tur,
                "baslangic_tarihi": _tarih(-basla),
                "bitis_tarihi": _tarih(-bitis_gun_sonra),
                "tutar": tutar,
                "para_birimi": "TRY",
                "sorumlu_kullanici_id": admin_id,
            },
        )
        if durum in ("aktif", "sonlandi"):
            c.patch(f"/api/v1/sozlesmeler/{s['id']}/durum", {"durum": "aktif"})
        if durum == "sonlandi":
            c.patch(f"/api/v1/sozlesmeler/{s['id']}/durum", {"durum": "sonlandi"})
    # Yaklaşan bitişleri tara → kenar-tetikli 'sozlesme.yaklasiyor' outbox olayı.
    c.post("/api/v1/sozlesmeler/yaklasanlari-tara", {})

    talepler = [
        (0, "Yeni model braket için fiyat teklifi", "teklif", "yuksek", "cozuldu"),
        (2, "Sevkiyat gecikmesi şikayeti", "sikayet", "yuksek", "inceleniyor"),
        (5, "Teknik çizim revizyon talebi", "destek", "orta", "acik"),
        (4, "Pano montaj kapasitesi bilgisi", "bilgi", "dusuk", "kapandi"),
        (0, "Ek kalıp yatırımı görüşmesi", "teklif", "orta", "inceleniyor"),
        (2, "Fatura düzeltme talebi", "diger", "dusuk", "cozuldu"),
        (3, "Profil ölçü değişikliği", "destek", "orta", "acik"),
    ]
    yol = {
        "acik": [],
        "inceleniyor": ["inceleniyor"],
        "cozuldu": ["inceleniyor", "cozuldu"],
        "kapandi": ["inceleniyor", "cozuldu", "kapandi"],
    }
    for fi, baslik, tur, oncelik, durum in talepler:
        t = c.post(
            "/api/v1/talepler",
            {
                "firma_id": firmalar[fi]["id"],
                "baslik": baslik,
                "tur": tur,
                "oncelik": oncelik,
                "talep_eden_ad": "Firma yetkilisi",
                "aciklama": "Demo müşteri talebi.",
            },
        )
        for hedef in yol[durum]:
            c.patch(f"/api/v1/talepler/{t['id']}/durum", {"durum": hedef})
    print("  CRM: 6 firma + 6 sözleşme + 7 talep")


def dys(c: Istemci) -> None:
    belgeler = [
        ("Kalite El Kitabı", "kalite", 2),
        ("İSG Acil Durum Prosedürü", "isg", 1),
        ("CNC-1 Bakım Talimatı", "bakim", 2),
        ("Müşteri Sözleşme Şablonu", "sozlesme", 1),
    ]
    for ad, kategori, surum_sayisi in belgeler:
        b = c.post("/api/v1/belgeler", {"ad": ad, "kategori": kategori, "aciklama": "Demo belgesi"})
        for s in range(1, surum_sayisi + 1):
            icerik = f"%PDF-1.4\n% FabrikaOS demo belgesi: {ad} v{s}\n".encode() + bytes(
                rng.randbytes(256)
            )
            r = c.http.post(
                f"/api/v1/belgeler/{b['id']}/surumler",
                files={"dosya": (f"{kategori}-v{s}.pdf", icerik, "application/pdf")},
                data={"aciklama": f"Sürüm {s}"},
                headers=c._basliklar(),
            )
            if r.status_code >= 400:
                raise RuntimeError(f"belge yükleme -> {r.status_code}: {r.text[:200]}")
    print("  DYS: 4 belge (6 sürüm, MinIO)")


def duyurular(c: Istemci) -> None:
    tanimlar = [
        (
            "Cumartesi planlı elektrik kesintisi",
            "uyari",
            "Cumartesi 06:00-10:00 arası trafo bakımı yapılacaktır.",
            True,
        ),
        (
            "Yeni İSG eğitim takvimi yayınlandı",
            "bilgi",
            "Temmuz ayı eğitim oturumları İK panosunda.",
            True,
        ),
        (
            "PRES-1 hattı geçici olarak devre dışı",
            "kritik",
            "Hidrolik pompa arızası; iş emirleri PRES-2'ye yönlendirildi.",
            True,
        ),
        ("Yemekhane menüsü güncellendi", "bilgi", "Yaz menüsü pazartesi başlıyor.", True),
        ("Yıl sonu envanter sayımı (taslak)", "uyari", "Planlama devam ediyor.", False),
    ]
    for baslik, onem, icerik, yayinla in tanimlar:
        d = c.post(
            "/api/v1/duyurular",
            {"baslik": baslik, "onem": onem, "icerik": icerik, "bitis_tarihi": _gun(-30)},
        )
        if yayinla:
            c.post(f"/api/v1/duyurular/{d['id']}/yayinla", {})
    print("  duyurular: 5 (4 yayında)")


# ---------------------------------------------------------------- ana akış


async def provizyonla(slug: str, ad: str, eposta: str, parola: str) -> None:
    from app.control_plane.provizyon import tenant_provizyonla

    await tenant_provizyonla(slug=slug, ad=ad, admin_eposta=eposta, admin_parola=parola)


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS demo verisi")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--tenant", default="demo")
    p.add_argument("--tenant-ad", default="Demo Fabrika A.Ş.")
    p.add_argument("--admin-eposta", default=VARSAYILAN_ADMIN_EPOSTA)
    p.add_argument("--admin-parola", default=VARSAYILAN_ADMIN_PAROLA)
    p.add_argument("--force", action="store_true", help="Var olan veriye rağmen devam et")
    args = p.parse_args()

    print(f"tenant provizyonlanıyor: {args.tenant}")
    asyncio.run(provizyonla(args.tenant, args.tenant_ad, args.admin_eposta, args.admin_parola))

    c = Istemci(args.base_url, args.tenant)
    c.giris(args.admin_eposta, args.admin_parola)
    ben = c.get("/api/v1/kimlik/ben")

    mevcut = c.get("/api/v1/makineler?sayfa=1&adet=1")
    if mevcut and not args.force:
        print("Bu tenant'ta zaten veri var; --force ile yine de çalıştırabilirsiniz.")
        return 1

    print("demo verisi giriliyor…")
    kullanicilar(c)
    m = makineler(c)
    ikiz_yerlesim(c, m)
    uretim_verileri(c, m)
    saha(c)
    is_emirleri(c, m, ben["id"])
    bakim(c, m)
    malzemeler_l = stok(c)
    satinalma(c, malzemeler_l)
    kalite(c, m)
    enerji(c, m)
    isg(c, m)
    ik(c)
    crm(c, ben["id"])
    dys(c)
    duyurular(c)
    print(f"\nTamam. Giriş: {args.admin_eposta} / {args.admin_parola}  (X-Tenant: {args.tenant})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
