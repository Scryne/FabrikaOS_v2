# ADR-0047 — Kurumsal Güvence & Sürdürülebilirlik (S28)

- **Durum:** Kabul edildi (S28, Faz 6)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0022 (güvenlik ve uyum, ertelenmiş işler), ADR-0040 (gözlemlenebilirlik),
  ADR-0041 (yedek/DR), ADR-0043 (sertleştirme ve kapasite). Yol haritası bu sprinti "ADR-0027"
  diye anıyordu; numaralar Faz 5'te 0040'tan devam ettiği için 0047 oldu.

S28'in sorusu "testler yeşil" ile "ürün kurumsal müşteriye verilebilir" arasındaki boşluk:
testlerin hatayı gerçekten yakaladığı, ürünün kötü girdide ve altyapı kesintisinde düzgün
davrandığı, tedarik zincirinin görünür olduğu ve işletenin elinde runbook olduğu.

## 1. Mutasyon testi: kendi AST koşucumuz, eşik %90

`backend/scripts/mutasyon.py` dokuz saf çekirdek dosyada (OEE, dört durum makinesi, SPC, izin
hakedişi, eğitim matrisi, iş günü) aritmetik, karşılaştırma, mantık ve sabit mutasyonları tek
tek uygular, hedefin birim testlerini koşar. Skor %57,7 → (26 yeni sınır testiyle) **%93,4**;
kalan 16 mutantın çoğu eşdeğer (ör. `>= 0` ile `> 0` aynı sonucu veren sınır). CI `mutasyon`
işi eşiğin altında düşer.

Reddedilen: mutmut 3 (`fork` ister, Windows'ta çalışmaz; geliştirici makinesiyle CI aynı sonucu
vermezdi), cosmic-ray (oturum veritabanı ve ayrı işçi kurulumu, bu ölçekte fazlası). Kapsam
bilerek saf çekirdek: veritabanı katmanında mutant başına tam entegrasyon koşusu dakikalar sürer.

## 2. Sertleştirme taraması: schemathesis, tek denetim "5xx yok"

`backend/scripts/sertlestirme.py` tek kullanımlık veritabanı kurar, API'yi aynı süreçte bellek
içi nesne deposuyla açar ve schemathesis 4.32.7'yi tüm uçlara (GET dahil, durumlu zincirlerle)
sürer. İlk koşu **88 uçta 500** buldu; ayrıntı [sertlestirme.md](../operasyon/sertlestirme.md).

**Karar: istemci kaynaklı veritabanı hatası merkezi işleyicide sınıflanır.** Aralık dışı tamsayı,
NUL baytı, olmayan kayda referans, yeniden adlandırmada benzersizlik ve zorunlu alana `null`
88 ucun her birinde ayrı ayrı sınır koymak yerine `app/core/exceptions.py`'de SQLSTATE ile
ayrılır: 22003/22021/22P02/22P05 ve sürücünün parametre hatası → 422 `GECERSIZ_DEGER`;
23503 → 422 `GECERSIZ_REFERANS` (silmede 409 `BAGLI_KAYIT`); 23505 → 409 `CAKISMA`; 23502 → 422
`DOGRULAMA` alan adıyla. Liste dar: sınıf 22'nin geri kalanı (ör. sıfıra bölme) sunucu kusurudur
ve 500 kalır. Bedel: yanıt çoğu durumda hangi alanın hatalı olduğunu söyleyemez; arayüz bu
değerleri seçicilerden ürettiği için etkilenen pratikte API istemcisidir.

Reddedilen: her `int` yol/sorgu parametresine `le=2**63-1` eklemek (yüzlerce imza, yeni uçta
unutulur); şemaya özel bir `Kimlik` tipi (aynı unutulma riski, NUL ve FK sınıflarını çözmez).

Düzeltmeden sonra: 277 uç, 13.098 örnek, **0 sunucu hatası**. CI `sertlestirme` işi.

