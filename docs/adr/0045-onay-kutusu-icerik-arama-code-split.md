# ADR-0045 — Platform Deneyimi I: Birleşik Onay Kutusu, İçerik Araması, Rota Düzeyi Code-Split (S27-A)

- **Durum:** Kabul edildi (S27-A, Faz 6)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0021 (bildirim merkezi), ADR-0018 (entitlement), ADR-0024 (sayım görev ayrımı),
  ADR-0044 (izin bakiyesi), `uiplani.md` §11.3

## Bağlam

S27 dört parçadır: bildirim merkezi (S-VB'de yapıldı), birleşik onay kutusu, global içerik araması
ve UI Master Planı'nın kalan kalemleri. 2026-11-01 envanteri: onay kutusu ve içerik araması yoktu,
⌘K yalnız sayfa geziyordu; 66 sayfa `App.tsx`'te statik içe aktarıldığı için ilk açılışta tek
863 kB'lık (gzip 226 kB) ana parça iniyordu. S27 ikiye bölündü: S27-A bu üçü, S27-B dışa aktarma,
yazdırma ve erişilebilirlik pası.

---

## 1. Onaylarım: toplayıcı, karar verici değil

`GET /onaylarim` modüllerin onay akışlarına dokunmaz. Kullanıcının **onay izni olan ve modülü
aboneliğinde açık** kaynaklardan bekleyen işleri toplar: satınalma talebi (`satinalma:onay`), izin
talebi ve fazla mesai (`ik:onay`), sayım farkı (`stok:duzeltme`). Her kalem kendi modülünün mevcut
onay/red ucunu ve red gerekçesinin zorunlu olup olmadığını taşır; ekran o uca gider, yetki ve iş
kuralları (izin bakiyesi 409, görev ayrımı) modülde yine denetlenir.

**Görev ayrımı listede de görünür.** Kullanıcının kendi açtığı sayım listeye girmez (onaylayamaz);
sayısı `kendi_sayimlarim` olarak döner ve ekran "başka bir yetkili onaylamalı" der.

Reddedilen: ayrı bir "onay görevi" tablosu. Her modülün durumu zaten tek kaynak; kopyası
senkron hatası üretirdi.

## 2. İçerik araması: kaynak başına iki kapı

`GET /ara?q=` (en az 2 karakter) makine, malzeme, iş emri, firma, belge ve personelde kod/ad
üzerinde `ILIKE` arar. Her kaynak okuma iznini **ve** modül aboneliğini ayrı denetler; RBAC dışı
kayıt sonuçta hiç görünmez (test: İK rolü yalnız personel grubunu alır). `%` ve `_` kaçışlanır.
Kaynak başına en çok 10 sonuç. ⌘K paleti sayfaları ve kayıt gruplarını tek klavye listesinde
gösterir; içerik isteği 250 ms sakinleşince atılır.

Reddedilen: Postgres tam metin ya da ayrı arama motoru. Kiracı başına binlerle ölçülen kayıtta
indeksli `ILIKE` yeterli; ölçek değişirse kaynak fonksiyonları aynı arayüzle değiştirilir.

## 3. Derin bağlantı: `?kayit=<id>`

Onay kalemi ve arama sonucu, detayı çekmecede açılan listelere `?kayit=<id>` ile gider
(`useDerinKayit`): çekmece açık başlar, kapanınca parametre `replace` ile silinir. İş emri, belge,
satınalma talebi ve izin talebi listeleri bu kancaya geçti; firma (`?firma=`) ve uygunsuzluk
(`?uygunsuzluk=`) kendi adlarıyla çalışmaya devam eder.

## 4. Rota düzeyi code-split

Kabuk dışındaki 66 sayfa `React.lazy` ile ayrı parçalara alındı; kök `Routes` ve her iki kabuğun
`Outlet`'i `Suspense` içinde (sayfa yüklenirken menü kaybolmaz). Ana parça 863 kB → 246 kB
(gzip 226 → 78 kB). Kabuk, yetki kapıları ve gerçek-zaman sağlayıcısı statik kalır.

## Sonuçlar

- Yeni modül `app/modules/deneyim` (servis + uçlar), ön yüz `modules/deneyim` (Onaylarım, kancalar),
  `useDerinKayit`, `SayfaYukleniyor`.
- Menüde izinsiz "Onaylarım" girdisi (kalemler zaten izinle süzülür).
- Testler: onay kutusu izin süzgeci, görev ayrımı, kalemdeki ucun gerçekten çalışması; arama RBAC,
  kiracı izolasyonu, joker kaçışı. Arama izni ve görev ayrımı mutasyonla kaldırılınca testler düşüyor.
