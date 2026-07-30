# ADR-0024 — Tedarik Zinciri Derinleşmesi: Depo/Lokasyon, Transfer, Sayım, PO/Teslim Alma (S25)

- **Durum:** Kabul edildi (S25, Faz 6)
- **Tarih:** 2026-07-31
- **İlgili:** ADR-0011 (stok & satınalma çekirdeği), ADR-0023 (BOM patlatma, izlenebilirlik),
  ADR-0014 (CRM `Firma` = tedarikçi), ADR-0016 (ReportLab)

## Bağlam

S9 stok çekirdeği tek boyutluydu: `Malzeme.mevcut_stok` tek bir tutulan bakiye, hareketler
lokasyonsuz. WMS olgunluğu için depo/lokasyon boyutu, transfer, sayım ve satınalma siparişi
(PO) → teslim alma zinciri gerekiyor. Bu dört alanın hepsi **eşzamanlılık ve idempotency**
açısından risklidir; kararlar aşağıda gerekçeleriyle sabitlenmiştir.

---

## 1. Sayım: mutlak değer DEĞİL, **delta** uygulanır

**Sorun.** Sayım açıkken stok hareketleri durmaz. Onay anında sayılan miktar *mutlak*
bakiye olarak yazılırsa, sayım süresince yapılan her hareket sessizce silinir:

```
t0  bakiye 100 · sayım satırı açılır, fiziksel sayım 95
t1  üretimden 50 giriş  → bakiye 150
t2  sayım onaylanır, "95" MUTLAK yazılır → bakiye 95   ← 50 birim buharlaştı
```

**Karar.** Sayım satırı açılırken **sistem miktarı anlık görüntülenir**
(`SayimSatiri.sistem_miktari`). Onayda:

```
fark = sayilan_miktar − sistem_miktari          (satır açıldığı andaki fark)
yeni_bakiye = o_anki_bakiye + fark              (delta olarak uygulanır)
```

Yukarıdaki örnekte: fark = 95 − 100 = −5 → 150 + (−5) = **145**. t1'deki 50 girişi korunur
ve sayımın tespit ettiği −5 fark da uygulanır. İkisi birbirini ezmez.

**Neden dondurma (freeze) değil?** Lokasyonu sayım boyunca kilitlemek üretimi durdurur;
çalışan bir fabrikada kabul edilemez. Delta yaklaşımı dondurma gerektirmez. (Dondurma
isteyen müşteri için lokasyon bazlı `sayim_kilidi` bayrağı ertelenmiş iştir.)

**Kabul testi:** sayım satırı açılır → araya stok hareketi girer → onay → hareketin
korunduğu ve farkın uygulandığı sayısal olarak doğrulanır.

> ⚠️ **Mevcut kodda aynı hata var (S9).** `stok_hareketi_uygula` içindeki `duzeltme` türü
> `return miktar  # mutlak sayım sonucu` ile **mutlak** yazıyor. Bu uç zaten yayında
> olduğundan davranışı sessizce değiştirmek kırıcıdır → `REFACTOR-BACKLOG.md`'ye işlendi.
> S25 sayım akışı bu türü KULLANMAZ; yeni `sayim_duzeltme` türü delta uygular.

---

## 2. Transfer: iki bacak + **deterministik kilit sırası**

`Depo` → `Lokasyon` hiyerarşisi; bakiye artık `stok_bakiyeleri(malzeme_id, lokasyon_id,
lot_no)` satırlarında tutulur. Transfer tek transaction'da iki bacak yazar (çıkış + giriş).

**Sorun.** A→B ve B→A transferleri aynı anda koşarsa, `FOR UPDATE` kilitleri **geliş
sırasına** göre alınırsa klasik kilitlenme (deadlock) oluşur: T1 A'yı kilitler B'yi bekler,
T2 B'yi kilitler A'yı bekler.

**Karar.** Kilitler **her zaman sabit bir sırada** alınır: `(malzeme_id, lokasyon_id)`
demetine göre **artan sıralama**. Transferin yönü ne olursa olsun her iki taraf da aynı
sırayı kullandığı için döngüsel bekleme oluşamaz.

```python
for anahtar in sorted([(malzeme_id, kaynak_lok_id), (malzeme_id, hedef_lok_id)]):
    ...SELECT ... FOR UPDATE
```

**Kabul testi:** A→B ve B→A transferleri **eşzamanlı** koşturulur; deadlock oluşmadığı ve
son bakiyelerin doğru olduğu doğrulanır.

---

## 3. Teslim alma: idempotent + açık **fazla teslim** politikası

**İdempotency.** Teslim alma `teslim-{po_kalem_id}-{irsaliye_no}` idempotency anahtarı
taşır (S9 `stok_hareketleri.idempotency_anahtari` UNIQUE alanı yeniden kullanılır). Aynı
irsaliyenin ikinci gönderimi **yeni hareket üretmez**, mevcut sonucu döner.

**Fazla teslim politikası (açıkça tanımlı).**

| Durum | Davranış |
|---|---|
| Kümülatif teslim ≤ sipariş miktarı | Kabul |
| Sipariş miktarını aşan ama tolerans içinde | Kabul + `fazla_teslim=True` işareti + denetim kaydı |
| Toleransı aşan | **422 reddedilir** (`FAZLA_TESLIM`) |

Tolerans `SatinalmaSiparisiKalemi.fazla_teslim_toleransi_yuzde` alanındadır, **varsayılan 0**
(katı). Kontrol **kümülatiftir**: kısmi teslimlerin toplamı üzerinden hesaplanır, tek tek
değil — üç ayrı %5'lik fazla teslim toplamda %15 yapar ve reddedilir.