## 3. Dayanıklılık: kesintide zarif bozulma, veri kaybı yok

| Kesinti | Karar |
|---|---|
| Redis | Oran sınırı süreç içi yedek sayaca geçer (koruma kalkmaz, giriş kilitlenmez; N işçide sınır en çok N kat gevşer). Refresh iptal listesi okunamazsa yenileme reddedilir ama 500 değil **503** `HIZMET_KULLANILAMAZ` (replay'e kapı açmamak için güvenli taraf). |
| Nesne deposu | Yükleme başarısızsa sürüm kaydı açılmaz, 503. MinIO istemcisi 3 sn bağlantı süresi ve tek bağlantı denemesiyle kurulur (SDK varsayılanı yükleme isteğini 21 sn asılı tutuyordu). |
| MQTT / veritabanı | Alım işçisi geçici veritabanı hatasında 0,5 → 15 sn arası altı kez yeniden dener; broker koparsa üstel beklemeyle (en çok 30 sn) yeniden bağlanır; kalıcı oturum (`clean_session=False`, sabit istemci kimliği) + QoS 1 ile kopukken gelen mesajlar kaybolmaz; tekrar teslim idempotent. |

`backend/tests/test_s28_dayaniklilik.py` her kararı sabitler; düzeltme geri alındığında testler
düşüyor (4/4 ölçüldü).

## 4. Alan şifrelemesi: özetlenemeyen sırlar

TOTP sırrı ve webhook imza anahtarı doğrulama/imza için düz hâlde gerekir, özetlenemez; ADR-0022
TOTP şifrelemesini ertelemişti. `SifreliMetin` SQLAlchemy tipi (Fernet, `f1:` önekli) yazarken
şifreler, okurken çözer; servis kodu değişmedi. Anahtar `VERI_SIFRELEME_ANAHTARLARI` (virgüllü,
ilki yazım için: döndürme), verilmezse `SECRET_KEY`'den HKDF ile türetilir ve türetilmiş anahtar
her zaman son okuma anahtarı olarak kalır. Göç `e6b8d0f2a4c6` mevcut değerleri şifreler, geri
almada çözer.

Sonuç: anahtar yedeğin parçasıdır (başka kuruluma geri yüklenen tenant'ın 2FA'sı anahtarsız
çalışmaz) ve `SECRET_KEY` döndürme artık bir ön adım ister; ikisi [dr.md](../operasyon/dr.md)'de.
Açık: OIDC client secret tenant ayar JSONB'sinde düz (aynı desen JSONB alanına uygulanacak).

Reddedilen: PostgreSQL `pgcrypto` (anahtar SQL oturumlarından geçer, loglara düşebilir);
uygulama dışı KMS (kuruluma özgü bağımlılık; arayüz ileride KMS'e açılabilir).

## 5. Görev ayrımı kişi düzeyinde

Kullanıcı kılavuzunu koddan doğrularken bulundu: satınalma talebi, izin talebi ve fazla mesaide
ayrım yalnız roldeydi; hem kayıt hem onay yetkisi olan kişi (ör. admin) kendi talebini
onaylayabiliyordu. Sayımda kişi düzeyi kural zaten vardı. Üçüne de aynı kural: kaydı açan kişi
onaylayamaz, 403. Onaylarım kendi kayıtları listelemez, sayaçta gösterir
(`kendi_kayitlarim`, eski `kendi_sayimlarim`'ın genellemesi). Demo tohumu onayları ilgili demo
onaycısıyla verir.

## 6. Rapor hazır bildirimi

Bildirim kuralı tanımlıydı ama rapor servisi outbox olayını hiç yazmıyordu; test olayı elle
eklediği için kusur görünmüyordu. Olay artık raporu `hazir` yapan işlemin içinde yazılır;
`test_s28_rapor_bildirimi.py` API → outbox → bildirim üretici zincirini uçtan uca sınar.

## 7. Tedarik zinciri ve sır taraması

- **SBOM:** CI `sbom` işi her build'de CycloneDX 1.6 üretir (backend ortamı cyclonedx-bom 7.2.1;
  ön yüz üretim bağımlılıkları @cyclonedx/cyclonedx-npm 2.1.0) ve artefakt olarak saklar.
- **Bağımlılık güncelleme:** Dependabot (pip ve npm haftalık, GitHub Actions ve Docker aylık); mevcut
  pip-audit ve `npm audit --audit-level=high` kapıları sürüyor.
- **Sır taraması:** pre-commit'te gitleaks 8.30.1 + `.gitleaks.toml` (varsayılan kurallar; satır
  hedefli dar istisnalar). Tüm git geçmişi ve çalışma ağacı temiz tarandı.
- **İmaj imzalama: bu sprintte yok, bilerek.** İmzalanacak bir yayın hattı (kayıt defteri, etiketli
  imaj) henüz yok; CI imajı kurup taramıyor ve dağıtmıyor. Kayıt defteri seçildiğinde yayın işine
  cosign anahtarsız imza (GitHub OIDC) + SBOM eki eklenir ve dağıtım tarafında doğrulama
  (`cosign verify`) zorunlu tutulur. Doğrulanamayan bir adımı "yapıldı" diye yazmamak için ertelendi.

## 8. Operasyon ve doküman seti

- Runbook: [olay-mudahale.md](../operasyon/olay-mudahale.md) (önem dereceleri, roller, iletişim
  şablonları, güvenlik olayı, suçlamasız inceleme, kesinti davranış tablosu),
  [nobet.md](../operasyon/nobet.md), [tatbikatlar/takvim.md](../operasyon/tatbikatlar/takvim.md).
  Hata bütçesi panosu S19'da vardı ("Kalan bütçe · 30 gün"); yeniden yapılmadı.
- Kılavuzlar: [kullanıcı el kitabı](../kilavuz/kullanici-el-kitabi.md) (modül modül),
  [yönetici kılavuzu](../kilavuz/yonetici-kilavuzu.md) (fabrika yöneticisi + platform operatörü).
  El kitabındaki her iddia koddan doğrulandı; yanlış çıkan 9 iddia düzeltildi, ikisi ürün
  kusuruydu (§5, §6).
- API portalı: `backend/scripts/api_portali.py` → `docs/api/` (Redoc, şema sayfaya gömülü; dosyadan
  açılır). Girişte kimlik doğrulama, tenant başlığı, hata kodu tablosu, webhook imzası. CI şemanın
  güncel olduğunu denetler.
- Sürüm notları: `backend/scripts/surum_notlari.py` sprint (`S27 …`) ve Conventional Commits
  başlıklarını gruplar, CHANGELOG'un işaretli bloğunu yeniler; `--surum vX` "Yayımlanmamış"ı
  sürüme çevirir.
- Uyum: ISO 27001 eşlemesi güncellendi (8.16, 8.24, 8.29, 8.31 ✅; olay yönetimi ve süreklilik
  maddeleri eklendi), ISO 9001 eşlemesi yeni.

## Kabul

| Ölçüt (yol haritası) | Kanıt |
|---|---|
| Mutasyon skoru eşiği CI'da | `mutasyon` işi, eşik %90, ölçülen %93,4 |
| Üç kesinti senaryosu testli, veri kaybı yok | `test_s28_dayaniklilik.py` (6 test) |
| SBOM her build'de | `sbom` işi (yerelde 97 + 94 bileşen doğrulandı) |
| Doküman seti yayınlanmış ve sürüm treniyle güncellenebilir | `docs/kilavuz/`, `docs/operasyon/`, `docs/api/` (CI denetimli), `surum_notlari.py` |
| Sertleştirme pası bulguları kapatılmış | 88 uçta 500 → 0; kod okumasıyla bulunan 3 kusur kapandı |
