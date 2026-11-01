# FabrikaOS kullanıcı el kitabı

Fabrikada FabrikaOS'u her gün kullanan kişiler için: vardiya amiri, kalite sorumlusu, depo
görevlisi, İSG uzmanı, İK, satınalma, satış. Kurulum, kullanıcı ve rol işleri
[yönetici kılavuzunda](yonetici-kilavuzu.md).

Menüde yalnız rolünüzün izin verdiği ve fabrikanızın aboneliğinde açık olan modüller görünür.
Aradığınız bir ekran yoksa yöneticinize hangi rolün gerektiğini sorun; her bölümün sonunda
gereken izin yazıyor.

## 1. Başlarken

**Giriş.** E-posta ve parola; fabrikanıza ait adresten (ör. `fabrika-a.…`) girmiyorsanız ekran ayrıca **Firma kodu** sorar (yöneticinizin verdiği kısa ad). İki aşamalı doğrulama
açıksa ardından kimlik doğrulama uygulamanızdaki 6 haneli kodu girersiniz. Telefonunuzu
kaybettiyseniz 2FA kurulumunda size bir kez gösterilen kurtarma kodlarından birini kullanın;
her kod bir kez geçer.

**2FA'yı kendiniz açmak:** sağ üst menü › Güvenlik › İki aşamalı doğrulama › QR kodu
uygulamanızla (Google Authenticator, Microsoft Authenticator, 1Password …) okutun, gösterilen
kodu girin. Kurtarma kodlarını o ekranda kaydedin; tekrar gösterilmez.

**Oturumlarınız:** Güvenlik ekranında açık oturumlarınızı (cihaz, IP, son kullanım) görür,
tanımadığınız oturumu tek tek kapatırsınız.

