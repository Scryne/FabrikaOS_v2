# Yedekleme ve felaket kurtarma — runbook (S20)

Kararlar: [ADR-0041](../adr/0041-yedekleme-dr-staging.md). Hedefler (şartname §6.5):
**RPO ≤ 15 dk**, **RTO ≤ 2 sa**, geri yükleme tatbikatı **çeyrekte bir**.

| Katman | Sıklık | Nerede | Saklama |
|---|---|---|---|
| WAL arşivi | sürekli (`archive_timeout=300`) | `wal-arsiv` biriminde | 35 gün |
| Küme temel yedeği (`pg_basebackup`) | haftalık | `yedek:/yedek/taban/` | 35 gün |
| Tenant mantıksal yedeği | günlük | `yedek:/yedek/tenant/` | 14 gün |
| Göç öncesi tenant yedeği | her dağıtımda | `goc_dagit.py --yedek-dizini` | dağıtım doğrulanınca |

Bütün komutlar `DATABASE_URL`'i uygulamayla aynı ortamdan okur. Konteynerde:
`docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm yedek '<komut>'`.

## 1. Tek tenant'ı geri yükle

Bir müşteri verisini yanlışlıkla sildi ya da bir göç tek tenant'ı bozdu.

```bash
python backend/scripts/yedek.py dogrula /yedek/tenant/demo-20261101T020000Z.zip   # önce bütünlük
python backend/scripts/yedek.py geri-yukle /yedek/tenant/demo-20261101T020000Z.zip --evet
```

- Geçici şemaya kurar, satır sayısı + içerik parmak izi yedekle birebir tutmazsa **durur ve
  canlıya dokunmaz**. Tutarsa canlıyla tek işlemde yer değiştirir; eski şema
  `eski_demo_<zaman>` olarak kalır.
- Geri yükleme yedek anına döner: o andan sonra yazılan veri yeni şemada yoktur, eski şemada
  durur. Gerekirse kayıtlar eski şemadan elle taşınır, sonra eski şema silinir:
  `DROP SCHEMA "eski_demo_<zaman>" CASCADE`.
- Uygulama yeniden başlatma gerektirmez (şema adı aynı).

**Son 24 saatten daha yakın bir ana dönmek gerekirse:** §2'deki PITR'ı **ayrı bir sunucuda**
yap, oradan `yedek.py al demo` ile o anın yedeğini al, bu dosyayla canlıda §1'i uygula.

## 2. Tüm kümeyi bir ana döndür (PITR)

Sunucu/disk kaybı, toplu bozulma.

1. Yeni (boş) bir veri dizini hazırla; en son **hedef andan önceki** temel yedeği aç:
   `tar -xzf /yedek/taban/<tarih>/base.tar.gz -C $PGDATA`
2. `postgresql.conf`'a ekle:
   ```
   restore_command = 'cp /wal-arsiv/%f %p'
   recovery_target_time = '2026-11-01 14:05:00+03'   # felaketten hemen önce
   recovery_target_action = 'promote'
   ```
3. `touch $PGDATA/recovery.signal`, sunucuyu başlat; `SELECT pg_is_in_recovery()` `f` dönünce
   terfi etmiştir. Hedef anın satırlarını doğrula, sonra uygulamayı bu sunucuya yönlendir.
4. `archive_mode`'u yeniden aç ve **yeni bir temel yedek al** (eski zaman çizelgesinden kopar).

Windows'ta deneme yaparken: `postgresql.conf` içindeki yolda ters bölüyü ikile; `pg_ctl start`
çıktısını bir boruya yakalama (başlatılan sunucu boruyu açık tutar, çağıran bekler).

## 3. Göç dağıtımı ve geri alma

```bash
python backend/scripts/goc_dagit.py --yedek-dizini /yedek/goc/$(date +%Y%m%d)
```

Her tenant için bir JSON satırı (`onceki`, `sonraki`, `basarili`, `hata`, `yedek`). Çıkış 1 ise
başarısız tenant'lar eski revizyonda kalmıştır, diğerleri yükselmiştir. Bozuk göç bir tenant'ın
verisini bozduysa o tenant'ın `…-goc-oncesi.zip` dosyasıyla §1 uygulanır; geri yükleme yedekteki
revizyona kurar ve `head`'e yükseltir — göç düzeltilmeden yeniden yüklemek aynı hatayı tekrarlar,
önce göçü düzelt.

## 4. Staging'i yenile (anonim prod kopyası)

```bash
# Bir kez: staging tenant'ını provizyonla (adında "staging" geçmeli)
# Sonra her yenilemede:
STAGING_YONETICI_PAROLA='<güçlü-parola>' python backend/scripts/yedek.py staging \
  /yedek/tenant/demo-<zaman>.zip --hedef demo-staging --yonetici-eposta yonetici@staging.test
```

Kopyada kişisel veri maskelenir, prod kullanıcılarının parolası kullanılamaz, webhook'lar kapalı,
bekleyen olaylar gönderilmiş sayılır; giriş yalnız verilen staging yöneticisiyle. Staging yığını
prod'la aynıdır: `docker-compose.prod.yml` + `APP_ENV=staging` + kendi alan adı.

## 5. Tatbikat (çeyrekte bir)

```bash
python backend/scripts/yedek.py tatbikat demo --dizin /yedek/tatbikat --rapor docs/operasyon/tatbikatlar
```

Yedek alır, geçici şemaya geri yükler, doğrular, süreleri ölçer, siler; canlıya dokunmaz. Rapor
`docs/operasyon/tatbikatlar/` altına yazılır ve depoya eklenir. PITR tatbikatı (§2) ayrı bir
sunucuda yılda en az iki kez.

| Tarih | Tür | Sonuç | Süre | Kayıt |
|---|---|---|---|---|
| 2026-10-31 | Tenant (demo, 67 tablo / 1.927 satır) | Başarılı | 1,9 sn | [kayıt](tatbikatlar/2026-10-31-demo.md) |
| 2026-10-31 | PITR (yerel küme) | Başarılı, hedef an doğru | 0,8 sn | [kayıt](tatbikatlar/2026-10-31-pitr.md) |

## Açık
- WAL arşivi ve yedek birimi aynı sunucuda: disk kaybında ikisi birlikte gider. İlk prod
  kurulumunda arşiv nesne deposuna / başka bölgeye kopyalanmalı (ör. WAL-G → S3/MinIO).
- Tenant yedeği şifrelenmez; şifreli disk ya da nesne deposu şifrelemesi (SSE) zorunlu.
- Prod compose katmanı Docker'da henüz koşturulmadı (ilk staging kurulumunda).
