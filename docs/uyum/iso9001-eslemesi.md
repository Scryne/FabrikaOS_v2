# ISO 9001:2015 — Madde Eşlemesi

ISO 9001 maddelerinin **üründeki karşılığı**: bir kalite yönetim sistemi kuran fabrikanın hangi
kaydı FabrikaOS'ta tutabileceği. Belgelendirme iddiası değildir; kalite politikası, hedefler,
yönetimin gözden geçirmesi ve iç tetkik programı kuruluşun kendi sürecidir. Bilgi güvenliği
karşılığı: [iso27001-kontrol-eslemesi.md](iso27001-kontrol-eslemesi.md).

**Durum işaretleri:** ✅ üründe kayıt ve iş akışı var · 🟡 kısmen (kayıt var, akış elle) · ⬜ ürün kapsamı dışında

Son gözden geçirme: 2026-11-01 (S28).

| Madde | Durum | Üründeki karşılığı | Ekran |
|---|---|---|---|
| 7.1.3 Altyapı | ✅ | Makine kaydı, periyodik/kestirimci bakım planları, MTBF/MTTR, duruş kayıtları ve nedenleri | Üretim › Bakım, Vardiya & Duruş |
| 7.1.5 İzleme ve ölçme kaynakları | ✅ | Ölçüm cihazı envanteri, kalibrasyon kayıtları (sertifika, sonuç, sonraki tarih), süresi yaklaşan/geçen kalibrasyon taraması ve bildirimi; kalibrasyonu geçmiş ya da pasif cihazla SPC ölçümü reddedilir (`KALIBRASYON_GECERSIZ`) | Kalite › Ölçüm cihazları |
| 7.2 Yetkinlik | ✅ | Eğitim kayıtları ve katılım, departman başına zorunlu eğitim gereksinimi, eğitim matrisi (eksik/süresi dolan) | İSG & İK › Eğitim & KKD |
| 7.5 Dokümante edilmiş bilgi | 🟡 | Belge kaydı (kategori, sahip), değiştirilemez sürüm geçmişi, sürüm indirme; **onay/yayın akışı yok** (sürüm yükleme yetkisi `dys:yaz` ile sınırlı) | Doküman & Duyuru › Belgeler |
| 8.2 Ürün ve hizmet şartları | ✅ | Müşteri firma kaydı, sözleşmeler (süre, yenileme uyarısı), müşteri talepleri SLA ile | Ticari › Firmalar, Sözleşmeler, Talepler |
| 8.4 Dış kaynaklı süreç ve ürünlerin kontrolü | ✅ | Tedarikçi skoru (teslim zamanı, kabul oranı, uygunsuzluk), satınalma talebi → onay → sipariş → kısmi teslim → iade, mal kabul; uygunsuzluk tedarikçiye bağlanır | Stok & Satınalma, Ticari › Firmalar |
| 8.5.1 Üretim ve hizmet sunumunun kontrolü | ✅ | İş emri durum makinesi, ürün reçetesi (BOM), kontrol planı (karakteristik, spesifikasyon, örnekleme) | Üretim › İş emirleri, Ürünler & Reçete; Kalite › Kontrol planları |
| 8.5.2 Tanımlama ve izlenebilirlik | ✅ | Lot bakiyesi ve hareketleri, lot → iş emri → ürün izlenebilirliği (ileri/geri), malzeme etiketi | Üretim › İzlenebilirlik |
| 8.5.4 Koruma | 🟡 | Depo/lokasyon, transfer, sayım (delta), kritik stok uyarısı; raf ömrü takibi yok | Stok › Depolar, Sayımlar |
| 8.6 Ürün ve hizmetlerin serbest bırakılması | ✅ | Kalite kontrol kaydı (kabul/ret), SPC kontrol kartı ve yetenek (Cp/Cpk) | Kalite › Kalite kontrol, Kontrol planları |
| 8.7 Uygun olmayan çıktıların kontrolü | ✅ | Uygunsuzluk kaydı (kaynak: kalite kontrol, iş kazası, tedarikçi), sorumlu, termin | Kalite › Uygunsuzluklar |
| 9.1.1 İzleme, ölçme, analiz | ✅ | OEE (kullanılabilirlik × performans × kalite), SPC (Western Electric kuralları), enerji tüketimi trendi, analitik pano ve PDF/XLSX raporlar | Üretim, Kalite, Zekâ › Analitik, Raporlar |
| 9.1.2 Müşteri memnuniyeti | 🟡 | Müşteri talebi/şikâyet kaydı ve SLA; memnuniyet anketi yok | Ticari › Talepler |
| 9.2 İç tetkik | 🟡 | Değiştirilemez denetim kaydı (kim, ne, ne zaman) tetkike kanıt sağlar; tetkik programı/bulgu kaydı ürün kapsamı dışında | Yönetim › Denetim Kayıtları |
| 9.3 Yönetimin gözden geçirmesi | 🟡 | Girdiler hazır (OEE, uygunsuzluk, tedarikçi, müşteri talebi raporları); toplantı kaydı yok | Zekâ › Raporlar |
| 10.2 Uygunsuzluk ve düzeltici faaliyet | ✅ | Tam CAPA durum makinesi: açık → kök neden → aksiyon planı → uygulama → doğrulama → kapandı; doğrulama başarısızsa uygulamaya döner; iş kazasından tek tıkla CAPA | Kalite › Uygunsuzluklar |
| 10.3 Sürekli iyileştirme | ⬜ | Kuruluş süreci; ürün ölçüm verisini sağlar | — |

## Boşluklar

| Boşluk | Madde | Not |
|---|---|---|
| Belge onay/yayın akışı (taslak → onay → yayında, okundu onayı) | 7.5.2, 7.5.3 | En büyük boşluk; DYS sürüm geçmişi var, onay katmanı yok |
| Raf ömrü / son kullanma takibi | 8.5.4 | Lot modelinde tarih alanı yok |
| Müşteri memnuniyeti ölçümü | 9.1.2 | Talep kaydı var; anket/puan yok |
| İç tetkik ve yönetim gözden geçirmesi kayıtları | 9.2, 9.3 | Kuruluşların çoğu ayrı araçta tutar; ürün kapsamı kararı açık |