**Hızlı erişim.** `Ctrl+K` (Mac'te `⌘K`) komut paletini açar: ekran adı yazarak gidin ya da
kayıt arayın (iş emri kodu, malzeme, firma, personel, belge …). Sonuç tıklanınca kaydın
kendisi açılır; adres çubuğundaki bağlantıyı kopyalayıp bir arkadaşınıza gönderebilirsiniz.

**Listeler.** Her listede arama, filtre, sıralama ve sayfa boyutu var. Sağ üstteki
**Dışa aktar** düğmesi o anki filtreyle CSV ya da Excel verir (en çok 5.000 satır). Yazdırma
(`Ctrl+P`) menüleri gizleyip yalnız içeriği basar.

**Onaylarım.** Genel › Onaylarım, onayınızı bekleyen her şeyi tek listede toplar: satınalma
talepleri, izin talepleri, fazla mesailer ve sayım farkları. Kendi açtığınız kayıtlar listede
yer almaz (görev ayrımı: kaydı açan kişi onaylayamaz); kaç tanesinin başka bir yetkiliyi
beklediği listenin üstünde yazar. Rolünüzde onay yetkisi yoksa liste boştur.

**Bildirimler.** Zil simgesi: size atanan işler, yaklaşan sözleşme bitişleri, SLA'sı yaklaşan
talepler, kalibrasyonu yaklaşan cihazlar, hazır olan raporlarınız. Yönetim › Bildirim
tercihleri'nden hangi türleri alacağınızı seçersiniz; kurulumda e-posta sunucusu tanımlıysa
seçtikleriniz e-postayla da gelir.

## 2. Pano

Giriş ekranı. Fabrikanın anlık OEE'si, aktif iş emirleri, açık uygunsuzluklar, kritik stok ve
son olaylar. Sayılar sayfa yenilenmeden, olay oldukça güncellenir; her bölümün başlığındaki
**Panele git** ilgili ekranı açar.

## 3. Üretim

**Makineler** (`uretim:oku`): makine kartları, anlık durum, OEE (kullanılabilirlik ×
performans × kalite) ve hedefe göre sapma. Makine detayında geçmiş OEE eğrisi ve duruşlar.

**Üretim verileri:** saha cihazlarından ya da elle girilen vardiya kayıtları (planlanan süre,
duruş, toplam ve sağlam adet). Elle giriş için sağ üstte **Yeni kayıt**.

**İş emirleri** (`isemri:oku`, değiştirmek için `isemri:yaz`): akış
`açık → atandı → devam ediyor → kapandı`; her aşamada **iptal** edilebilir, kapanan ya da iptal
edilen iş emri yeniden açılmaz. Ürünü reçeteli bir iş emri **kapanırken** reçetedeki malzemeler
üretilen adet kadar stoktan düşülür; stok yetmezse kapanış reddedilir ve eksik malzeme
yazılır. Lot numarası verilen iş emri izlenebilirlik zincirine girer.

**Üretim planı** (`planlama:oku`, düzeltmek için `planlama:yaz`): açık iş emirleri makine başına
vardiya saatlerine, teslim tarihi en yakın olan önce gelecek şekilde yerleştirilir (devam eden iş
her zaman başta). Çubuk rengi durumu söyler: mavi zamanında, amber **sıra kaynaklı gecikme**
(elle verdiğiniz sıra yüzünden geç; sırayı kaldırırsanız yetişir), kırmızı **kapasite aşımı**
(hiçbir sırayla yetişmez: fazla mesai, başka makine ya da yeni teslim tarihi gerekir). Bir çubuğa
tıklayıp süreyi (dakika) ya da sırayı elle girin; **Otomatiğe döndür** ikisini de siler. Süre
girilmemişse miktar × makinenin son çevrim süresinden tahmin edilir; veri yoksa 60 dk varsayılır
ve sarı **varsayılan** etiketi çıkar. **Günlük yük** her makinenin günlük doluluğunu gösterir.

**Ürünler & Reçete:** ürün kartı ve reçetesi (BOM: ürün başına bir reçete, satırları malzeme ve
birim başına miktar; alt reçete yoktur).

**Vardiya & Duruş:** vardiya tanımları ve duruş kayıtları (neden kodlarıyla). Duruş nedenleri
listesi fabrikaya özeldir; yönetici ekler.

**İzlenebilirlik:** bir lot numarası girin; o lottan hangi iş emrinin, hangi malzeme lotlarıyla
üretildiği (geri) ve nereye gittiği (ileri) zincir olarak görünür.

**Dijital ikiz:** fabrika yerleşiminde makinelerin canlı durumu (çalışıyor, durdu, bakımda, arıza).
**Saha cihazları** (`saha:oku`): veri gönderen ağ geçitleri, çevrimiçi durumu ve son görülme zamanı.

**Bakım** (`bakim:oku`): periyodik bakım planları, gecikenler, MTBF/MTTR. **Vade taraması**
zamanı gelen her plan için bir bakım iş emri açar ve planın sonraki tarihini periyot kadar ileri
alır; bakımın kendisi o iş emri üzerinden yürür ve kapanır.

## 4. Stok & Satınalma

**Malzemeler** (`stok:oku`): malzeme kartı, birim, kritik seviye, depo/lot bazında bakiye.
Malzeme detayında **Etiket** düğmesi QR kod ve Code128 barkodlu etiket PDF'i üretir.
**Kritik stok:** kritik seviyenin altındaki malzemeler; satırdaki satınalma düğmesi
(`satinalma:yaz`) satınalma talepleri ekranını açar, talebi orada oluşturursunuz.

**Depolar ve Sayımlar:** depo/lokasyon tanımı, depolar arası transfer, sayım. Sayımda yalnız
sayılan miktarı girersiniz; fark (delta) sistemce hesaplanır ve onaylanınca stok düzeltme
hareketi olarak işlenir (`stok:duzeltme`; sayımı açan kişi onaylayamaz).

**Satınalma talepleri** (`satinalma:oku`): akış `taslak → onay bekliyor → onaylandı / reddedildi`.
Onay `satinalma:onay` yetkisi ister ve talebi açan kişi, bu yetkiye sahip olsa bile kendi
talebini onaylayamaz (görev ayrımı).

**Satınalma siparişleri:** onaylı talepten sipariş; tedarikçiden kısmi teslim alınabilir, her
teslim stok hareketi üretir; iade de kayıt altına girer. Sipariş detayında **Sipariş formu (PDF)**
tedarikçiye gönderilecek resmi formu verir. Teslim süresi ve kabul oranı tedarikçi skoruna yansır.

## 5. Kalite & Enerji

**Kalite kontrol** (`kalite:oku`): kontrol kayıtları (makine, iş emri ya da malzemeye bağlı;
ölçülen değer, alt/üst limit, numune adedi, sonuç). Ret çıkan bir kontrol, uygunsuzluk kaydında
kaynak olarak seçilir.

**Kontrol planları:** ürün başına ölçülecek karakteristikler, spesifikasyon sınırları ve
örnekleme. Karakteristiğin **kontrol kartı** (X̄-R) alt gruplar ölçüldükçe çizilir; Western
Electric kural ihlalleri işaretlenir: 3σ sınırı dışında nokta; art arda 3 noktanın 2'si 2σ
ötesinde; 5 noktanın 4'ü 1σ ötesinde; 8 nokta merkez çizgisinin aynı tarafında. Yetenek
indeksleri (Cp, Cpk) kartın altında.

**Ölçüm cihazları:** cihaz envanteri ve kalibrasyon geçmişi. Kalibrasyonu geçmiş ya da pasif
cihazla ölçüm **kaydedilemez**; tarih yaklaşınca sorumlusuna bildirim gider.

**Uygunsuzluklar** (CAPA): akış `açık → kök neden → aksiyon planı → uygulama → doğrulama → kapandı`;
doğrulama başarısızsa uygulamaya döner. Kaynak bir kalite kontrolü, tedarikçi ya da iş kazası
olabilir. İş kazası ekranından **CAPA aç** tek tıkla bağlı vaka açar (kaza başına bir vaka).

**Enerji** (`enerji:oku`): sayaç tüketimleri ve dönem trendi.

**Sürdürülebilirlik (ESG)** (`esg:oku`; faktör eklemek için `esg:yaz`): seçilen aralıkta Kapsam 1
(tesiste yakılan doğalgaz) ve Kapsam 2 (şebeke elektriği) emisyonu, günlük ya da aylık. **Karbon
yoğunluğu** sağlam ürün başına kg CO₂e'dir. Emisyon faktörü olmayan tüketim (ör. basınçlı hava) 0
sayılmaz, sarı uyarıda miktarıyla görünür. Varsayılan faktörler resmî kaynaklıdır (ETKB, IPCC);
fabrikanıza özgü faktörü kaynağıyla girdiğinizde o tarihten itibaren o kullanılır ve geçmiş dönemler
de yeniden hesaplanır. **ESG raporu** PDF olarak Raporlar ekranında hazırlanır.

## 6. İSG & İK

**İş kazaları** (`isg:oku`): kaza bildirimi, yaralanma bilgisi, kök neden; ilgili makine ve
personele bağlanır.
**Risk değerlendirme:** tehlike, olasılık × şiddet puanı, önlem ve sorumlu.
**Eğitim & KKD:** eğitim kayıtları ve katılımcılar; departman başına zorunlu eğitim ve KKD
(kişisel koruyucu donanım) gereksinimleri; **eğitim matrisi** kimin hangi eğitimi eksik ya da
süresi dolmuş olduğunu gösterir. KKD teslimi zimmet olarak kaydedilir.
**Tatbikatlar:** yangın, tahliye, ilk yardım tatbikatları ve katılım.

**Personel** (`ik:oku`; TC kimlik numarası listede maskeli görünür): personel kartı, departman,
yönetici, işe giriş tarihi. Detayda izin bakiyesi, zimmetler, işe giriş/çıkış kontrol listeleri.
**Org şeması:** yönetici ilişkilerinden çizilir. Bir kişi kendi astının astına bağlanamaz.

**İzin talepleri:** akış `taslak → onay bekliyor → onaylandı / reddedildi`; onay `ik:onay`
ister ve talebi giren kişi onaylayamaz (fazla mesai onayında da aynı kural). Yıllık izin hakkı
İş Kanunu md. 53'e göre kıdemden hesaplanır (1–5 yıl 14 gün, 5–15 yıl 20 gün, 15+ yıl 26 gün;
18 yaş altı ve 50 yaş üstü en az 20 gün). Bakiyeyi aşan talep onaylanamaz.

