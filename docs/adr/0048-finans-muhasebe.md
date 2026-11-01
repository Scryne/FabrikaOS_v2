# ADR-0048 — Finans & Muhasebe MVP (S29)

- **Durum:** Kabul edildi (S29, Faz 7)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0011 (stok bakiye + kilit deseni), ADR-0014 (CRM firma), ADR-0016 (rapor),
  ADR-0020 (webhook + API anahtarı), ADR-0045 (Onaylarım), ADR-0047 (görev ayrımı, hata sınıfları).
  Yol haritası bu sprinti "ADR-0028" diye anıyordu; numara Faz 5'te 0040'tan devam ettiği için 0048.

Faz 7'nin ilk yeni satılabilir modülü: `finans` (yalnız deneme ve kurumsal planda). Kapsam bir
ön muhasebe çekirdeğidir: kime ne kadar borçlu/alacaklıyız, hangi fatura ne zaman kesildi ve
kapandı, üretilen bir işin malzemesi kaça mal oldu. Genel muhasebe (yevmiye, hesap planı,
mizan, beyanname) kapsam dışıdır; bunlar müşterinin muhasebe yazılımında kalır ve FabrikaOS
oraya fatura ve cari verisini taşır.

## 1. Cari hesap: tutulan bakiye + değiştirilemez hareket

`cari_hesaplar` firma başına tek satır, `bakiye` **tutulan** değerdir ve yalnız `FOR UPDATE` satır
kilidi altında değişir (stok bakiyesiyle aynı desen, ADR-0011). Her değişiklik `cari_hareketler`e
işaretli tutar ve `bakiye_sonrasi` ile yazılır. İşaret bizim gözümüzden: pozitif = firma bize
borçlu.

| Olay | Bakiye etkisi |
|---|---|
| Satış faturası kesildi | + genel toplam |
| Tahsilat | − tutar |
| Alış faturası kesildi | − genel toplam |
| Firmaya ödeme | + tutar |
| Kesilmiş faturanın iptali | kesilmenin tersi |

**Çift sayım iki katmanla engellenir.** `cari_hareketler.kaynak` tekildir (`fatura:12`,
`fatura-iptal:12`, `odeme:7`): aynı olay bakiyeye ikinci kez giremez. Ödeme ucunda
`Idempotency-Key` başlığı `odemeler.idempotency_anahtari`'na yazılır: istemcinin yeniden denemesi
ilk kaydı döndürür (200), ikinci ödeme açmaz.

Reddedilen: bakiyeyi her okumada hareketlerden toplamak. Doğru ama liste ve yaşlandırma her
istekte tüm geçmişi tarar; tutulan bakiye + kilit deseni kod tabanında zaten kanıtlı.

## 2. Fatura yaşam döngüsü ve görev ayrımı

```
taslak → onay_bekliyor → kesildi → kapandi
  ▲            │            │
  └── (iade) ──┘            └→ iptal (yalnız ödemesizse, nedenle)
taslak / onay_bekliyor → iptal
```

