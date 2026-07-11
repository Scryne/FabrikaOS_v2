# S-VB — Vitrin Bütünlüğü + Bildirim Merkezi Çekirdeği (Tasarım)

**Tarih:** 2026-07-11 · **Sprint:** Faz 4B / S-VB (köprü) · **ADR:** 0021

> Bu belge, yol haritasındaki **Faz 4B — Vitrin Bütünlüğü** köprü sprintinin kodlanmaya
> hazır tasarım sözleşmesidir. Format S8–S18 tasarım belgeleriyle aynıdır; kurallar
> `tenant-rbac-conventions` + `turkce-identifier-standardi` + `alembic-fan-out` skill'lerine
> bağlıdır. Global DoD (yol haritası) aynen geçerlidir.

## 1. Amaç

`/tanitim` blueprint vitrini müşteriye **"27 Entegre Modül"** vaat ediyor; bazı **görünür**
özellikler henüz kodda yok. Bu sprint, o boşluğu **demo-yeterli çekirdek** seviyede kapatarak
vitrini dürüst + etkileyici yapar (truth-in-advertising). **Yeni çekirdek icat edilmez**;
kanıtlanmış desenler yeniden kullanılır:

- transactional outbox (`giden_olaylar` / `olay_yayinla`) — S4
- kenar-tetikli tarama (`/yaklasanlari-tara`) — S12
- ayrı-süreç relay/tüketici (webhook relay, ingestion worker) — S8/S18
- saf skor fonksiyonu + tablo testi (`oee_hesapla`, `riskMatris`) — S3/S11
- S13 saf/deterministik AI çıkarım deseni
- gerçek-zaman yayını (`core/gercekzaman.py`, WS + Redis pub/sub) — S7

Yedi kalem tek dikey dilimde teslim edilir: **(1)** Bildirim Merkezi çekirdeği,
**(2)** SLA takibi, **(3)** AI operatör eşleştirme, **(4)** tedarikçi performans skoru,
**(5)** coğrafi site haritası, **(6)** takvim görünümü, **(7)** landing hizalama.

Bu kalemlerin **kurumsal-tam** sürümleri Faz 6'da derinleşir (bildirim → S27, tedarikçi
skoru/PO → S25, vardiya/operatör atama → S24). Burada amaç kapsam değil, **vitrin ↔ gerçek
örtüşmesi**.

## 2. Kavramlar ve sözlük (turkce-identifier-standardi)

| Kavram | Identifier | Açıklama |
|---|---|---|
| Bildirim | `Bildirim` / `bildirimler` | Kişi-hedefli, tenant içi uygulama-içi bildirim (kaynak = bir outbox olayı) |
| Bildirim tercihi | `BildirimTercihi` / `bildirim_tercihleri` | Kullanıcı × olay türü aç/kapa + kanal seçimi |
| Bildirim imleci | `BildirimImleci` / `bildirim_imleci` | Tüketicinin işlediği son `giden_olaylar.id` (yüksek-su-işareti) |
| Bildirim üretici | `bildirim_uretici` | Outbox → hedef kullanıcı fan-out + kanal gönderim döngüsü (ayrı süreç) |
| Bildirim kanalı | `BildirimKanali` | Soyutlama: `UygulamaIciKanal` (birincil), `EPostaKanali` (SMTP), `SmsKanali` (stub) |
| SLA aşımı | `sla.asildi` | İş emri / talep hedef tarihini geçtiğinde yazılan outbox olayı |
| Operatör eşleştirme | `operator_eslestir` | İş emri gereksinimi ⋈ personel → sıralı öneri (saf, deterministik) |
| Tedarikçi skoru | `tedarikci_skoru` | Firma performans skoru (saf fonksiyon, 0–100) |

