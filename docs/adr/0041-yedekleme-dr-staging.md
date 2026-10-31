# ADR-0041 — Yedekleme, Felaket Kurtarma ve Staging (S20)

- **Durum:** Kabul edildi (S20, Faz 5)
- **Tarih:** 2026-10-31
- **İlgili:** NFR-11 (tenant-farkında yedek, tanımlı RPO/RTO), şartname §6.5 (RPO ≤ 15 dk, RTO ≤ 2 sa,
  çeyreklik tatbikat), ADR-0003 (şema başına tenant), ADR-0004 (Alembic fan-out), ADR-0006
  (TimescaleDB hypertable), `docs/uyum/kisisel-veri-envanteri.md`

## Bağlam

Yedek hiç yoktu; geri yükleme hiç denenmemişti (risk R10). İki ayrı ihtiyaç var: (1) tüm
kümenin bir felaketten belirli bir ana dönmesi, (2) **tek bir tenant'ın** diğerlerine
dokunmadan geri alınması (bir müşterinin yanlışlıkla sildiği veri, bozuk bir göç). İkincisi
çok kiracılı bir ürünün asıl DR sorusudur ve şema başına tenant tasarımının vaadidir.

## Kararlar

### 1. İki katman
| Katman | Araç | Ne için | Hedef |
|---|---|---|---|
| Küme | Sürekli WAL arşivi + haftalık `pg_basebackup` | Tüm kümeyi bir ana döndürme (PITR) | RPO ≈ `archive_timeout` (300 sn) |
| Tenant | Günlük mantıksal yedek (`app/operasyon/yedek.py`) | Tek tenant'ı bağımsız geri yükleme | RPO 24 sa (küme katmanı tamamlar) |

Tek tenant'ın son 5 dakikaya dönmesi gerekirse: küme PITR'ı **ayrı bir sunucuya** yapılır,
oradan o tenant'ın yedeği alınıp canlıya tenant geri yüklemesiyle taşınır (runbook).

### 2. Tenant yedeği `pg_dump --schema` değil
TimescaleDB hypertable verisi tenant şemasında değil `_timescaledb_internal` chunk'larındadır;
şema bazlı döküm `uretim_verileri` ve `enerji_tuketim`'i **boş** yedekler. Bunun yerine:
- Yapı yedeklenmez, göçlerden kurulur: yedek Alembic revizyonunu kaydeder; geri yüklemede boş
  şema o revizyona yükseltilir (hypertable'lar göçte oluşur), veri yüklenir, sonra `head`'e.
- Veri tablo tablo `COPY … (FORMAT binary)`; hypertable'a COPY chunk'lara kendiliğinden dağılır.
- Bütün tablolar tek `REPEATABLE READ` anlık görüntüsünde okunur (tutarlı kesit).
- CAGG (sürekli toplulaştırma) türevdir; geri yüklemeden sonra yeniden hesaplanır.

### 3. Geri yükleme: geçici şema → doğrula → atomik yer değiştir
Geçici şemaya kurulur; **yabancı anahtarlar yükleme süresince kaldırılıp aynı tanımla yeniden
eklenir** (şemada FK döngüleri var, sıralı yükleme mümkün değil; yeniden ekleme bütün satırların
referans bütünlüğünü bir kez daha doğrular; süper kullanıcı gerekmez). Satır sayısı ve sıra
bağımsız içerik parmak izi yedektekiyle birebir tutmadan canlı şemaya dokunulmaz. Sonra tek
işlemde `tenant_<slug>` → `eski_<slug>_<zaman>`, geçici → `tenant_<slug>`. Eski şema geri dönüş
için saklanır (elle silinir). TimescaleDB şema adı değişikliğinde hypertable/CAGG kataloğunu
güncelliyor (testle doğrulandı). Bütünlük: dosya SHA-256 + satır sayısı + parmak izi.
PostgreSQL ana sürümü farklıysa (ikili COPY taşınmaz) reddedilir.

### 4. Staging: aynı yedek + anonimleştirme
Staging, prod compose katmanıyla (`docker-compose.prod.yml`, `APP_ENV=staging`) aynı yığındır;
verisi prod yedeğinin adında `staging` geçen bir tenant'a geri yüklenip **yerinde maskelenmesidir**
(`app/operasyon/anonim.py`). Maskeler deterministiktir (satır kimliğinden): ilişkiler korunur.
Envanterdeki kişisel veri alanları, denetim izi (koruma tetikleyicisi işlem süresince kapatılıp
yeniden açılır), oturum/kurtarma kodu/API anahtarı silinir; webhook'lar kapatılır, bekleyen
outbox olayları gönderilmiş sayılır (staging prod'un müşterilerine konuşmaz). Prod tenant'ına
uygulanamaz (ad koruması). Kalan risk: operasyonel serbest metin alanları (malzeme açıklaması,
duyuru) taranmaz.

### 5. Göç dağıtımı tenant başına yalıtılır
`alembic --name tenant upgrade head` tek koşuda bütün tenant'ları yükseltir; biri hata verirse
kalanlar eski revizyonda kalır. `scripts/goc_dagit.py` her tenant'ı ayrı yükseltir, birinin hatası
diğerlerini durdurmaz, tenant başına önceki/sonraki revizyonu ve süreyi raporlar, isteğe bağlı
olarak **göç öncesi o tenant'ın yedeğini** alır (bozuk göç tek komutla geri alınır).

### 6. Prod hazırlığı
Traefik: HTTP→HTTPS yönlendirmesi, Let's Encrypt **DNS-01** ile joker sertifika (`*.alan-adi`;
HTTP-01 joker vermez), alt alan adı = tenant, `/metrics` dışarıya kapalı, pano kapalı. Uvicorn
`--proxy-headers` (denetim izindeki IP gerçek istemci olur). DB/MinIO portları dışa kapalı.

## Sonuçlar
- (+) Tek tenant geri yükleme kanıtlı: testte felaket (silme/değiştirme/çöp) → geri yükleme →
  parmak izi yedek anıyla birebir, komşu tenant değişmedi, uygulama girişi ve listeler çalıştı.
  Demo tenant'ında tatbikat (67 tablo, 1.927 satır) 1,9 sn.
- (+) PITR akışı yerel kümeyle kanıtlı (hedef ana dönüş doğru; arşiv gecikmesi = archive_timeout).
- (+) Staging kopyasında demo verisinin kişisel verisi taramada 0 (prod şemasında 855 eşleşme).
- (−) Tenant yedeği şifrelenmez; gizlilik depolama katmanına (şifreli disk / MinIO SSE) bırakıldı.
- (−) Prod compose katmanı Docker'da koşturulmadı (makinede test için Docker açılmıyor); ilk
  staging kurulumunda doğrulanacak.
- **Açık:** WAL arşivi ve yedek birimi aynı sunucuda; disk kaybına karşı nesne deposuna/başka
  bölgeye kopya (ör. WAL-G → S3) ilk prod kurulumunda. Tatbikat takvimi: çeyrekte bir
  (`docs/operasyon/dr.md`).
