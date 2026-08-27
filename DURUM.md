# DURUM — FabrikaOS_v2 — çok kiracılı MES+ERP

> **Ne bu dosya:** sertifika değil **envanter**. 2026-08-27 denetiminde ölçülen gerçek durum.
> "Çalışmıyor" yazan satır kusur değil, kayıt. Kapanış standardı:
> `ScryneOS/🎯 100-Command-Center/Kapanis-Standardi.md`

**Ölçüm tarihi:** 2026-08-27
**Tek cümle:** Frontend derleniyor ama **backend testlerinin 822'si de hata veriyor**: test veritabanı kimlik bilgisi çalışmıyor.

## Ne çalışıyor

- **Frontend derlemesi başarılı** (Vite + React + antd + echarts). Uyarı: `antd` 1,27 MB
  ve `echarts` 1,03 MB — kod bölme yapılmamış, 1250 KB eşiği aşılıyor.
- Depo en büyük ikinci proje: 172 commit, 1094 kaynak dosyası, 185 test dosyası.
- `docker-compose`: api · ingestion · db · redis · minio · mqtt · traefik.

## Ne çalışmıyor / doğrulanmadı

- **Backend test paketi hiç koşmuyor. 822 hata, 0 başarısızlık** — hepsi aynı sebepten:
  `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "fabrikaos"`.
  Yani testler kırık değil, **veritabanına bağlanamıyorlar**.
- Bir Postgres cevap veriyor ama o **PolitikDesk'in konteyneri** (5432 portunda `pd-db`).
  İki proje aynı portu istiyor; ikisi aynı anda ayağa kalkamaz.
- Sonuç: bu projede **hiçbir şey test edilmiş sayılmaz.** 185 test dosyasının durumu BİLİNMİYOR.

## Ne yarım

- Dal `feat/s25-tedarik-zinciri` üzerinde ama içerik `origin/main` ile birebir aynı —
  yani dal boş, iş main'de.
- Beş ayrı feature dalı duruyor: s23-guvenlik-uyum · s24-mes-derinlik · s25-tedarik-zinciri ·
  persona-pano-landing-derinlestirme · svb-vitrin-butunlugu.
- `REFACTOR-BACKLOG.md` açık.

## Sonraki adım

`docker compose up` ile kendi Postgres'ini kaldır (port çakışmasını çöz), testleri koştur, sonucu buraya yaz.