## 7. Ticari

**Firmalar** (`crm:oku`): müşteri ve tedarikçi kartları. Tedarikçilerde **skor** (teslim, kabul,
uygunsuzluk) ve bağlı uygunsuzluklar. **Ticari pano:** firma ve talep özeti.

**Sözleşmeler** (`sozlesme:oku`): akış `taslak → aktif → sona erdi / feshedildi`. Bitişi
yaklaşan sözleşme için sahibine bildirim gider.

**Talepler** (`talep:oku`): müşteri talepleri ve şikâyetleri; akış
`açık → inceleniyor → çözüldü → kapandı` (müşteri itiraz ederse çözüldüden incelemeye döner).
SLA süresi yaklaşan ya da geçen talep işaretlenir.

**Satış siparişleri** (`satis:oku`; hazırlamak için `satis:yaz`, onay için `satis:onay`): müşteri
siparişi taslak olarak açılır (ürün × miktar, teslim tarihi, üretim hattı). Detaydaki **Malzeme
ihtiyacı** tablosu her malzeme için gerekeni, kullanılabiliri (stok + gelmekte olan − açık iş
emirlerine ayrılmış) ve eksiği gösterir. **Onayla** her kalem için seçilen hatta bir üretim emri ve
eksik malzemeler için tek bir satınalma talebi açar; talep satınalma onayına düşer. Siparişi açan
kişi onaylayamaz. Aynı sipariş ikinci kez onaylanamaz; açılan işler **Açılan işler** listesinden
izlenir. Akış `taslak → onaylandı → sevk edildi → kapandı`; onaylı sipariş iptal edilirse açılan
üretim emirleri ve talep ayrıca kapatılmalıdır.

