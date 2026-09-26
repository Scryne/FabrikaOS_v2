# DURUM — FabrikaOS_v2 — çok kiracılı MES+ERP

> **Ne bu dosya:** sertifika değil **envanter**. Ölçülen gerçek durum; "çalışmıyor" yazan satır
> kusur değil, kayıt. Kapanış standardı: `ScryneOS/🎯 100-Command-Center/Kapanis-Standardi.md`

**Ölçüm tarihi:** 2026-09-26 (önceki: 2026-08-27)
**Tek cümle:** Backend 667 + frontend 214 test yeşil, CI 07-30'dan beri ilk kez tam kapıdan
geçecek durumda; demo tenant tüm modülleriyle dolu ve kendini bugüne getiriyor.

## Ne çalışıyor (ölçüldü)

- **Backend:** 667 test (birim + gerçek PostgreSQL/TimescaleDB entegrasyon), MinIO kapalıyken
  de 657/657 → testler dış servise bağlı değil. `ruff`, `ruff format`, `mypy` temiz, `pip-audit` 0.
- **Frontend:** 214 test, `tsc --strict`, ESLint, Prettier, Vite 8 derlemesi temiz. `npm audit`
  yüksek/kritik 0 (kalan 2 orta: react-router 6, bkz. README güvenlik notları).
- **CI benzetimi:** `node:22` konteynerinde temiz `npm ci` + tam frontend kapısı geçti.
- **Docker:** API imajı derleniyor (`.dockerignore` README'yi dışlıyordu → düzeltildi);
  compose'da `bildirim` ve `webhook-relay` süreçleri var.
- **Demo:** `demo` tenant — 12 makine, 14+ gün üretim, iş emirleri, bakım, stok, satınalma,
  kalite/CAPA, enerji, İSG, İK, CRM, DYS, duyuru, vardiya/duruş, ürün/reçete + lot
  izlenebilirliği, 3 rapor, 144 bildirim, 3/4 AI modeli eğitilmiş.
- **Arayüz:** 43 tenant + 6 platform ekranı masaüstü ve mobilde (390 px) yatay taşmasız ve konsol
  hatasız; 10 etkileşimli görünüm (lot sorgusu, harita, takvim, Pareto, kanban, komut paleti) hatasız.

## 2026-09-26 denetiminde kapatılanlar

1. CI kırmızısı: 5 KVKK testi gerçek MinIO'ya çıkıyordu → bellek içi depo fikstürü; sözleşme
   testi gerçek depoyu sonraki testlere sızdırıyordu.
2. Beklenmeyen 500 CORS başlığı ve `x-request-id` olmadan dönüyordu (tarayıcıda "CORS hatası")
   → içteki saf ASGI hata katmanı + regresyon testi.
3. WebSocket JWT'si erişim loguna düz metin yazılıyordu → log maskeleme + test.
4. Mobilde her oturumlu sayfa +241 px yatay taşıyordu; menü içeriği itiyordu → duyarlı üst bar,
   katman çekmece; grafik eksen etiketleri üst üste biniyordu.
5. Bildirim üretici ve webhook relay compose'da yoktu (bildirim merkezi hiç dolmazdı).
6. Demo seed S24/S-VB/rapor modüllerini doldurmuyordu, "Tenant Yöneticisi" adıyla karşılıyordu
   ve zaman serisi seed anına sabitti (kiosk birkaç günde sıfıra düşüyordu).
7. 10 yüksek/kritik geliştirme bağımlılığı açığı (Vite 5→8, Vitest 2→5, Playwright 1.63),
   ECharts XSS (5→6.1); CI Node 20→22, action'lar v7, bağımlılık taraması CI'ya eklendi.
8. DESIGN.md Google DESIGN.md spec'ine çevrildi; README durumu 08-27'den bayattı.
9. Anomali bildirim yağmuru: `GET /tahmin/anomali` her görüntülemede outbox olayı yazıyordu
   (09-23'te bir saatte 49 olay → her yetkili kullanıcıya bildirim) → aynı makine kümesi 24 saat
   içinde tekrar bildirilmez (test). Başlık "AI anomali tespiti: " diye boş bitiyordu → makine
   kodları / bulgu sayısı.
10. Bildirim zili satırlarının CSS sınıfı hiç tanımlanmamıştı (tarayıcının gri butonu, okunaksız).
11. Sayfa başlığı aksiyonları ve 3 tablo (kritik stok, platform tenant/abonelik) dar ekranda
    sayfayı yatay kaydırıyordu.
12. Demo: lot üretim kayıtları (izlenebilirliğin son halkası boştu) ve makine konumları (coğrafi
    harita boştu) eklendi.

## Ne yarım / bilinçli açık

- S25 (tedarik zinciri) yalnız tasarım (ADR-0024). Faz 5 operasyon sprintleri (S19–S22) açık.
- Stok tahmin modeli malzeme başına ≥3 günlük gerçek tüketim ister; yeni tenant'ta bekler.
- Playwright E2E CI'da değil (çalışan yığın + seed ister).
- Uzak dallar: `feat/persona-pano-landing-derinlestirme`, `feat/s18-dis-portal-webhook`,
  `feat/s6-uretim-isemri-ekranlari`, `feat/s7-gercek-zaman` — içerik main'de; silinmesi sahibin kararı.
