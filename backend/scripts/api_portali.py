"""Geliştirici API portalı (S28, ADR-0047): OpenAPI şemasından statik site.

``docs/api/index.html`` tek dosyadır: şema (uygulamanın kendisinden üretilir, veritabanı
gerekmez) sayfaya sıkıştırılmış gömülür, Redoc gösterir. Herhangi bir statik sunucuda ya da doğrudan
dosyadan açılır; arama, etiket bazlı gezinme ve istek/yanıt örnekleri Redoc'tan gelir. Ham şema
zaten ``frontend/openapi.json``'da (tip üretimi için) durduğundan ikinci kopya tutulmaz.
Portalın başına kimlik doğrulama, tenant başlığı ve hata zarfı anlatımı eklenir.

    python backend/scripts/api_portali.py            # docs/api/index.html yazar
    python backend/scripts/api_portali.py --kontrol  # şema değiştiyse 1 döner (CI)

Çıktı yalnız koddan değil, şemayı üreten kütüphanelerden de etkilenir: pydantic 2.14, ``Decimal``
alanlarına eskiden kendiliğinden konan ``pattern``'i kaldırdı (eski desen geçerli üslü yazımı,
ör. ``1E+2``, reddediyordu). Eski pydantic'li bir ortam bu yüzden aynı koddan farklı bir sayfa
üretir; CI'nın temiz Linux kurulumu en yeni sürümü aldığı için fark "yalnız Linux'ta" görünüyordu.
Bu yüzden betik sürüm tabanını kendisi denetler ve tabanın altındaki bir ortamda yazmayı reddeder.
"""

# ruff: noqa: E501 — GIRIS ve SAYFA şablon metni (Markdown tablosu, HTML) satır kırılmadan durur

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
HEDEF = KOK / "docs" / "api"
REDOC = "https://cdn.jsdelivr.net/npm/redoc@2.1.5/bundles/redoc.standalone.js"
# Şema çıktısını değiştiren en son pydantic sürümü (Decimal deseni). pyproject.toml tabanıyla aynı.
PYDANTIC_TABANI = (2, 14)

GIRIS = """
## Başlarken

**Taban adres:** `https://<kurulumunuz>/api/v1`. Her istek hangi fabrikaya (tenant) ait olduğunu
`X-Tenant: <fabrika-kodu>` başlığıyla söyler.

**Kimlik doğrulama.** İki yol vardır:

1. *Kullanıcı adına* (ön yüz, kısa ömürlü betikler): `POST /api/v1/kimlik/token` (form:
   `username`, `password`) → `access_token` (15 dk) + `refresh_token`. Her istekte
   `Authorization: Bearer <access_token>`. Yenileme: `POST /api/v1/kimlik/yenile`; her yenileme
   yeni bir refresh token verir, eskisi geçersizleşir.
2. *Sistem entegrasyonu* (ERP, MES, BI): Yönetim › Webhooklar & API ekranından izin kapsamlı
   **API anahtarı**; `/api/v1/entegrasyon/*` uçlarında `X-API-Anahtar: <anahtar>`.

**Yanıt zarfı.** Başarılı yanıt `{"success": true, "data": …, "message": …}`; listelerde ayrıca
`meta` (sayfa, adet, toplam). Hata `{"success": false, "message", "hata_kodu", "detaylar": [{"alan", "mesaj"}]}`.

| Durum | `hata_kodu` | Anlamı |
|---|---|---|
| 401 | `KIMLIK` | Token yok, süresi dolmuş ya da geçersiz |
| 403 | `YETKISIZ`, `MODUL_KAPALI` | Rolde izin yok / modül abonelikte kapalı |
| 404 | `BULUNAMADI` | Kayıt yok ya da bu tenant'a ait değil |
| 409 | `CAKISMA`, `BAGLI_KAYIT` | Benzersizlik ya da durum çakışması / silinecek kayda bağlı kayıt var |
| 422 | `DOGRULAMA`, `GECERSIZ_DEGER`, `GECERSIZ_REFERANS` | Girdi geçersiz / aralık-biçim dışı değer / olmayan kayda referans |
| 429 | `RATE_LIMIT` | Oran sınırı (giriş, SSO, 2FA denemeleri); bir süre bekleyip yeniden deneyin |
| 503 | `HIZMET_KULLANILAMAZ` | Bağımlı altyapı geçici olarak yok; işlem yapılmadı, yeniden deneyin |

**Webhook imzası.** Giden olaylar `X-FabrikaOS-Signature: t=<unix>,v1=<hex>` taşır;
`HMAC-SHA256(gizli_anahtar, "<t>." + ham_gövde)` ile doğrulayın ve 5 dakikadan eski `t`'yi reddedin.
"""

SAYFA = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FabrikaOS API</title>
<meta name="description" content="FabrikaOS REST API başvurusu: uçlar, şemalar, kimlik doğrulama.">
<style>body{{margin:0;background:#fff}}</style>
</head>
<body>
<div id="portal"></div>
<noscript>Bu sayfa JavaScript ister. Ham şema depoda: frontend/openapi.json</noscript>
<script id="sema" type="application/json">{sema}</script>
<script src="{redoc}"></script>
<script>
Redoc.init(JSON.parse(document.getElementById("sema").textContent), {{
  hideHostname: true, expandResponses: "200,201", pathInMiddlePanel: true, nativeScrollbars: true
}}, document.getElementById("portal"));
</script>
</body>
</html>
"""


def surumler() -> str:
    from importlib.metadata import version

    return ", ".join(f"{p} {version(p)}" for p in ("pydantic", "pydantic-core", "fastapi"))


def surum_uygun() -> bool:
    import pydantic

    ana, alt = (int(x) for x in pydantic.VERSION.split(".")[:2])
    return (ana, alt) >= PYDANTIC_TABANI


def sema() -> dict[str, object]:
    sys.path.insert(0, str(KOK / "backend"))
    from app.main import create_app

    s = create_app().openapi()
    bilgi = dict(s.get("info", {}))
    bilgi["description"] = str(bilgi.get("description", "")) + "\n" + GIRIS
    s["info"] = bilgi
    return s


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS API portalı")
    p.add_argument("--kontrol", action="store_true", help="yazmadan, güncel mi diye bak")
    a = p.parse_args()
    if not surum_uygun():
        taban = ".".join(map(str, PYDANTIC_TABANI))
        print(
            f"pydantic >= {taban} gerekli ({surumler()}); eski sürüm Decimal alanlarına farklı şema "
            'üretir. Ortamı güncelleyin: pip install -e ".[dev]"'
        )
        return 2
    s = sema()
    metin = json.dumps(s, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    # Şema sayfaya gömülür: file:// ile açılınca tarayıcı ayrı JSON'u getirmeyi reddeder.
    sayfa = SAYFA.format(redoc=REDOC, sema=metin.replace("</", "<\\/"))
    hedef = HEDEF / "index.html"
    if a.kontrol:
        if not hedef.exists() or hedef.read_text(encoding="utf-8") != sayfa:
            print("docs/api/index.html güncel değil: python backend/scripts/api_portali.py")
            print(f"Üreten ortam: {surumler()}")
            return 1
        return 0
    HEDEF.mkdir(parents=True, exist_ok=True)
    hedef.write_text(sayfa, encoding="utf-8", newline="\n")
    print(f"docs/api/index.html yazıldı: {len(s['paths'])} yol")  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
