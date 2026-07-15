# ADR-0023 — Üretim & Bakım Derinleşmesi: Vardiya, Duruş, Ürün/BOM, İzlenebilirlik, MTBF/MTTR (S24)

- **Durum:** Kabul edildi (S24, Faz 6)
- **Tarih:** 2026-07-15
- **İlgili:** ADR-0004 (OEE saf çekirdek), ADR-0007 (outbox), ADR-0011 (stok hareket çekirdeği),
  ADR-0021 (SLA/bakım takvimi)

## Bağlam

Üretim ve bakım modülleri MVP seviyesindeydi: OEE kullanılabilirliği yalnızca üretim
verisindeki manuel `durus_sure_dk` alanından besleniyordu, iş emri hiçbir ürüne bağlı
değildi (malzeme tüketimi elle giriliyordu), lot/parti takibi yoktu ve bakım planları
yalnız CRUD idi (vadesi gelen plan iş emri üretmiyordu). MES olgunluğu için beş kalem
tek dikey dilimde ele alındı.

## Karar

1. **Vardiya kataloğu:** `vardiyalar` tablosu (ad UNIQUE, saat aralığı). Üretim verisindeki
   serbest metin `vardiya` kolonu (S3'ten beri var) **değiştirilmedi** — katalog FE
   seçeneklerini ve OEE vardiya kırılımını besler. `GET /makineler/{id}/oee?vardiya=` ve
   `GET /oee/ozet?vardiya=` filtre olarak alır; geriye uyumlu (filtre yoksa davranış aynı).
2. **Duruş yönetimi:** `durus_nedenleri` kataloğu (planlı/plansız sınıfı) + `durus_kayitlari`
   (makine, aralık, neden; `bitis > baslangic` 422). OEE kullanılabilirliği artık **kayıtlı
   duruşlardan da** düşer: pencere-içi kesişim dakikaları `durus_sure_dk` toplamına eklenir;
   `oee_hesapla` saf çekirdeği **değişmeden** korunur (girdi kaynağı zenginleşti — ADR-0004
   sözleşmesi). Belgelenmiş sınır: kayıtlı duruşlar vardiyaya bağlanmaz; `?vardiya=` filtreli
   sorguda yalnız üretim verisi duruşu sayılır. `GET /durus/pareto?gun=` neden bazında
   toplam dk + yüzde + kümülatif yüzde döner (saf `pareto_hesapla`, birim testli;
   sıfır-toplamda boş liste — bölme hatası imkânsız).
3. **Ürün & Reçete (BOM):** `urunler` + `receteler` (ürün başına TEK reçete — UNIQUE
   `urun_id`, sürümleme Faz 6+ ertelendi) + `recete_kalemleri` (malzeme FK RESTRICT,
   `UNIQUE(recete_id, malzeme_id)`). Reçete `PUT /urunler/{id}/recete` **replace-all**
   (ikiz yerleşim deseni). İş emrine opsiyonel `urun_id + miktar + lot_no` bağlanır;
   **kapanışta BOM patlatma** (`urun.service.bom_patlat`) kapanışla aynı transaction'da
   `recete.miktar × is_emri.miktar` kadar stok çıkışı üretir (S9 `stok_hareketi_uygula`
   yeniden kullanımı — kritik eşik kenar-tetiği dahil). İdempotency iki katman: durum
   makinesi terminalden çıkışı zaten engeller; hareket `bom-{is_emri_id}-{malzeme_id}`
   idempotency anahtarı taşır. **Yetersiz stok kapanışı 422 ile durdurur** — transaction
   bütünüyle geri alınır, iş emri açık kalır (negatif bakiye yazılamaz).
4. **İzlenebilirlik:** `is_emirleri.lot_no` + `uretim_verileri.lot_no` (indeksli) +
   `GET /izlenebilirlik?lot=` — tek uçta ileri/geri zincir: lotu üreten iş emirleri →
   BOM tüketim hareketleri (`kaynak='bom:{id}'` bağı = **geri izleme**) + makine bazında
   üretim kayıtları (= **ileri izleme**).
5. **Bakım olgunluğu:**
   - **Arıza kaydı otomasyonu:** makine `ariza` durumuna geçişte açık `ArizaKaydi` açılır,
     arızadan çıkışta kapanır (S18 `ariza.olustu` kenar-tetiğiyle aynı transaction).
   - **MTBF/MTTR:** saf `mtbf_mttr_hesapla` (birim testli): MTTR = kapanan arızaların
     ortalama onarım saati (açık arıza MTTR'a girmez); MTBF = (pencere − arıza süresi) /
     arıza sayısı; arıza yoksa ikisi de `None` ("arıza yok" ≠ "MTBF 0").
     `GET /bakim/metrikler?makine_id=&gun=`.
   - **Otomatik bakım iş emri:** `POST /bakim-planlari/vade-tara` kenar-tetikli; bir-kez
     garantisi İKİ katman: plan başına açık otomatik iş emri (`is_emirleri.bakim_plani_id`)
     varsa üretmez + üretim sonrası vade `periyot_gun` kadar ileri atılır (periyotsuz plan
     tek seferlik — vade temizlenir).
   - **Yedek parça = malzeme:** `bakim_planlari.yedek_parca_malzeme_id` nullable FK.
   - `is_emirleri.ariza_kaydi_id` — arıza ↔ bakım iş emri bağı.

## Sonuçlar

- Migration `c4a7f3e9b528` (tenant, fan-out up/down testli): 6 yeni tablo
  (`vardiyalar`, `durus_nedenleri`, `durus_kayitlari`, `urunler`, `receteler`,
  `recete_kalemleri`) + `is_emirleri`ne 5, `uretim_verileri`ne 1, `bakim_planlari`na
  1 kolon.
- **Yeni izin yok:** yeni uçlar mevcut `uretim:*` / `bakim:*` izinlerine bağlandı
  (vardiya/duruş/ürün üretim ailesidir; ayrı izin gerektirecek görev ayrımı yok).
- Yeni modüller `vardiya`, `durus`, `urun` **router seviyesinde** ayrıdır ama entitlement
  kapısı `uretim` modülüdür (katalog değişmedi — bunlar üretim yeteneğinin parçası).
- Async SQLAlchemy dersi: yeni oluşturulan üst kayda flush sonrası koleksiyon `append`'i
  lazy-load tetikler (`MissingGreenlet`) → koleksiyon kurucuda `kalemler=[]` ile başlatılır.
- FE: `/vardiyalar`, `/durus-kayitlari` (pareto), `/urunler` (BOM editörü),
  `/izlenebilirlik` (zincir görünümü); makine detayına MTBF/MTTR kartları; iş emri
  formuna ürün/miktar/lot alanları (uiplani §11.3 S24 sözleşmesi).
