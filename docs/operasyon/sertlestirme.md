# Sertleştirme pası — bulgular ve kapanış (S28, 2026-11-01)

Amaç: istemci ne gönderirse göndersin sunucunun 5xx dönmemesi. Araç: schemathesis 4.32.7
(OpenAPI şemasından sınır değerler, bozuk tipler, NUL baytı, dev tamsayılar, Unicode
uç durumları ve oluştur → oku → güncelle → sil zincirleri üreten durumlu test). Tek denetim
`not_a_server_error`. Ayrıntı ve gerekçe: [ADR-0047](../adr/0047-kurumsal-guvence.md).

```bash
python backend/scripts/sertlestirme.py --db-url postgresql+asyncpg://…/fabrikaos_sertlik \
    --redis-url redis://…/3      # tek kullanımlık veritabanı; CI'da `sertlestirme` işi
```

Kapsam dışı (bilerek): `/kimlik/*` (çıkış, parola, 2FA taramanın kendi oturumunu düşürür; ayrı
testleri var), `/platform/*` (ayrı kimlik), `/kullanicilar` (admin'i pasifleştirebilir).

## Bulgular

| # | Sınıf | Nerede | Örnek girdi | Önce | Kök neden | Sonra |
|---|---|---|---|---|---|---|
| 1 | Aralık dışı tamsayı | 76 GET ucu (her `{id}` yolu ve `*_id` filtresi), yazma uçlarında da | `/makineler/9223372036854775808` | 500 | `int` parametresi sınırsız; asyncpg 2⁶³'ü BIGINT'e bağlayamıyor | 422 `GECERSIZ_DEGER` |
| 2 | NUL baytı | metin alan her uç | `{"baslik": "a\u0000b"}` | 500 | PostgreSQL metinde `\0` kabul etmez (22021); JSONB'de 22P05 | 422 `GECERSIZ_DEGER` |
| 3 | Olmayan kayda referans | 10 oluşturma ucu (uygunsuzluk, iş kazası, firma, talep, kontrol planı, ölçüm cihazı, risk, personel …) | `{"makine_id": 987654321}` | 500 | FK ihlali (23503) servis katmanında önceden denetlenmiyordu | 422 `GECERSIZ_REFERANS` |
| 4 | Yeniden adlandırmada çakışma | `PATCH /vardiyalar/{id}`, `PATCH /durus-nedenleri/{id}` | var olan ad | 500 | oluşturmada denetlenen benzersizlik güncellemede denetlenmiyordu (23505) | 409 `CAKISMA` |
| 5 | Zorunlu alana açık `null` | `PATCH /makineler/{id}` (ve aynı desendeki kısmi güncellemeler) | `{"ad": null}` | 500 | kısmi güncelleme DTO'su `null`'ı "gönderilmedi"den ayırmıyor (23502) | 422 `DOGRULAMA`, alan adıyla; kayıt bozulmaz |
| 6 | Bozuk CSV | `POST /saha/olcumler/csv` | tırnaksız alanda satır sonu | 500 | `csv.Error` yakalanmıyordu; `newline=""` eksikti | 422 |
| 7 | UTF-8 olmayan CSV | aynı uç | Excel'in Windows-1254 CSV'si | 500 (taramada değil, kod okumasında bulundu) | `.decode("utf-8-sig")` korumasız | 422, "CSV UTF-8 olarak kaydedilmeli" |
| 8 | Depo yokken uzun bekleme | `POST /belgeler/{id}/surumler` | MinIO kapalı | 503, **21 sn** sonra | SDK varsayılanı 5 dk zaman aşımı + 5 deneme; ad çözümü her denemede tekrar | 3 sn bağlantı, tek bağlantı denemesi |
| 9 | Görev ayrımı yalnız rolde | satınalma talebi, izin talebi, fazla mesai onayı | hem kayıt hem onay yetkisi olan kişi kendi talebini onaylıyor | 200 (kusur) | kılavuz iddiası koddan doğrulanırken bulundu; sayımda vardı, diğerlerinde yoktu | 403; Onaylarım kendi kayıtlarını listelemez |
| 10 | Rapor hazır bildirimi hiç üretilmiyor | `POST /raporlar` | rapor biter | bildirim yok (kusur) | kural tanımlı, outbox olayı yazılmıyordu; test olayı elle ekliyordu | olay rapor işlemiyle aynı transaction'da; uçtan uca testli |

9 ve 10 tarayıcının değil, kullanıcı kılavuzundaki her iddianın koddan doğrulanmasının bulgusu:
tarama yanıt kodunu denetler, iş kuralını değil.

**Neden merkezi düzeltme.** 1–5, 88 ucun her birine ayrı sınır koymak yerine hata işleyicide
(`app/core/exceptions.py`) kapandı: hepsi veritabanının istemci değerini reddetmesidir ve
SQLSTATE bunu kesin söyler. Liste bilerek dar tutuldu: 22003, 22021, 22P02, 22P05, sürücünün
"invalid input for query argument" hatası ve 23502/23503/23505. Sınıf 22'nin geri kalanı
(ör. 22012 sıfıra bölme) sunucu kusurudur ve 500 olarak kalır. Bedeli: yanıt hangi alanın
hatalı olduğunu çoğu durumda söyleyemez (not-null hariç). Kullanıcı arayüzü bu değerleri zaten
seçicilerden ürettiği için bu yanıtlar pratikte API istemcilerine gider.

## Sonuç

| Koşu | Uç | Örnek | 5xx |
|---|---|---|---|
| İlk GET taraması | 154 | 4.972 | 76 |
| İlk yazma taraması | 147 | 8.391 | 12 (+1 zaman aşımı) |
| Düzeltme sonrası, tüm yöntemler (`sertlestirme.py`, tohum 28) | 277 | 13.098 | **0** |

Geri dönüşü önleyen testler: `backend/tests/test_s28_sertlestirme.py` (her sınıftan bir
temsilci; işleyici kaydı kaldırılınca 5/5 düşüyor, ölçüldü).

## Kalan uyarılar (hata değil)

- *Missing test data*: ~80 uç rastgele kimlikle hep 404 döndü; derin dallar (ör. var olan bir
  iş emrinin durum geçişleri) yalnız durumlu aşamada ve sınırlı ölçüde denendi. Bu dallar
  modül entegrasyon testlerinde ayrıca kapsanıyor.
- *Schema validation mismatch*: ~90 uç üretilen girdilerin çoğunu 422 ile reddetti; şemadaki
  serbest `string` alanların gerçekte biçim (tarih, kod deseni) beklemesinden. Şemaya `pattern`
  eklemek taramayı derinleştirir; sonraki iyileştirme.
