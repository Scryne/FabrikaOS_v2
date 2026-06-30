# ADR-0010: Edge & Ingestion — MQTT topic-per-tenant + edge-side agregasyon + store-and-forward

Durum: Kabul
Tarih: 2026-06-30

## Bağlam
Faz 2 / S8 sahadan **otomatik** veri akışı gerektirir: PLC/sayaç → bulut → OEE panosu, elle
giriş olmadan. Kısıtlar: (R3) ingestion tenant-aware olmalı, çapraz-tenant sızıntı olmamalı;
(R5) saha bağlantısı kopunca veri kaybolmamalı (store-and-forward). Donanım bağımlılığı
olmadan uçtan uca test edilebilir olmalı (kabul kriteri "simüle PLC verisi" der).

Mevcut altyapı: `uretim_verileri` TimescaleDB hypertable OEE girdilerini taşıyor (S3); OEE
özeti/pano bu tabloyu okuyor (S6/S7); Redis pub/sub gerçek-zaman katmanı hazır (ADR-0009).

## Karar
- **Edge Gateway Agent (`edge/`, bağımsız paket; backend `app`'i import etmez).** Pluggable
  `SahaSurucu` arayüzü (`oku() -> list[HamOkuma]`). MVP'de **simülasyon sürücüsü** yazılır;
  `opcua`/`modbus` belgelenmiş **adaptör iskeleti** (seam), gerçek implementasyon Faz 5.
- **Edge-side agregasyon.** Ajan ham sayaç görüntülerini periyodik okur, önceki okumayla
  fark alıp **aralık özeti** üretir (mevcut `UretimVerisi` şekli + `olcum_id` UUID). Böylece
  veri doğrudan `uretim_verileri`'ne yazılır → OEE hattı (S3/S6/S7) **değişmeden** çalışır.
  Ham sinyal saklama + ayrı agregasyon (continuous aggregate) bilinçli olarak ertelendi (S10/S19).
- **Taşıma: MQTT, topic `fabrikaos/<tenant_slug>/<cihaz_kod>/olcum` (QoS 1).** Tenant
  yönlendirmesi **topic'ten** çözülür; ingestion slug'ı alır, tenant aktif mi + cihaz
  kayıtlı/aktif + makine eşlemesi doğrular. Bilinmeyen → düşür + logla (yazma yok). Bir gateway
  **N makine** köprüleyebilir (cihaz makineye sabit FK ile bağlı değil; ölçüm `makine_kod` taşır).
- **Store-and-forward (kayıpsızlık).** Edge'de dayanıklı yerel kuyruk (stdlib `sqlite3`):
  paket önce tampona yazılır, MQTT PUBACK'te silinir. Broker erişilemezken paketler tamponda
  birikir, reconnect'te ekleme sırasıyla replay edilir. Süreç yeniden başlasa veriler kalır.
- **Idempotency (çift-sayma önleme).** Replay'de aynı paket iki kez gelebilir; bulutta
  tenant şemasındaki `saha_alinan_olcum (olcum_id UUID PK)` defterine `ON CONFLICT DO NOTHING`
  ile işaretlenir — çakışan paket atlanır, `uretim_verileri`'ne ikinci kez yazılmaz.
- **Ayrı Ingestion Worker (`app.ingestion`, aiomqtt).** `fabrikaos/+/+/olcum`'a abone; her
  mesaj için `tenant_slug_ctx`/`request_id_ctx` set (log korelasyonu, §3.7), tenant oturumu +
  `search_path`, idempotent yaz, sonra makine-bazlı `uretim.eklendi` realtime olayı (ADR-0009).
  Hata izole: tek bozuk mesaj döngüyü düşürmez. Yazma servisi (`olcum_yaz_toplu`) gerçek-zaman
  yayınından **ayrıştırıldı** (çağıran yayınlar) → broker'sız birim test edilebilir.
- **Üç ingestion yöntemi, tek yazma yolu.** (a) MQTT (worker), (b) REST `POST /saha/olcumler`
  (`edge` izni, toplu/batch), (c) CSV `POST /saha/olcumler/csv` — hepsi aynı `olcum_yaz_toplu`'ya
  gider. Cihaz yönetimi: `GET/POST /saha/cihazlar` (`saha:oku`/`saha:yaz`, audit).
- **Auth (MVP).** REST ingestion için `edge` RBAC izni (servis hesabı; `saha-cihaz` rolü).
  Dev'de mosquitto anonim → registry doğrulama tek kapı. MQTT-seviyesi **mTLS/credential
  Faz 5'e ertelendi** (donanım/sertifika zinciri gerekir).

## Sonuçlar
- (+) Simüle PLC → MQTT → ingestion → `uretim_verileri` → OEE panosu **elle giriş olmadan**
  akar; gerçek broker'a karşı round-trip testi kanıtlar (`test_s8_mqtt_roundtrip.py`).
- (+) Tenant izolasyonu topic + registry doğrulamasıyla; `olcum_yaz_toplu` izolasyon testli.
- (+) Store-and-forward kayıpsız + idempotency çift-saymayı önler (edge tampon + bulut defter,
  iki kat güvence); birim testli (`edge/tests/test_tampon.py`, `test_s8_service.py`).
- (+) OEE hattı dokunulmadan yeniden kullanıldı; ham sinyal katmanı eklenmedi (YAGNI).
- (−) Dev'de MQTT anonim → broker-seviyesi kimlik yok; registry tek savunma. mTLS Faz 5.
- (−) `saha_alinan_olcum` defteri sınırsız büyür → retention S19/S20'de ele alınacak.
- (−) Worker mesaj alıp DB yazımı arasında çökerse o mesaj kaybolabilir (mosquitto dev'de
  `persistence false`); edge-disconnect senaryosu (kabul kriteri) tampon ile kayıpsız. Broker
  kalıcılığı + manuel ack ile worker-crash dayanıklılığı Faz 5 sertleştirme notu.

## Notlar
- Plan'da Edge ADR'si "ADR-0007" olarak anılmıştı; o numara S4 (durum makinesi + outbox)
  tarafından alındığından Edge ADR'si sıradaki boş numaraya (**0010**) kaydı.
- Windows yerel çalışma: aiomqtt/paho ProactorEventLoop'ta soket kaydını desteklemez; worker
  ve edge `main()` (ve test conftest'i) Windows'ta `WindowsSelectorEventLoopPolicy`'ye geçer —
  Linux CI zaten SelectorEventLoop kullandığından davranış hizalı.
