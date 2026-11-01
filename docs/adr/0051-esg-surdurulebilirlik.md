# ADR-0051 — ESG & Sürdürülebilirlik (S32)

- **Durum:** Kabul edildi (S32, Faz 7)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0016 (S14 async rapor), S10 enerji hypertable. Yol haritası bu sprinti "ADR-0031"
  diye anıyordu; numara 0040'tan beri kaydığı için 0051.

Faz 7'nin dördüncü ve son satılabilir modülü: `esg` (deneme ve kurumsal planda). Kapsam: enerji
tüketiminden **Kapsam 1** (tesiste yakılan yakıt) ve **Kapsam 2** (satın alınan elektrik) emisyonu,
birim ürün başına karbon ve enerji yoğunluğu, dönemsel (gün/ay) toplulaştırma, async rapor.
Kapsam 3 (tedarik zinciri), su ve atık göstergeleri, sertifikalı envanter (ISO 14064 doğrulaması)
kapsam dışıdır.

## 1. Emisyon saklanmaz, hesaplanır

`emisyon = tüketim × faktör`. Tüketim ham `enerji_tuketim` tablosundan okunur; saatlik toplam
görünümünde (CAGG) birim olmadığı için kullanılamaz. Emisyon tabloya yazılmaz: faktör düzeltilince
geçmiş dönemler de yeni faktörle hesaplanır, bayat emisyon kalmaz. Saklanan tek şey tenant'ın
faktörleridir (`emisyon_faktorleri`: tür + normal birim + geçerlilik başlangıcı tekil, kapsam, kaynak
zorunlu).

**Dönem sınırı İstanbul saatidir** (`date_trunc` + `timezone('Europe/Istanbul', zaman)`). UTC'ye göre
kovalasaydık 00:00–03:00 arasındaki tüketim önceki güne düşerdi (S27'deki takvim günü hatasının
aynısı). Aylık kırılımda faktör ayın ilk günü geçerli olandır.

## 2. Faktörler: kaynaklı varsayılan + tenant

Faktör seçimi: aynı tür ve birim, `gecerlilik <= dönem başı` olanların en yenisi. Tenant'ın o tür ve
birim için hiç satırı yoksa kod içindeki **kaynaklı varsayılan** kullanılır (2026-11-01'de birincil
kaynaktan alındı):

| Tür | Değer | Kapsam | Kaynak |
|---|---|---|---|
| Elektrik | 0,469 kg CO2e/kWh | 2 | ETKB 2023 tüketim noktası faktörü, dağıtım hattına bağlı tüketim (iletim hattına bağlı tesis 0,436) |
| Doğalgaz | 1,928 kg CO2e/Sm³ | 1 | IPCC 2006 CO2 56.100 kg/TJ × alt ısıl değer 8.200 kcal/Sm³ (ETKB); CH4/N2O payı (+0,002) birincil kaynaktan doğrulanamadı |

Kararlar ve bilinen belirsizlikler:
- Elektrikte CDM tarzı **kombine marj** (0,62) kurumsal envanter için kullanılmaz; GHG Protocol konum
  bazlı Kapsam 2 ortalama şebeke yoğunluğu ister. ETKB tüketim noktası faktörü dağıtım kaybını
  içerir: Kapsam 3'te iletim-dağıtım kaybı ayrıca sayılırsa çift sayım olur (kaynak satırında yazılı).
- ETKB faktörü yaklaşık iki yıl gecikmeli yayımlanır (2023 verisi 31.12.2025'te). Varsayılan yıllık
  güncellenmeli; tenant kendi yılı için faktör girebilir.
- Alt ısıl değer için tek yetkili Türkiye değeri bulunamadı (8.200 / 8.250 / ~8.240, fark ≈ %0,6).
- Basınçlı hava, su ve buhar için faktör **verilmez**: enerjileri elektrik ya da yakıt tüketiminin
  içindedir. Bu tüketimler "faktörsüz" listesinde miktarıyla görünür, **0 sayılmaz** (eksik veri
  sessizce "düşük emisyon" görünmesin). Dışarıdan satın alınan buhar varsa tenant faktör girer.

## 3. Yoğunluk

`kg CO2e / sağlam adet` ve `kWh / sağlam adet`, aynı dönemin `uretim_verileri.saglam_adet`
toplamıyla. Üretim yoksa yoğunluk **tanımsız** (null), 0 değil.

## 4. API, yetki, rapor

- `GET /esg/ozet?baslangic&bitis&donem=gun|ay` (`esg:oku`): dönemler, tür kırılımı, faktörsüz
  tüketim, toplamlar. Aralık sınırı günlükte 92, aylıkta 1096 gün (422).
- `GET/POST/DELETE /esg/faktorler` (`esg:yaz` yazma): birim normalleştirilir (kWh, m³), faktör temel
  birim başına girilir (MWh ile 422), aynı tür/birim/tarih 409.
- Rapor: rapor modülüne `esg` türü eklendi (`POST /raporlar`, 202, süreç-içi async, nesne deposuna
  yazılır). Rapor ucu ESG için ayrıca modül açıklığını ve `esg:oku`'yu denetler.
- Rol `esg`: `esg:oku/yaz`, `enerji:oku`, `uretim:oku`, `rapor:oku/yaz`.

## 5. Doğrulama

- 10 birim + 4 entegrasyon testi. Entegrasyon bilinen seriyle: faktör değişimi pencere ortasında,
  gece yarısı sınırı (00:30 İstanbul = 21:30 UTC önceki gün), faktörsüz basınçlı hava, aylık
  kırılımda dönem başı faktörü, yoğunluk, RBAC, izolasyon, async rapor (XLSX içeriği okunarak), göç.
- Mutasyon `hesap.py` %100. Koruma sökme: İstanbul saatiyle kovalama, faktörsüzü 0 saymama ve tarihe
  göre faktör seçimi tek tek kaldırıldığında testler düşüyor (3/3).
- Canlı (dev demo): 30 günde 2,657 t CO2e (doğalgaz 658,3 m³ × 1,928 = 1.269 kg; elektrik 2.958,4 kWh
  × 0,469 = 1.387 kg), basınçlı hava 2.101 m³ faktörsüz. PDF Türkçe karakterli; yoğunluk sütunları 4
  basamak (ilk denemede genel 2 basamak yuvarlaması 0,0261'i 0,03 yapıyordu).
- Dev ortamında MinIO yok: rapor yükleme adımında bütün türler gibi "başarısız" olur (içerik
  üretimi ayrı doğrulandı).