**Yeni olay türleri:** `sla.asildi` (outbox + webhook kataloğu), `bildirim.yeni`
(yalnız gerçek-zaman — zil canlı güncellemesi için, outbox'a yazılmaz).

## 3. Bildirim Merkezi (çekirdek)

### 3.1 Veri modeli (tenant şeması)

- `bildirimler`: `kullanici_id` FK `kullanici.id` CASCADE (index), `giden_olay_id` FK
  `giden_olaylar.id` CASCADE (kaynak olay; nullable — sistem bildirimleri için), `olay_turu`
  (denorm, filtre + tercih eşleştirme), `baslik`, `govde` (kısa metin), `veri` JSONB
  (derin-bağlantı için: `{kaynak_tur, kaynak_id}`), `onem` (`bilgi`/`uyari`/`kritik`),
  `okundu` bool (default false, index), `okundu_tarihi` nullable.
  **Benzersizlik:** `UNIQUE(kullanici_id, giden_olay_id)` — tüketici tekrar tarasa da çift
  bildirim üretmez (idempotency korunur; `giden_olay_id IS NULL` satırlar kısıta girmez).
- `bildirim_tercihleri`: `kullanici_id` FK CASCADE, `olay_turu`, `uygulama_ici` bool
  (default true), `eposta` bool (default false); `UNIQUE(kullanici_id, olay_turu)`.
  Kayıt yoksa varsayılan: uygulama-içi açık, e-posta kapalı.
- `bildirim_imleci`: tek-satırlık imleç — `son_islenen_olay_id` BigInteger (default 0).
  Tüketici verimliliği için (kısıt zaten çift-yazımı önler; imleç yalnız tarama penceresini
  daraltır).

### 3.2 Olay → hedef kullanıcı yönlendirme (saf, testli)

Sistem olayları `govde`'de kullanıcı taşımaz; hedef **izne göre** belirlenir. Saf fonksiyon
`bildirim_hedefleri(olay_turu, govde) -> HedefKurali`:

| Olay türü | Hedef kuralı | Önem |
|---|---|---|
| `stok.kritik` | `stok:oku` izinli tüm aktif kullanıcılar | uyari |
| `sozlesme.yaklasiyor` | `crm:oku` | uyari |
| `anomali.tespit` | `ai:oku` | kritik |
| `rapor.hazir` | yalnız `govde.olusturan_kullanici_id` | bilgi |
| `ariza.olustu` | `uretim:oku` | kritik |
| `oee.dustu` | `uretim:oku` | uyari |
| `sla.asildi` | `govde.sorumlu_kullanici_id` (varsa) + ilgili modül `:oku` | uyari |
| `duyuru.yeni` | tüm aktif kullanıcılar (oturum) | bilgi |

İzin→kullanıcı çözümü tek sorguda (`kullanici ⋈ kullanici_rol ⋈ rol_izin ⋈ izin`), yalnız
`aktif=true`. Yönlendirme kuralları tablo-testli; yeni olay eklemek = tabloya satır.

### 3.3 Üretici (tüketici döngüsü) — ayrı süreç

`backend/app/modules/bildirim/uretici.py` + `backend/scripts/bildirim_uretici.py`
(webhook relay / ingestion worker deseni; uygulama restart'ından bağımsız, yatay ölçeklenir):

1. Public'ten **aktif** tenant'ları döner; her şemada `search_path` ile çalışır.
2. `giden_olaylar` içinden `id > bildirim_imleci.son_islenen_olay_id` ∧ `olay_turu ∈
   BILDIRIM_OLAYLARI` satırlarını `id` sırasıyla okur.
3. Her olay için `bildirim_hedefleri` → hedef kullanıcı kümesi; her hedef için tercih
   kontrolü (`uygulama_ici` açıksa) → `bildirimler` INSERT (ON CONFLICT DO NOTHING —
   idempotent), `veri` derin-bağlantısı doldurulur.
4. Her yeni bildirim için gerçek-zaman `bildirim.yeni` yayını (kullanıcı-hedefli;
   `tenant:<slug>:kullanici:<id>` kanalı veya mevcut tenant kanalı + FE süzgeci — S7 deseni).
5. E-posta tercihi açık hedefler için `EPostaKanali.gonder` (SMTP iskeleti + şablon;
   `SmsKanali` stub — yalnız log). Kanal hatası bildirimi düşürmez (uygulama-içi otoritedir).
6. İmleç `son_islenen_olay_id`'ye ilerletilir.

Bayrak: `--tek-tur` (test/e2e determinizmi), `--araligi <sn>` (döngü, varsayılan 10),
`--tenant <slug>`. Webhook relay ile **çakışmaz**: relay `giden_olaylar.durum`'u kullanır;
bildirim üretici bağımsız `id` imleci kullanır (iki tüketici, tek outbox — decoupled).

### 3.4 Yönetim uçları (`/api/v1/bildirimler`)

Kişisel yüzey — kullanıcı **yalnız kendi** bildirimlerini görür/yönetir (izin gerekmez,
oturum yeter; filtre dependency'de `oturum.kullanici_id`'ye zorlanır — controller'a bırakılmaz):

| Uç | Not |
|---|---|
| `GET /bildirimler` | sayfalı; `?okundu=` + `?olay_turu=` filtresi; yalnız oturum kullanıcısının |
| `GET /bildirimler/ozet` | `{okunmamis, toplam, son: [...5]}` — zil rozeti beslemesi |
| `POST /bildirimler/{id}/okundu` | tek bildirimi okundu işaretle (başkasının 404) |
| `POST /bildirimler/tumunu-okundu` | oturum kullanıcısının tümü |
| `GET /bildirim-tercihleri` | katalog + kullanıcının override'ları (yoksa varsayılan) |
| `PUT /bildirim-tercihleri` | olay türü başına `{uygulama_ici, eposta}` upsert (katalog dışı 422) |

## 4. SLA takibi

- **Alan:** `is_emirleri.hedef_tarih` + `talepler.hedef_tarih` (nullable timestamptz).
  Oluşturma/güncelleme DTO'larına opsiyonel eklenir; boş = SLA takibi yok.
- **Tarama (kenar-tetikli, S12 `yaklasanlari-tara` deseni):**
  - `POST /is-emirleri/sla-tara` (`isemri:yaz`) + `POST /talepler/sla-tara` (`crm:yaz`).
  - Açık (terminal olmayan) + `hedef_tarih < now()` kayıtlar için `sla.asildi` outbox olayı
    (`govde = {kaynak_tur: "is_emri"|"talep", kaynak_id, kod, hedef_tarih,
    sorumlu_kullanici_id?}`).
  - **Dedup (bir-kez garantisi):** aynı kaynak için mevcut `sla.asildi` olayı varsa yeniden
    yazılmaz (`giden_olaylar` sorgusu: `olay_turu='sla.asildi' ∧ govde->>'kaynak_tur' ∧
    govde->>'kaynak_id'`). S12 `sozlesme.yaklasiyor` dedup'ının birebir kopyası.
- **Zincir:** `sla.asildi` → bildirim üretici → sorumluya (+modül `:oku`) bildirim.
  Ayrıca webhook kataloğuna (`OLAY_TURU_KATALOGU`) eklenir → dış sistemler abone olabilir.

## 5. AI Operatör Eşleştirme

`POST /tahmin/operator-eslesme` (izin `ai:oku`; modül `ai`). Gövde: `{is_emri_id}` (veya
`{makine_id, is_turu?}`). Yanıt: sıralı `[{personel_id, ad, departman, unvan, skor,
gerekce}]`.

**Saf, deterministik skor** (`app/modules/ai/operator_eslestir.py`, S13 çıkarım deseni —
model artefaktı gerekmez, kural-tabanlı; birim testli):

```
skor = 0.5 * departman_uygunlugu   # iş emri makine/tür ↔ personel departman/unvan eşleşmesi
     + 0.3 * gecmis_performans      # personelin kullanıcı_id'siyle kapattığı iş emri sayısı/hızı (normalize)
     + 0.2 * musaitlik              # bugün onaylı izinde değil (İK izin_talepleri)
```

Yalnız `personel.aktif` + `kullanici_id` dolu adaylar. Girdi yoksa (geçmiş yok) skor
bileşeni 0'a düşer — bölme yok, deterministik. Sonuç kesin sıralanır (skor, sonra
`personel_id` tie-break). Tenant izole (tüm sorgular `search_path`).

> Not: "beceri matrisi" (S26) ve gerçek vardiya-atama (S24) sonrası bu skor derinleşir;
> bu sürüm demo-yeterli kural-tabanlı öneridir.

## 6. Tedarikçi performans skoru (öz)

`app/modules/crm/tedarikci_skoru.py` — saf fonksiyon `tedarikci_skoru(...) -> SkorDetay`
(0–100 + bileşen kırılımı; `oee_hesapla` tarzı, birim testli). Firma detayında gösterilir:
`GET /firmalar/{id}/skor` (`crm:oku`).

Mevcut sinyallerden (PO/teslim verisi S25'te gelene dek):

```
skor = 40 * kalite_gecme_orani     # firmanın malzemelerine bağlı kalite_kontrolleri geçme oranı
     + 30 * sozlesme_uyumu          # aktif/zamanında kapanan sözleşme oranı
     + 30 * talep_cozum_orani       # firmayla ilişkili taleplerin çözülme oranı
```

Sinyal yoksa ilgili bileşen nötr (0.5) sayılır ve `gerekce`'de "yetersiz veri" işaretlenir —
skor asla NaN/bölme hatası vermez. Deterministik + tenant izole.

> Not: "zamanında teslim" tam bileşeni **satınalma siparişi teslim alma** (S25) ile eklenir;
> spec'te alan ayrılmıştır (`SkorDetay.zamaninda_teslim = None` → S25'te dolar).

## 7. Coğrafi site haritası

- **Alan:** `makineler.enlem` + `makineler.boylam` (nullable Float). `GET /ikiz/durum`
  yanıtına makine başına koordinat eklenir (varsa); yeni ağır uç açılmaz.
- **FE:** `/ikiz` içinde ikinci sekme "Harita" (`GorunumGecis`): **React-Leaflet** — koordinatı
  olan makineler durum LED renginde işaretlenir (ikiz LED dili birebir); işaretçi tıklama →
  makine kartı (durum + pencere OEE + son veri). Koordinatsız makineler SVG şema sekmesinde
  kalır. Harita katmanı ücretsiz OSM tile (offline/self-host notu ADR-0021'de).

## 8. Takvim görünümü

- **FE-only** (yeni backend yok). `TakvimZaman` primitifi (uiplani §4) ile `/bakim-planlari`
  ekranına "Takvim" sekmesi: bakım planı periyotları + onaylı izin talepleri
  (`/izin-talepleri?durum=onaylandi`) tek zaman şeridinde; tür pimi renkli.
- İSG eğitim + kalibrasyon takvim beslemeleri S26'da bağlanır (spec'te sekme hazır, veri
  o sprintte).

## 9. Landing hizalama (`/tanitim`)

- `frontend/src/modules/tanitim/TanitimSayfasi.tsx` + i18n + `MODUL_KATALOGU` **gerçekle
  örtüşür**: modül ızgarası fiilen var olan `MODUL_KATALOGU` girdilerinden üretilir.
- **"27 modül" iddiası** ya (a) gerçek katalog sayısıyla güncellenir (bugün 19; Faz 7 ile
  23), ya da (b) "yol haritasında" olanlar açıkça *gelecek* rozetiyle ayrılır. Yalan
  vitrin bırakılmaz (truth-in-advertising — köprü kapısı şartı).
- Bu kalem **backend/model değiştirmez**; sunum + kopya + i18n işidir.

## 10. Entitlement & roller

- **Bildirim çapraz-kesen özelliktir** (duyuru gibi): yeni modül kapısı YOK; uçlar oturum
  yeterli, kişisel süzgeç dependency'de. `bildirim` router'ı `modul_gerekli` almaz.
- Operatör eşleştirme `ai` modülü + `ai:oku` (mevcut). Tedarikçi skoru `crm:oku` (mevcut).
  Coğrafi harita `uretim:oku` (mevcut, `/ikiz/durum`).
- **Yeni izin/rol gerekmez.** SLA tarama mevcut modül izinleriyle korunur.
- `sla.asildi` webhook kataloğuna eklenir (S18 `OLAY_TURU_KATALOGU` — katalog 8 → 9).

## 11. Migration (tenant ağacı, fan-out up/down)

Tek revizyon (`alembic-fan-out` skill; `public` + ≥2 tenant şemasında up/down testli):

- `bildirimler`, `bildirim_tercihleri`, `bildirim_imleci` tabloları (§3.1)
- `is_emirleri.hedef_tarih`, `talepler.hedef_tarih` kolonları (§4)
- `makineler.enlem`, `makineler.boylam` kolonları (§7)

Downgrade tam tersini yapar (kolon drop + tablo drop). Public migration **gerekmez**
(entitlement değişmiyor; yeni modül yok).

## 12. Frontend

| Ekran / bileşen | İş |
|---|---|
| `BildirimPaneli.tsx` (kabuk üst bar) | Zil → `GET /bildirimler/ozet` rozeti; açılır liste (okundu/tümü okundu); `bildirim.yeni` WS ile canlı artış |
| `/bildirim-tercihleri` (Yönetim) | Olay türü başına anahtar (uygulama-içi/e-posta) |
| `/ikiz` "Harita" sekmesi | React-Leaflet + durum LED işaretçileri |
| `/bakim-planlari` "Takvim" sekmesi | `TakvimZaman` (bakım + onaylı izin) |
| Firma detay | Tedarikçi skoru kartı (bileşen kırılımı + "yetersiz veri" notu) |
| İş emri detay / `/tahminler` | "Operatör öner" → sıralı personel + skor `MiniBar` + gerekçe |
| İş emri / Talep formu | Opsiyonel `hedef_tarih` alanı |
| `/tanitim` | Modül ızgarası `MODUL_KATALOGU`'yla hizalanır |

Yeni `/ozet` + hook'lar için `npm run codegen`. Görsel dil `DESIGN.md` + `uiplani.md`
(DurumPim/MiniBar/PanelKart/OzetSerit; hat rengi kimliği korunur).

## 13. Test stratejisi

- **Saf:** `bildirim_hedefleri` yönlendirme (her olay türü → doğru izin kümesi),
  SLA dedup, `operator_eslestir` determinizm + tie-break + boş-girdi, `tedarikci_skoru`
  determinizm + yetersiz-veri nötrü + sınır (0/100), FE `grafikSecenek`/`TakvimZaman`.
- **Migration:** head'de 3 tablo + 4 kolon var; down→yok; up→geri (fan-out ≥2 tenant).
- **Bildirim üretici:** olay → doğru kullanıcılar bildirim alır; tercih kapalı → almaz;
  ikinci tur → **çift bildirim yok** (unique kısıt); imleç ilerler; **tenant izolasyonu**
  (A'nın olayı B'nin kullanıcısına asla bildirim üretmez — 7 kritik test ailesine
  "bildirim tenant-izolasyonu" eklenir).
- **SLA:** hedef geçmiş açık kayıt → tek `sla.asildi` → tek bildirim; ikinci tara → dup yok;
  terminal kayıt olay üretmez.
- **Uçlar:** `/bildirimler` yalnız kendi kayıtları (başkasının okundu 404), `/bildirimler/ozet`
  sayım doğruluğu, tercih upsert + katalog dışı 422; operatör eşleştirme `ai:oku` 403 +
  izolasyon; tedarikçi skoru `crm:oku` 403 + izolasyon.
- **FE:** vitest — zil paneli okundu/canlı artış, tercih ekranı, harita sekmesi render,
  takvim sekmesi, operatör öner listesi. i18n görünür Türkçe metin + ARIA rolü (mevcut sınır).

## 14. Riskler / bilinçli kararlar

- **Çok-tüketicili outbox:** bildirim üretici webhook relay'den bağımsız `id` imleci +
  `UNIQUE(kullanici_id, giden_olay_id)` ile çalışır; `giden_olaylar.durum` yalnız webhook
  relay'in koordinasyon alanıdır. İki tüketici tek outbox'ı çakışmasız okur.
- **İzne-göre hedefleme:** sistem olayları kullanıcı taşımadığından bildirim izin sahiplerine
  gider (rol-tabanlı). Kişi-hedefli olaylar (`rapor.hazir`, `sla.asildi` sorumlusu)
  `govde`'deki kullanıcıya gider. Kural tablosu tek doğruluk kaynağı, testli.
- **Tedarikçi skoru "öz" sürüm:** zamanında-teslim bileşeni S25 (PO teslim alma) ile dolar;
  şimdilik alan `None`. Skor honest — eksik sinyali "yetersiz veri" olarak işaretler.
- **SMS yalnız stub**, e-posta iskelet (SMTP + şablon). Uygulama-içi kanal otoritedir; kanal
  hatası bildirimi düşürmez. Gerçek e-posta/SMS sağlayıcısı S27'de.
- **Coğrafi harita self-host tile:** OSM public tile dev'de; prod'da tenant gizliliği için
  self-host/ücretli tile kararı ADR-0021'e not; koordinat girişi (makine formu) opsiyonel.
- **"27 modül" dürüstlük borcu:** landing sayısı gerçek katalog + gelecek rozetiyle
  hizalanır; köprü kapısının asıl amacı budur.
