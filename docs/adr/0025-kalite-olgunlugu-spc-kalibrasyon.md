# ADR-0025 — Kalite Olgunluğu: Kontrol Planı + SPC, Ölçüm Cihazı + Kalibrasyon (S26-A)

- **Durum:** Kabul edildi (S26-A, Faz 6)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0010 (kalite kontrol + CAPA), ADR-0021 (bildirim üretici), ADR-0024 (tedarikçi skoru),
  ISO 9001:2015 7.1.5, ASTM E2587 / Montgomery (*Introduction to SQC*, Ek VI)

## Bağlam

S10 kalite modülü tekil ölçümleri (geçti/kaldı) ve CAPA vakasını tutuyordu. Kurumsal QMS iki şey
daha ister: prosesin **istatistiksel olarak kararlı** olduğunu gösteren kontrol kartları ve
ölçümlerin **kalibre edilmiş ekipmanla** yapıldığının kanıtı. İkisi birbirine bağlıdır: geçersiz
cihazla girilen ölçüm kartı "kararlı" gösterebilir ama dayanağı yoktur.

S26 yol haritası İSG ve İK kalemlerini de içerir; onlar S26-B'ye ayrıldı (bu ADR yalnız kaliteyi
kapsar).

---

## 1. SPC: X̄-R kartı, saf fonksiyonlar

`app/modules/kalite/spc.py` veritabanı bilmez. Shewhart sabitleri n = 2…10 için tablodur (A2, D3,
D4, d2). X̄ kartında Western Electric kuralları 1–4, R kartında yalnız kural 1 uygulanır.

**İhlal, deseni tamamlayan noktanın indeksine yazılır.** Yeni bir alt grup geldiğinde "bu nokta
yeni bir ihlal doğurdu mu" sorusu tek indeksle cevaplanır; olay üretimi buna dayanır (§3).
Kural 2/3'te tamamlayan nokta kendisi de bölgenin ötesinde olmalıdır; aksi hâlde aynı desen
pencere kaydıkça iki kez sayılırdı (birim testte bilinen seriyle sabitlendi).

Yetenek: σ_iç = R̄/d2, Cp ve Cpk tolerans iki taraflıysa hesaplanır; tek taraflıda Cp `None`.

## 2. Limitler: faz-I sabitleme

Limitler sabitlenmemişse her ölçümde o ana kadarki tüm alt gruplardan yeniden hesaplanır; ekran
bunu "Faz-I" olarak açıkça söyler. Yeterli veri (≥ 2 alt grup; önerilen 20–25) birikince
`POST /karakteristikler/{id}/limitleri-sabitle` limitleri dondurur, sonraki ölçümler bu limitlere
göre değerlendirilir. Veri yetersizse 409 `SPC_YETERSIZ_VERI`.

**Reddedilen:** her zaman yeniden hesaplama. Kayan süreç kendi limitlerini genişletir ve
kaymayı gizler; sabitlemesiz kart kalite kanıtı değildir.

## 3. Ölçüm girişi: kalibrasyon kapısı + kenar tetikli olay

- Karakteristiğin (ya da istekteki) cihazı geçerli değilse ölçüm 422 `KALIBRASYON_GECERSIZ`.
  Geçerlilik: `aktif` ve `sonraki_kalibrasyon_tarihi >= bugün`. Kalibrasyonsuz cihaz geçersizdir.
- Alt grup sırası `SELECT … FOR UPDATE` ile karakteristik satırı kilitlenerek verilir;
  `uq(karakteristik_id, sira)` ikinci savunmadır (eşzamanlı 6 ölçüm testi).
- `kalite.spc_ihlal` outbox olayı **yalnız yeni noktanın tamamladığı** ihlaller için yazılır;
  eski ihlaller her yeni ölçümde yeniden bildirilmez.

## 4. Kalibrasyon kaydı ve cihaz durumu

Kalibrasyon kaydı sonraki tarihi `tarih + periyot` olarak yazar. Sonuç `uygunsuz` ise cihaz
`kullanim_disi` olur ve elle `aktif` yapılamaz (409 `KALIBRASYON_GEREKLI`); yeniden kullanım yeni
bir uygun kalibrasyonla mümkündür. Ekran durumu tek etikette toplar: `gecerli`, `yaklasiyor`
(30 gün), `gecmis`, `kalibrasyonsuz`, `kullanim_disi`, `hurda`.

## 5. Zamanlanmış taramalar bildirim işçisinde

`kalibrasyon.yaklasiyor` kenar tetiklidir (cihaz başına, sonraki tarih değişene kadar bir kez).
S26-A öncesinde sözleşme bitişi (`sozlesme.yaklasiyor`) ve SLA (`sla.asildi`) taramaları da yalnız
elle tetiklenen uçlardı; hiçbiri zamanlanmamıştı. Üçü `app/modules/bildirim/zamanli.py` altında
toplandı ve bildirim üreticisi bunları `--tarama-araligi` (varsayılan 900 sn) aralıkla, tenant
başına ve tarama başına ayrı transaction'da koşar. Bir taramanın hatası diğerlerini ve bildirim
turunu durdurmaz. Bakım vadesi dışarıda kaldı: olay değil iş emri üretir ve kullanıcı kimliği ister.

**Reddedilen:** ayrı bir zamanlayıcı süreci (cron/beat). Yeni bir servis ve dağıtım birimi
getirirdi; taramalar zaten kenar tetikli ve ucuz olduğu için var olan işçinin turu yeter.

## 6. Uygunsuzluk ↔ tedarikçi

`Uygunsuzluk.tedarikci_firma_id` giriş muayenesi uygunsuzluğunu firmaya bağlar. Firma tipi
`tedarikci` ya da `her_ikisi` olmalıdır (müşteri firması 422). Liste uçu bu alana göre süzer.
Tedarikçi skoru formülü (ADR-0024) değişmedi; bu bağ skora sonraki bir karar ile girebilir.

## Sonuçlar

- Yeni tablolar (tenant): `olcum_cihazlari`, `kalibrasyon_kayitlari`, `kontrol_planlari`,
  `kontrol_karakteristikleri`, `spc_alt_gruplari`; `uygunsuzluklar.tedarikci_firma_id`.
  Göç `c3e5a7f9b1d2` (up/down).
- Olay kataloğu 9 → 11 (`kalite.spc_ihlal`, `kalibrasyon.yaklasiyor`); bildirim hedefleme
  `kalite:oku` sahiplerine, derin bağlantı karta / cihaza.
- OpenAPI şema adları modüller arasında çakışıyordu (`PlanDTO` abonelikte, `CihazOlusturDTO`
  sahada); SPC DTO'ları `KontrolPlani*` / `OlcumCihazi*` olarak adlandırıldı.
- Ön yüz: Kontrol planları, plan detayı, SPC kartı (X̄ ve R grafikleri, tolerans ve kontrol
  limitleri ayrı renkte), Ölçüm cihazları, cihaz detayı + kalibrasyon kaydı. Uygunsuzluk formu
  ham kimlik kutularından makine / tedarikçi / sorumlu seçicilerine geçti.
