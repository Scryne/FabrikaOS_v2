# ADR-0007: İş emri durum makinesi + domain olayları için transactional outbox

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
İş emirleri (`is_emirleri`) bir yaşam döngüsüne sahiptir: açılır, atanır, ilerletilir,
kapatılır (veya iptal edilir). Geçersiz geçişler (örn. kapanmış bir emri yeniden "devam
ediyor" yapma) engellenmelidir. Ayrıca iş emri kapandığında, dış sistemlere (webhook;
gerçek teslimat S18) iletilecek bir `is_emri.kapandi` domain olayı üretilmelidir. Bu olayın
**kaybolmaması** ve iş ile **tutarlı** olması gerekir (emir kapandıysa olay da kalıcı olmalı).

## Karar
- **Durum makinesi saf bir modüldür** (`modules/isemri/durum.py`): geçiş tablosu (`GECISLER`)
  ve `gecis_gecerli_mi`/`gecerli_hedefler` saf fonksiyonları; DB/IO yok → kapsamlı birim
  testleri. Akış: `acik → atandi → devam_ediyor → kapandi`; her aktif aşamadan `iptal`.
  `kapandi`/`iptal` **terminaldir** (çıkış geçişi yok, yeniden açma yok).
  - Geçersiz geçiş → **409 Çakışma**; tanımsız hedef durum → **422**.
  - `atandi`'ya geçiş `atanan_kullanici_id` gerektirir (422). Atama, `Personel` modeli
    henüz olmadığından (S11) giriş yapan `Kullanici`'ya yapılır (nullable FK).
- **Eşzamanlılık güvenliği:** durum geçişinde iş emri satırı `SELECT … FOR UPDATE`
  (`with_for_update`) ile kilitlenir. Böylece iki eşzamanlı "kapat" isteği seri hâle gelir
  ve **çift `is_emri.kapandi` olayı** (çift webhook) oluşmaz.
- **Transactional outbox** (`core/olaylar.py` → `giden_olaylar` tablosu): olay, onu üreten
  iş ile **aynı transaction'da** `durum='beklemede'` satırı olarak yazılır (`olay_yayinla`).
  Dual-write sorunu yoktur: iş commit olduysa olay kalıcıdır, rollback olduysa olay da gider.
  - Teslimat (imzalama + retry + HTTP POST) bu sprintte **YOK**; S18'de bir relay
    `beklemede` satırlarını okuyup teslim edecek. `dis_anahtar` (UUID) dış tüketici
    idempotency'si içindir.
  - Tablo tenant şemasındadır (TimescaleDB değil, normal tablo) → olaylar da kiracı-izole.
- **Otomatik iş emri numarası:** `kod` boş bırakılırsa servis `IE-{yıl}-{id:06d}` üretir
  (id flush sonrası bilinir; geçici tekil koddan kalıcıya güncellenir). İstemci kendi
  kodunu da verebilir (tekil).

## Sonuçlar
- (+) Geçiş kuralları tek noktada (saf modül), test edilebilir ve yeniden kullanılabilir.
- (+) Outbox sayesinde olaylar güvenilir ve iş ile atomik; S18 yalnızca teslimatı ekler.
- (+) Satır kilidi, durum makinesi + outbox kombinasyonunu çift-olaya karşı korur.
- (+) `giden_olaylar` jeneriktir; `stok.kritik`, `ariza.olustu` gibi olaylar da yeniden
  kullanacak (S9+).
- (−) Outbox satırları S18'e dek tüketilmez (o zamana kadar yalnızca birikir); relay ve
  retention S18/S19'da eklenecek.
- (−) Atama `Personel` yerine `Kullanici`'ya yapılıyor; S11'de `Personel` gelince eşleme/
  göç gerekebilir (bilinçli ertelendi).

> Not: Plan taslağında "ADR-0007" Edge+MQTT için anılmıştı; ADR'ler oluşturulma sırasına
> göre numaralandığından S4 bu numarayı aldı, Edge ADR'si S8'de bir sonraki numarayı alır.