- **Kesme** (`kesildi`) cariye işler ve `fatura.kesildi` olayını aynı işlemde outbox'a yazar;
  `finans:onay` ister ve faturayı hazırlayan kişi kesemez (403; ADR-0047 §5'teki kuralın aynısı).
- **Kapanma** elle istenmez: ödenen tutar genel toplama ulaşınca servis geçirir.
- **İptal** kesilmiş faturada neden ister ve ödemesi varsa reddedilir (409): önce ödeme düzeltilir.
- Kesilmiş fatura düzenlenemez; düzeltme iade (taslağa dönüş, neden zorunlu) ile yapılır.
- Fatura ödeme tutarı da fatura satırı kilitlenerek güncellenir; veritabanı CHECK'i
  (`0 ≤ odenen_tutar ≤ genel_toplam`) son savunmadır. Eşzamanlı iki tahsilat açık tutarı aşamaz
  (testli; kilit kaldırılınca test düşüyor).

## 3. Tutar hesabı

Decimal, satır başına 2 basamağa yarım-yukarı yuvarlama: satır = miktar × birim fiyat, KDV =
satır × oran; toplamlar yuvarlanmış satırların toplamı. Böylece faturadaki her satır toplamla
kuruşu kuruşuna tutar. KDV oranları yasal küme: %0, %1, %10, %20. Ön yüz aynı kuralla canlı
önizleme yapar (birim testi sunucu örneğiyle aynı sonucu verir); kayıtlı tutar sunucunundur.

## 4. Yetkiler

| İzin | Kapsam |
|---|---|
| `finans:oku` | Fatura, cari, ödeme, özet, yaşlandırma, maliyet (izleyiciye de verilir) |
| `finans:yaz` | Fatura hazırlama/düzenleme/gönderme, taslak iptali, **tahsilat** |
| `finans:onay` | Kesme, iade, kesilmiş faturanın iptali, **firmaya ödeme**, e-Fatura durumu |

Roller: `finans` (oku + yaz; kesemez), `finans-onaylayan` (oku + yaz + onay). Para çıkışı (ödeme)
onay ister, para girişi (tahsilat) istemez.

## 5. Raporlar

- **Yaşlandırma:** açık (kesilmiş) faturaların vadeden bu yana geçen güne göre dağılımı
  (vadesi gelmemiş, 0–30, 31–60, 61–90, 90+), alacak ve borç ayrı, firma kırılımıyla.
  Faturaya bağlanmamış (avans) tahsilat faturaları kapatmaz; cari bakiyede görünür.
- **Ekstre:** dönem başı açılış bakiyesi + tarih sıralı yürüyen bakiye (geriye tarihli
  hareketlerde kayıt anındaki `bakiye_sonrasi` ekstre sırasıyla uyuşmayabilir, bu yüzden hesaplanır).
- **Üretim malzeme maliyeti:** kapanan iş emirlerinin gerçek BOM tüketimi (`bom:<id>` stok
  çıkışları) × malzemenin son satınalma siparişi fiyatı (yoksa son talepteki tahmini fiyat).
  Fiyatı olmayan kalem **0 sayılmaz**: işaretlenir ve birim maliyet hesaplanmaz. İşçilik, genel
  üretim gideri ve stok değerleme yöntemi (FIFO/ağırlıklı ortalama) bilerek yok.

## 6. e-Fatura: iskelet, entegratör üzerinden

FabrikaOS GİB'e doğrudan bağlanmaz (özel entegratör yetkisi ve UBL-TR imzası ayrı bir ürün).
Fatura ETTN (UUID), senaryo (`TEMELFATURA`/`TICARIFATURA`/`EARSIV`) ve iletim durumunu tutar.
Entegratör `GET /entegrasyon/faturalar` ucunu `finans:oku` kapsamlı API anahtarıyla okur (varsayılan
süzgeç: gönderilmemiş), sonucu `PUT /faturalar/{id}/gib-durumu` (`finans:onay`, denetim izli) ile
işlenir. Fatura PDF'i "bilgi nüshası"dır ve bunu üstünde yazar; taslak PDF'te filigran vardır.

## 7. Entegrasyon noktaları

Olaylar `fatura.kesildi`, `odeme.alindi`, `odeme.yapildi` webhook kataloğunda; ilk ikisi
bildirim merkezine (`finans:oku`). Onay bekleyen fatura Onaylarım'a düşer (hazırlayana değil,
sayaçta). ⌘K araması faturaları bulur. Demo tohumu 12 fatura, 5 tahsilat/ödeme üretir; faturayı
finans kullanıcısı hazırlar, mali işler yöneticisi keser.

## Kabul

| Ölçüt | Kanıt |
|---|---|
| Cari bakiye eşzamanlılık-güvenli, çift hareket çift saymaz | `test_esanli_tahsilat_fazla_odemeye_izin_vermez`, idempotency testi; kilit ve idempotency kaldırılınca testler düşüyor |
| Fatura durum geçişi + geçersiz 409 | `test_fatura_toplamlari_kesim_ve_gorev_ayrimi`, iptal testleri |
| RBAC 403 + tenant izolasyonu | `test_rbac_izolasyon_ve_liste`, ödeme onay testi |
| Göç fan-out up/down | `test_s29_goc_up_down` |
| Saf çekirdek | 17 birim testi, mutasyon skoru %100 (CI hedeflerine eklendi) |
| Ekranlar | Finans özeti, Faturalar, Cari hesaplar, Tahsilat & ödeme; 1440/390 taşmasız, konsol temiz; kes → tahsilat → kapandı akışı canlı denendi |
