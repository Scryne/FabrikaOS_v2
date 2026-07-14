# ADR-0021 — Vitrin Bütünlüğü: Bildirim Merkezi Çekirdeği + SLA + Operatör Eşleştirme + Tedarikçi Skoru + Coğrafi Harita (S-VB)

- **Durum:** Kabul edildi (S-VB, Faz 4B köprü)
- **Tarih:** 2026-07-15
- **İlgili:** ADR-0007 (outbox), ADR-0009 (gerçek-zaman), ADR-0015 (AI çıkarım), ADR-0020 (webhook)
- **Tasarım:** `docs/superpowers/specs/2026-07-11-svb-vitrin-butunlugu-design.md`

## Bağlam

`/tanitim` vitrini müşteriye bildirim, SLA, AI operatör eşleştirme, tedarikçi skoru ve
coğrafi harita gibi **görünür** özellikler vaat ediyordu; bunlar kodda yoktu
(truth-in-advertising borcu). Kurumsal-tam sürümleri Faz 6'da derinleşecek; köprü sprintin
amacı **vitrin ↔ gerçek örtüşmesini** demo-yeterli çekirdekle sağlamaktı.

## Karar

Yedi kalem tek dikey dilimde, **yeni çekirdek icat etmeden** teslim edildi:

1. **Bildirim Merkezi (çekirdek):** `bildirimler` + `bildirim_tercihleri` + `bildirim_imleci`
   tabloları; outbox'tan beslenen **ayrı süreç üretici** (`scripts/bildirim_uretici.py`,
   webhook relay deseni). İki tüketici tek outbox'ı çakışmasız okur: relay
   `giden_olaylar.durum`'u, üretici bağımsız `bildirim_imleci` yüksek-su-işaretini kullanır.
   İdempotency iki katmanlı: imleç pencereyi daraltır; `UNIQUE(kullanici_id, giden_olay_id)`
   (ON CONFLICT DO NOTHING) çift bildirimi yapısal önler. Hedefleme saf kural tablosuyla
   (`hedefleme.py`): sistem olayları **izne göre** (ör. `stok.kritik` → `stok:oku`
   sahipleri), kişi-hedefli olaylar gövde alanıyla (`rapor.hazir` → oluşturan). Kanallar:
   uygulama-içi otoritedir; e-posta SMTP iskeleti (stdlib `smtplib`, `smtp_host` boş =
   kapalı), SMS stub. Kanal hatası bildirimi düşürmez. Uçlar kişisel yüzeydir (oturum
   yeter, izin/modül kapısı YOK — duyuru gibi çapraz-kesen); kişisel süzgeç repository
   imzasında `kullanici_id` olarak zorlanır. FE: kabuk zili (rozet + panel + canlı
   `bildirim.yeni` invalidasyonu) + `/bildirim-tercihleri` ekranı.
2. **SLA takibi:** `is_emirleri.hedef_tarih` + `talepler.hedef_tarih` (boş = takip yok);
   `POST /is-emirleri/sla-tara` + `POST /talepler/sla-tara` kenar-tetikli tarama.
   **Dedup outbox'un kendisinden** sorgulanır (`core/sla.py`: `olay_turu='sla.asildi' ∧
   govde->>kaynak_tur ∧ kaynak_id`) — kaynak tabloya bayrak kolonu eklemek yerine olay
   geçmişi tek doğruluk kaynağı. `sla.asildi` webhook kataloğuna girdi (8 → 9).
   Talep SLA'sında `cozuldu` karşılanmış sayılır (yalnız `acik`/`inceleniyor` taranır).
3. **AI operatör eşleştirme:** `POST /tahmin/operator-eslesme` (`ai:oku`) — model
   artefaktsız, kural-tabanlı saf skor (0.5 departman uygunluğu + 0.3 geçmiş kapanış
   performansı + 0.2 müsaitlik); kesin sıralı (`-skor, personel_id`), boş girdide bölme
   hatası imkânsız. Beceri matrisi (S26) ve vardiya (S24) ile derinleşecek.
4. **Tedarikçi performans skoru:** `GET /firmalar/{id}/skor` (`crm:oku`) — saf fonksiyon
   `40·kalite + 30·sözleşme + 30·talep` (0–100); sinyalsiz bileşen nötr 0.5 + dürüst
   `yetersiz_veri` işareti. **Şema tamamlaması:** spec formülünün gerektirdiği bağlantılar
   yoktu → `malzemeler.tedarikci_firma_id` + `kalite_kontrolleri.malzeme_id` nullable FK
   olarak eklendi (S25 PO hazırlığıyla örtüşür). `zamaninda_teslim` alanı S25'te dolacak
   (bugün `None`).
5. **Coğrafi site haritası:** `makineler.enlem/boylam` (nullable) + `PATCH /makineler/{id}`
   genel güncelleme ucu; `/ikiz/durum` koordinat taşır. FE `/ikiz` "Harita" sekmesi
   (react-leaflet 4 + OSM karo; işaretçi = durum LED rengi `CircleMarker`). **Not:** public
   OSM karo dev içindir; prod'da tenant gizliliği için self-host/ücretli karo servisi
   değerlendirilecek (S19/S22 operasyon kalemi).
6. **Takvim görünümü:** FE-only — `/bakim-planlari` "Takvim" sekmesi (AntD Calendar):
   aktif planların sonraki bakım vadesi + (ik:oku varsa) onaylı izinler. Gün anahtarı
   **yerel** formatlanır (toISOString UTC kayması gün kaydırıyordu — testle yakalandı).
7. **Duyuru outbox'u:** `duyuru.yeni` artık gerçek-zaman sinyaline ek **outbox olayı**
   olarak da yazılır (bildirim üreticinin dayanıklı kaynağı; boş `olay_turleri` listeli
   webhook aboneliği bu olayı da alır — kabul edilen yan etki).

## Sonuçlar

- Migration `b3e7c5f9a284` (tenant, fan-out up/down testli): 3 tablo + 8 kolon.
- Katalog/rol değişmedi; **yeni izin yok** (bildirim kişisel yüzey; diğerleri mevcut izinler).
- 7 kritik test ailesine **bildirim tenant-izolasyonu** eklendi (A'nın olayı B'nin
  kullanıcısına asla bildirim üretmez).
- Landing "27 modül" hizalaması Faz 7 kapanışına bırakıldı (katalog 19 → 23 olunca tek
  seferde dürüst sayı yazılacak).
- Operasyon: bildirim üretici ayrı süreçtir — `python backend/scripts/bildirim_uretici.py`
  (relay ile birlikte çalıştırılır; `--tek-tur` e2e determinizmi).
