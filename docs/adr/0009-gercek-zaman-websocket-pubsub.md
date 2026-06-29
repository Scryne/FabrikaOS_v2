# ADR-0009: Gerçek-zaman çekirdeği — WebSocket + Redis pub/sub (tenant-kapsamlı)

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
Pano ve listelerin canlı güncellenmesi gerekir: bir makine durumu değişince, üretim verisi
girilince ya da iş emri ilerletilince ilgili kullanıcılar **anında** görmelidir. Bunun için
sunucudan istemciye itme (push) kanalı şarttır. En kritik kısıt (R3): bir tenant'ın olayı
**asla** başka tenant'a sızmamalıdır.

Mevcut altyapı: S4'te dayanıklı domain olayları için transactional outbox (`giden_olaylar`)
kuruldu (teslimat S18). Redis zaten refresh-iptal + rate-limit için kullanılıyor.

## Karar
- **Taşıma: FastAPI WebSocket + Redis pub/sub.** Tek uç: `GET /api/v1/ws/olaylar`.
- **Kanal adı `tenant:<slug>:olaylar`** → **izolasyon yapısaldır**: WebSocket yalnız kendi
  tenant'ının kanalına abone olur; başka tenant'ın olayını dinleyemez. Kanal sadece slug ile
  isimlendirildiğinden cross-tenant dinleme mümkün değildir.
- **WebSocket kimliği query ile:** tarayıcı WS el sıkışmasında özel başlık (Authorization)
  gönderemediği için `?token=<access>&tenant=<slug>`. Kabul öncesi üç kontrol:
  1. access token doğrulanır (geçersiz → `4401`),
  2. token'daki `tenant_slug` istekteki `tenant` ile **eşleşmek zorunda** (çapraz-tenant →
     `4403`) — REST'teki cross-tenant korumasının WS karşılığı,
  3. tenant aktif + aboneliği geçerli (değilse → `4404`).
  Ardından `accept()` + yalnız o tenant kanalına `subscribe`.
- **Yayın `core/gercekzaman.py::yayinla(slug, olay)`** — Redis PUBLISH. **Best-effort**:
  Redis erişilemezse `try/except` ile yutulur, **istek asla düşmez**. Canlı UI sinyali gözden
  kaçsa bile istemci olay-tetikli/periyodik refetch ile yakalar.
- **İki olay sınıfı (ayrım bilinçli):**
  - **Geçici UI sinyalleri** (`makine.durum`, `uretim.eklendi`, `isemri.durum`,
    `isemri.olusturuldu`) → doğrudan pub/sub ile yayınlanır. Yük yalnız kimlik/ids taşır;
    istemci olayı alınca ilgili sorguyu (örn. `/oee/ozet`) yeniden çeker → o an commit'lenmiş
    veriyi görür. Yayın commit'ten hemen önce yapılır; commit düşse bile istemci refetch'te
    eski veriyi görür (zararsız), olay payload'ı veri taşımaz.
  - **Dayanıklı domain olayları** (webhook) → outbox'ta kalır (S18). Pub/sub bunların yerine
    geçmez; tamamlayıcıdır.
- **WS yaşam döngüsü:** iki paralel görev — (a) pub/sub → ws iletimi, (b) ws.receive ile
  istemci kopuşunun tespiti. Biri biterse diğeri iptal edilir; çıkışta `unsubscribe` + kapama.

## Sonuçlar
- (+) Tenant izolasyonu kanal adıyla yapısal olarak garanti; testte beta WS'i alfa olayını
  hiç almaz (entegrasyon testi `test_s7_gercekzaman.py`).
- (+) Yayın best-effort → gerçek-zaman katmanı asla yazma işlemini bozmaz/yavaşlatmaz.
- (+) Mevcut JWT/tenant çözümleme yeniden kullanıldı; yeni güven sınırı eklenmedi.
- (−) Çoklu sunucu (yatay ölçek) senaryosunda pub/sub Redis üzerinden fan-out olur; tek Redis
  şimdilik yeterli. Ölçekte Redis cluster / dedicated pub/sub düşünülecek (S19+).
- (−) Pub/sub geçici; sunucu yeniden başlarsa o anki olaylar kaybolabilir (dayanıklılık
  gereken olaylar zaten outbox'ta). Bilinçli tercih.
- WS kapatma kodları uygulama-tanımlı: `4401` kimlik, `4403` çapraz-tenant, `4404` tenant.
