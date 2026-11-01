# ADR-0049 — Üretim Planlama & Çizelgeleme (S30)

- **Durum:** Kabul edildi (S30, Faz 7)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0004 (iş emri durum makinesi), ADR-0023 (S24 vardiya), ADR-0047 (görev ayrımı,
  hata sınıfları), ADR-0048 (Faz 7 modül deseni). Yol haritası bu sprinti "ADR-0029" diye anıyordu;
  numara Faz 5'ten beri 0040'tan devam ettiği için 0049.

Faz 7'nin ikinci satılabilir modülü: `planlama` (deneme ve kurumsal planda). Soru tek: **açık iş
emirleri bu makinelerde, bu vardiyalarla, teslim tarihlerine yetişir mi; yetişmiyorsa neden?**
Kapsam sonlu kapasiteli, makine başına çizelgedir. Çok kaynaklı APS (operatör + takım + malzeme
aynı anda), rota/operasyon adımları ve optimizasyon çözücüsü kapsam dışıdır.

## 1. Çizelge saklanmaz, her istekte hesaplanır

Tek doğruluk kaynağı iş emri (makine, öncelik, teslim, miktar, durum) ve iş emri başına küçük bir
plan girdisidir (`is_emri_planlari`: elle süre, elle sıra). Çizelge her `GET /planlama/cizelge`
isteğinde açık iş emirleri ve aktif vardiyalardan yeniden kurulur.

Reddedilen: hesaplanmış çizelgeyi tabloya yazmak. Bir iş emri kapandığında, bir vardiya
değiştiğinde ya da yeni iş geldiğinde saklı çizelge bayatlar; tazeleme tetikleri (outbox, zamanlı
iş) bu ölçekte (tenant başına onlarca açık iş) maliyetten başka bir şey getirmez. Hesap saf ve
milisaniyelerle ölçülür.

## 2. Model: makine başına tek makine problemi

Her iş emri zaten bir makineye bağlı; makineler birbirinden bağımsız çizelgelenir. Çalışılabilir
zaman yalnız vardiya pencereleridir (gece vardiyası ertesi güne taşar, bitişik pencereler
birleşir). İş pencere sonunda kesilir ve sonraki pencerede sürer (Gantt'ta parçalı çubuk).
Hiç vardiya tanımlı değilse 08:00–16:00 varsayılır ve yanıt bunu `varsayilan_vardiya` ile söyler.

**Sıralama kuralı (tam sıralı, tekrarlanabilir):** devam eden işler önce (yarıda bırakılmaz) →
elle sıra (küçük önce) → en erken teslim (EDD) → öncelik (kritik → düşük) → id.

**Süre:** elle girilen süre → tahmin (miktar × makinenin son ideal çevrim süresi ÷ OEE hedefi;
hedef yoksa 0,85) → varsayılan 60 dk. Hangisinin kullanıldığı her işte `sure_kaynagi` ile döner;
ekran varsayılanı sarı etiketle gösterir, çünkü o sayıya güvenilmez.

## 3. Kapasite aşımının deterministik tanımı

Tek makinede EDD sırası en büyük gecikmeyi en aza indirir (Jackson, 1955). Bu yüzden **EDD
çizelgesinde teslimini kaçıran bir iş varsa, o makinede teslim tarihlerini hiçbir sıra
karşılayamaz**: bu kapasite aşımıdır. Planlamacı elle sıra verdiğinde bu garanti bozulur; servis
çizelgeyi iki kez kurar (elle sıralı ve elle sırasız saf EDD) ve gecikmeyi ikiye ayırır:

| Durum | Anlamı | Ne yapılır |
|---|---|---|
| `kapasite_asimi` | Saf EDD'de de geç | Sıra değiştirmek yetmez: fazla mesai, başka makine, yeni teslim |
| `sira_kaynakli_gecikme` | Saf EDD'de zamanında, elle sırada geç | Elle sırayı gözden geçir |
| `sigmadi` | Ufuk içinde bitirilemedi | Ufku büyüt ya da kapasite ekle |

Devam eden işler her iki çizelgede de başta kalır; aşım tanımı "devam edeni yarıda bırakmadan"
koşulludur.

## 4. API ve yetki

- `GET /api/v1/planlama/cizelge?baslangic&gun(1–31)&makine_id` — `planlama:oku`. Makine başına
  işler (parçalarıyla), günlük yük (plan/kapasite dakika, gün sınırında bölünür), özet.
- `PUT /api/v1/is-emirleri/{id}/plan` — `planlama:yaz`. `{sure_dk, elle_sira}`; ikisi de boşsa
  girdi silinir (otomatiğe döner). Kapanmış/iptal iş emri 409, başka tenant'ın iş emri 404,
  satır `FOR UPDATE` altında yazılır, denetim kaydı düşer.
- Yeni rol `planlamaci`: `planlama:oku/yaz` + `isemri:oku` + `uretim:oku`. Planlamacı iş emrinin
  kendisini (durum, makine, teslim) değiştiremez; o iş emri sahibinin yetkisidir.
- Göç `a1c3e5f7b9d1` (tenant şeması, fan-out up/down).

## 5. Ön yüz

`/uretim-plani` (Üretim bölümü). Gantt HTML/CSS ile çizilir, ECharts ile değil: çubuklar
klavyeyle odaklanabilir düğmelerdir (Enter → plan çekmecesi), ekran okuyucu her çubuğun işini,
saatini ve durumunu okur. Aynı veri erişilebilir bir "İş sırası" tablosunda ve gün × makine yük
ızgarasında da durur. Renk anlamı tek kaynaktan (`isDurumu`): zamanında hat rengi, sıra gecikmesi
amber, kapasite aşımı kırmızı, ufka sığmayan taralı kırmızı. Dar ekranda Gantt kendi içinde yatay
kayar, sayfa taşmaz. Çizelge dakikada bir tazelenir ("şimdi" çizgisi ve devam eden işler kayar).

## 6. Bilinen sınırlar

- Vardiyalar haftanın her günü geçerlidir (vardiya modelinde gün yok); hafta sonu ve tatil
  kapasitesi ayrı bir takvim gerektirir.
- Ufkun ilk gününden önce başlayan gece vardiyasının (ör. 22:00–06:00) ilk sabah parçası ufka
  girmez; çizelge o pencereyi ilk günün 22:00'sinden başlatır.
- Hazırlık (setup) süresi ve sıra bağımlı değişim süresi yoktur; tahmin yalnız çevrim süresinden.
- Tek makine kuralı: aynı işi iki makineye bölmek ya da paralel hat yoktur.
