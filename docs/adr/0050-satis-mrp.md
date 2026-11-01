# ADR-0050 — Satış & Sipariş → MRP (S31)

- **Durum:** Kabul edildi (S31, Faz 7)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0011 (satınalma talebi, görev ayrımı), ADR-0023 (S24 ürün/reçete, BOM patlatma),
  ADR-0047 (görev ayrımı kişi düzeyinde), ADR-0049 (planlama: açılan iş emirleri çizelgeye girer).
  Yol haritası bu sprinti "ADR-0030" diye anıyordu; numara 0040'tan beri kaydığı için 0050.

Faz 7'nin üçüncü satılabilir modülü: `satis` (deneme ve kurumsal planda). Zincir:
**müşteri siparişi → malzeme ihtiyacı (BOM patlatma) → üretim iş emri + satınalma talebi**. Bu sprintle
dış portal talebinden faturaya kadar tedarik zinciri uçtan uca bağlanır (talep → sipariş → üretim/
satınalma → teslim → fatura).

## 1. Model

- `satis_siparisleri`: kod `SP-{yıl}-{id}`, CRM firması (`musteri` ya da `her_ikisi`; tedarikçiye
  sipariş açılmaz), teslim tarihi, isteğe bağlı üretim hattı (makine), isteğe bağlı dış portal talebi.
  `talep_id` **tekil**: bir portal talebi tek siparişe dönüşür.
- `satis_siparisi_kalemleri`: ürün × miktar (> 0), isteğe bağlı birim fiyat. Tutar yalnız bütün
  kalemlerin fiyatı varsa hesaplanır; eksikse "—" (0 sayılmaz).
- `mrp_tetikleri`: onayın açtığı her iş (`is_emri` / `satinalma_talebi`), `kaynak` tekil anahtarıyla.

Durum makinesi (saf): `taslak → onaylandi → sevk_edildi → kapandi`, `taslak|onaylandi → iptal`.
Yalnız taslak düzenlenir. Onaylı sipariş iptal edilirse açılan iş emirleri ve talep kendiliğinden
kapanmaz: onlar kendi sahiplerinin kararıdır (iptal onayında bu söylenir).

## 2. MRP hesabı (saf, `satis/mrp.py`)

```
brüt          = Σ kalem miktarı × reçete birim tüketimi        (tek seviye BOM, S24)
kullanılabilir = eldeki stok + açık tedarik − ayrılmış
net           = max(0, brüt − kullanılabilir)
```

- **Açık tedarik:** siparişe dönmemiş açık satınalma talepleri (taslak/onay bekliyor/onaylandı) +
  açık satınalma siparişlerinin teslim alınmamış kısmı. Talep siparişe dönünce talep değil sipariş
  sayılır (çift sayım yok).
- **Ayrılmış:** açık iş emirlerinin (ürün + miktar taşıyan) henüz stoktan düşülmemiş reçete tüketimi.
  İş emri kapanırken BOM stoktan düşer (S24); o ana kadar o malzeme başka siparişe "boş" görünmemeli.
- **Kendi tetikleri hariç:** siparişin kendi açtığı iş emirleri ayrılmış, kendi talebi açık tedarik
  sayılmaz; yoksa onaydan sonraki hesap ihtiyacı iki kez düşer.
- Reçetesi olmayan ürün patlatılamaz: `recetesiz` listesinde döner ve onay 422 verir (sessizce 0
  sayılmaz).

Reddedilen: çok seviyeli BOM ve zaman fazlı (time-phased) MRP. Reçete modeli tek seviyeli; teslim
tarihine göre gün gün projeksiyon bu ölçekte (KOBİ, tek hat) ek doğruluk getirmeden karmaşıklık ekler.
Planlama (S30) teslim tarihini iş emrine taşıdığı için kapasite tarafı orada görünür.

## 3. Onay → tetik (idempotent, görev ayrımlı)

`POST /satis-siparisleri/{id}/onayla` (`satis:onay`):

1. Sipariş satırı `FOR UPDATE` ile kilitlenir; durum `taslak` değilse 409 (eşzamanlı ikinci onay).
2. Siparişi açan kişi onaylayamaz → 403 (görev ayrımı, kişi düzeyinde).
3. Üretim hattı (onay gövdesi ya da sipariş) zorunlu; reçetesiz ürün 422.
4. Kalem başına bir **üretim iş emri** (ürün, miktar, hat, teslim günü 17:00 hedef, lot
   `SP-…-<sıra>`, öncelik yüksek) → S30 çizelgesine kendiliğinden girer.
5. Net ihtiyaç > 0 olan malzemeler için **tek satınalma talebi**, `onay_bekliyor` durumunda; talebi
   açan, siparişi onaylayan kişidir → satınalma onayını başka biri vermeli (S9 kuralı).
6. Her tetik `mrp_tetikleri.kaynak` (`ie:<kalem_id>`, `st:<siparis_id>`) tekil anahtarıyla yazılır:
   tetik yeniden çalışırsa (yeniden deneme, ikinci çağrı) var olan bulunur, yeni iş açılmaz.
7. Outbox: `satis.siparis_onaylandi` her onayda, `mrp.tetiklendi` yalnız yeni tetik oluştuğunda
   (kenar-tetikli). Bildirim: onay satış ekibine (`satis:oku`), MRP tetiği satınalma onaylayana.

Roller: `satis` (hazırlar, sevk eder, onaylayamaz), `satis-onaylayan` (+ onay ve onaylı siparişi
iptal). İkisi de `crm:oku`, `stok:oku` (MRP ekranı) ve `uretim:oku` (üretim hattı seçimi) taşır.

## 4. Doğrulama

- 18 birim (MRP + durum) + 6 entegrasyon testi: MRP sayıları (eldeki/açık tedarik/ayrılmış), onay →
  iş emri + talep içeriği, ikinci siparişin ilkinin tüketimini ve talebini görmesi, servis düzeyinde
  tetik tekrarında yeni kayıt olmaması, tedarikçi/olmayan ürün/boş kalem, RBAC (izleyici, temsilci),
  tenant izolasyonu, durum geçişleri, portal talebinin tek siparişe dönmesi, göç up/down.
- Mutasyon: `mrp.py` %100, `durum.py` %100. Koruma sökme denemesi: tetik tekilliği, görev ayrımı ve
  "kendi tetiklerini hariç tutma" tek tek kaldırıldığında testler düşüyor (3/3).
- Demo tohumu: satış temsilcisi iki sipariş açar, satış onaylayan birini onaylar → üretim emri +
  eksik profil için satınalma talebi; diğeri taslak kalır ve MRP'si ilk siparişin ayırdığı malzemeyi
  ve açtığı talebi gösterir.

## 5. Bilinen sınırlar

- Tek seviyeli reçete, tek üretim hattı (sipariş başına bir makine); operasyon rotası yok.
- Satış fiyatı/tutarı siparişte bilgi amaçlı; faturaya otomatik dönüşüm yok (finans S29 elle).
- Dış portal kullanıcısı siparişi göremez; portal talebi iç tarafta siparişe bağlanır.
- Stok rezervasyonu (fiziksel ayırma) yok: "ayrılmış" yalnız açık iş emirlerinin hesaben tüketimidir.
