# ADR-0013: İSG (iş kazası + risk matrisi) & İK (personel + izin onay akışı) + KVKK

Durum: Kabul
Tarih: 2026-07-04

## Bağlam
Faz 2 / S11 çekirdeğin üzerine iki iş modülü ekler: **İSG** (İş Sağlığı ve Güvenliği —
iş kazası/ramak-kala + risk değerlendirme) ve **İK** (İnsan Kaynakları — personel özlük +
izin talebi + fazla mesai + zimmet + sertifika). İK özlük verisi **KVKK** (kişisel veri)
kapsamındadır; veri minimizasyonu + erişim kısıtı gerekir.

Mevcut altyapı yeniden kullanılır: şema-başına-tenant + `search_path` (ADR-0003), Alembic
iki-ağaç fan-out (ADR-0004), RBAC izin/rol kataloğu (ADR-0005), transactional outbox + saf
durum makinesi (ADR-0007), görev ayrımı ayrı onay izni (ADR-0011 satınalma), Redis pub/sub
gerçek-zaman (ADR-0009).

## Karar
- **Risk matrisi (saf).** `RiskDegerlendirme` girişleri `olasilik` ve `siddet` (her ikisi
  1..5); `risk_skoru = olasilik × siddet` ve `risk_seviyesi` (`dusuk`/`orta`/`yuksek`/
  `cok_yuksek`, eşikler 4/9/15/25) **sunucuda** `isg/risk_matrisi.py` saf fonksiyonuyla
  hesaplanır (istemciye güvenilmez; kapsamlı birim testli). Güncellemede olasılık/şiddet
  değişirse skor/seviye yeniden hesaplanır.
- **İş kazası + domain olayı.** `IsKazasi` tür (`kaza`/`ramak_kala`/`meslek_hastaligi`) ve
  ağırlık (`hafif`/`orta`/`agir`/`olumcul`) beyaz-listeleriyle doğrulanır; oto kod `KZ-{yıl}-
  {id:06d}`. Kaza açılışında `isg.kaza` domain olayı transactional outbox'a yazılır (İSG
  olayları webhook/bildirim için kritiktir) + realtime yayını.
- **İzin talebi onay akışı.** `IzinTalebi` saf durum makinesiyle (`ik/izin_durum.py`,
  satınalma aynası) yönetilir: `taslak → onay_bekliyor → onaylandi/reddedildi` (+ `iptal`);
  terminalden çıkış yok. Durum geçişi `FOR UPDATE` satır kilidiyle yapılır (çift onay önler).
  **Onay/red ayrıca `ik:onay` iznini ister** (görev ayrımı: talep açan onaylayamaz) — S9
  `satinalma:onay` deseniyle aynı. `gun_sayisi` başlangıç/bitiş dâhil sunucuda hesaplanır.
  Fazla mesai onayı da `ik:onay` ister.
- **KVKK — özlük minimizasyonu + erişim kısıtı.** `Personel.tc_kimlik_no` saklanır ama API
  yanıtlarında **maskelenir** (`tc_maskele`: yalnız son 2 hane, `*********01`); maskesiz TC
  hiçbir uçtan dönmez. Tüm İK okuma `ik:oku`, yazma `ik:yaz` ister → yetkisiz erişim 403
  (erişim kısıtı). Fazla veri toplanmaz (minimizasyon): yalnız operasyonel özlük alanları.
- **Modüller arası referans.** `is_kazalari.personel_id` (İSG → İK) ve tüm İK yardımcı
  tabloları `personel.id`'ye FK verir (`search_path` çözer, şema öneki yazılmaz). Migration'da
  `personel` tablosu **önce** oluşturulur (bağımlılık sırası).
- **RBAC.** `isg:oku/yaz`, `ik:oku/yaz` katalogda zaten vardı; `ik:onay` eklendi. Görev
  rolleri: `isg` (isg:oku/yaz), `ik` (ik:oku/yaz — **onay yok**), `ik-onaylayan`
  (ik:oku/onay).

## Sonuçlar
- (+) Risk matrisi skoru/seviyesi, izin onay akışı + geçersiz geçiş 409, `ik:onay` 403
  (görev ayrımı), KVKK TC maskeleme + erişim kısıtı ve migration fan-out up/down entegrasyon
  testli ve kalıcı (+47 backend testi → 226).
- (+) İSG kazası domain olayı outbox'ta → S18 webhook için hazır (`isg.kaza`).
- (+) Üretim/OEE hattı ve diğer modüller S11'den **etkilenmez**; İSG/İK ayrık modüllerdir.
- (−) TC maskeleme uygulama katmanındadır; DB'de ham TC durur (tam KVKK için sütun şifreleme/
  ayrı erişim rolü Faz 5 sertleştirmeye bırakıldı, YAGNI).
- (−) İzin bakiyesi (`yillik_izin_hakki`) kaydedilir ama onayda otomatik düşülmez (bakiye
  muhasebesi sonraki iterasyona ertelendi).

## Notlar
- Migration `d5c8e1f0a927` (down `b7e4c2f9a016`); 7 tablo (`personel`, `is_kazalari`,
  `risk_degerlendirmeleri`, `izin_talepleri`, `fazla_mesailer`, `zimmetler`, `sertifikalar`),
  hypertable/CAGG yok; `public` + ≥2 tenant şemasında fan-out up/down testli
  (`test_s11_migration.py`).
- Uçlar: `/is-kazalari`, `/risk-degerlendirmeleri`, `/personeller`, `/izin-talepleri`
  (+`/gonder|onayla|reddet|iptal`), `/fazla-mesailer` (+`/onayla`), `/zimmetler` (+`/iade`),
  `/sertifikalar`. Realtime olayları: `isg.kaza`, `isg.risk`, `ik.izin`.
- Ertelenen: TC sütun şifreleme + ayrı hassas-veri erişim rolü (Faz 5); izin bakiyesi
  muhasebesi; İSG kazası → iş emri/CAPA otomatik köprüsü.