## 8. Doküman & Duyuru

**Belgeler** (`dys:oku`): prosedür, talimat, form. Her yükleme yeni bir **sürüm** açar; eski
sürümler silinmez, indirilebilir kalır. **Duyurular:** yayınlanan duyuru tüm kullanıcılara
bildirim olarak gider; hedef departman alanı duyurunun kimi ilgilendirdiğini belirtir (bugün
gönderimi daraltmaz).

## 9. Finans

**Faturalar** (`finans:oku`; hazırlamak için `finans:yaz`): satış ve alış faturaları. Akış
`taslak → onay bekliyor → kesildi → kapandı`. Faturayı hazırlayan kişi kalemleri (açıklama, miktar,
birim fiyat, KDV %0/%1/%10/%20) girer, toplam yazarken hesaplanır ve **Onaya gönder**ir. Onay
yetkilisi (`finans:onay`) **Faturayı kes**er ya da nedenini yazarak düzeltmeye iade eder; faturayı
hazırlayan kişi kendi faturasını kesemez. Kesilen fatura cari hesaba işlenir ve artık
düzenlenemez. Ödemesi tamamlanan fatura kendiliğinden **kapandı** olur. Kesilmiş fatura yalnız
hiç ödemesi yoksa ve nedenle iptal edilir. **PDF** bilgi nüshasıdır; resmî e-Fatura
entegratör üzerinden gider.

**Tahsilat & ödeme:** firmadan gelen tahsilatı finans kullanıcısı, firmaya yapılan ödemeyi onay
yetkilisi girer. Faturaya bağlanan tutar faturanın açık tutarını aşamaz. Aynı formu iki kez
göndermek (çift tık, kopan bağlantı) ikinci kayıt açmaz.

**Cari hesaplar:** firma başına bakiye (yeşil: alacağımız, turuncu: borcumuz), açık fatura ve
vadesi geçen alacak. Satıra tıklayınca son 12 ayın ekstresi (açılış bakiyesi, borç, alacak,
yürüyen bakiye) açılır.

**Finans özeti:** açık alacak ve borç, vadesi geçen alacak, bu ayın satışı ve tahsilatı; vade
yaşına göre dağılım ve en büyük açık alacaklar (satıra tıklayınca o firmanın faturaları);
kapanan iş emirlerinin malzeme maliyeti (reçeteden tüketilen malzeme × son satınalma fiyatı).
Fiyatı bilinmeyen malzeme maliyete 0 diye eklenmez, "fiyatsız" diye işaretlenir.

## 10. Zekâ

**AI Tahminleri** (`ai:oku`): kestirimci bakım (arıza riski yüksek makineler), anomali (olağan
dışı üretim/enerji değerleri), OEE ve stok tahmini. Tahminler karar desteğidir; tablolar
dayandıkları ölçümleri (veri günü, duruş ve fire oranı, günlük tüketim) ve altta model sürümüyle
üretim zamanını gösterir.
**Analitik** (`analitik:oku`): dönem karşılaştırmalı KPI'lar. **Raporlar** (`rapor:oku`):
PDF/XLSX raporlar arka planda hazırlanır; liste kendiliğinden güncellenir ve rapor hazır
olunca zile "Raporunuz hazır" bildirimi düşer.

## 11. Sık sorulanlar

- **"Bu işlem için yetkiniz yok" diyor.** Rolünüzde ilgili izin yok; yöneticiniz Yönetim ›
  Kullanıcılar'dan rol ekler.
- **"Seçilen ilişkili kayıtlardan biri bulunamadı".** Seçtiğiniz makine/personel/firma bu arada
  silinmiş ya da pasifleştirilmiş; listeyi yenileyip yeniden seçin.
- **"Bu değerle başka bir kayıt zaten var".** Kod ya da ad benzersiz olmalı (ör. iki vardiya aynı
  adı taşıyamaz).
- **"Hizmet geçici olarak kullanılamıyor" (503).** Bir altyapı parçası (ör. belge deposu) kısa
  süreli erişilemiyor; işleminiz kaydedilmedi, birkaç dakika sonra tekrar deneyin.
- **CSV yükleme reddedildi.** Dosyayı Excel'de *CSV UTF-8* olarak kaydedin; ilk satır sütun
  adlarını taşımalı.