**İade / ters çevirme.** `TeslimAlma.iade_edilen_id` ile orijinal teslime bağlı ters kayıt:
stoktan çıkış yazar, PO'nun teslim alınan miktarını azaltır. İade de idempotency anahtarı
taşır (`iade-{teslim_id}`); iade edilen miktar orijinali aşamaz (422).

---

## 4. Lot / döküm (heat) numarası ve malzeme sertifikası — **şimdi yapısal, sonra işlevsel**

**Bağlam.** Metal ve ağır sanayide döküm/parti numarası ile **EN 10204 3.1 malzeme
sertifikası** izlenebilirliği sözleşmesel zorunluluktur. S24 üretim tarafına `lot_no`
ekledi (`is_emirleri`, `uretim_verileri`), ancak **stok tarafında lot boyutu yok**.

**Risk.** Lokasyon boyutu bu sprintte ekleniyor. Lot boyutu sonraki bir sprintte eklenirse
`stok_bakiyeleri` birincil anahtarı ve tüm bakiye geçmişi **yeniden yapılandırılmak**
zorunda kalır — çalışan sistemde riskli, pahalı bir migration.

**Karar (yapısal olarak şimdi).** Bakiye anahtarı **baştan üç boyutlu** kurulur:

```
stok_bakiyeleri(malzeme_id, lokasyon_id, lot_no)   UNIQUE
stok_hareketleri.lot_no                            (nullable → '' varsayılan)
```

`lot_no = ''` "lot takibi yapılmayan malzeme" demektir ve bugünkü davranışın birebir
karşılığıdır. Lot takibi açıldığında **hiçbir yapı değişmez**, yalnız değer dolmaya başlar
(tamamen eklemeli).

`Malzeme.lot_takipli` (bool, varsayılan `False`) bayrağı da şimdi eklenir: açıksa giriş
hareketleri lot numarası ister (422), kapalıysa `''` kullanılır.

**Roadmap yerleşimi (işlevsel katman).** Lot **genealojisi** (stok lotu ↔ üretim lotu
zinciri, ileri/geri izleme birleşimi) ve **sertifika yönetimi** (EN 10204 3.1 belgesi
yükleme, lota bağlama, müşteriye sevk belgesiyle verme) **S26'ya (Kalite/QMS)** önerilir:
sertifika saklama S26'daki `OlcumCihazi`/kalibrasyon sertifikası ve DYS `Belge` desenleriyle
aynı yapıdadır; kalite modülünün doğal parçasıdır. S25 yalnız **veri boyutunu** açar.

---

## 5. Negatif stok: **katı biçimde engellenir** (bayrak yok)

Mevcut davranış korunur: çıkış hareketi bakiyeyi negatife düşürecekse **422 "Yetersiz
stok"**. Bu kural S25'te transfer, sayım düzeltmesi ve iade için de aynen geçerlidir.

**Neden per-tenant bayrak eklenmiyor?** Negatif bakiye, sonraki her hesabı (maliyet, MRP
ihtiyacı, ABC analizi, envanter değeri) sessizce bozar ve genelde bir *veri girişi
eksikliğini* gizler — çözüm negatife izin vermek değil, eksik girişi yapmaktır. Ayarlanabilir
hale getirmek "kapalı" varsayımıyla yazılmış tüm çağrı yollarını şüpheli kılar. Müşteri
gerçekten isterse ayrı bir ADR ile ele alınmalıdır.

---

## 6. Ölçü birimi: **tek temel birim**, S25'te dönüşüm yok

`Malzeme.birim` malzemenin **temel birimidir** ve tüm hareketler bu birimdedir.

- Teslim alma ve transfer gövdeleri birim taşırsa malzemenin temel birimiyle **birebir
  eşleşmelidir**; farklıysa **422** (`BIRIM_UYUSMAZLIGI`). Sessiz kabul yapılmaz.
- **Dönüşüm (ton↔kg, koli↔adet) S25 kapsamında DEĞİLDİR.** Yarım yapılmış bir dönüşüm
  katmanı (ör. yalnız teslim almada) bakiyeyi sessizce bozar; ya her yol dönüştürür ya da
  hiçbiri.
- Dönüşüm gerektiğinde tasarım hazır: `MalzemeBirimDonusum(malzeme_id, birim, carpan)` +
  girişte temel birime normalize etme. Ertelenmiş iş olarak kaydedildi; satınalma birimi
  (koli) ile stok birimi (adet) ayrışması gerçek bir ihtiyaç olduğunda ele alınacak.

---

## Sonuçlar

- Yeni tablolar: `depolar`, `lokasyonlar`, `stok_bakiyeleri`, `sayim_oturumlari`,
  `sayim_satirlari`, `satinalma_siparisleri`, `satinalma_siparisi_kalemleri`,
  `teslim_almalar`, `teslim_alma_kalemleri`.
- Yeni izin: `stok:duzeltme` (sayım farkı onayı — görev ayrımı; sayanla onaylayan farklı).
  **Bu izin, S23'te eklenen uzlaştırma sayesinde mevcut tenant'lara otomatik iner.**
- `Malzeme.mevcut_stok` **korunur**: lokasyon bakiyelerinin toplamı olarak güncellenir
  (geriye uyumluluk — mevcut ekranlar, kritik stok olayı ve MRP bu alanı okur).
- Migration fan-out up/down testli; mevcut stok verisi **varsayılan depo/lokasyona**
  backfill edilir (veri kaybı yok, boş DB'de geçen migration kabul edilmez).
