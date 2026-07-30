# REFACTOR-BACKLOG

Bu dosya, **modül maratonu** sırasında tespit edilen ama maratonu durdurmamak için
uygulanmayan değişikliklerin kaydıdır. Kullanıcı bu listeyi maraton bitiminde **tek
parti hâlinde** gözden geçirecektir (2026-07-30 tarihli talimat).

## Buraya ne yazılır?

1. **Kırıcı (breaking) değişiklik önerileri** — mevcut API sözleşmesini, alan adlarını,
   endpoint yapısını veya yanıt şeklini değiştirecek her şey.
2. **Mevcut uçlarda doğrulama sıkılaştırması** — Pydantic sınır/desen/ondalık hassasiyet/
   tarih tutarlılığı eklemeleri. Şema *şekli* değişmese bile davranışsal kırıcı değişikliktir:
   bugün kabul edilen bir gövde yarın 422 döner. **Yalnız bu maratonda yeni eklenen uçlarda
   doğrudan uygulanır**; maraton öncesi var olan uçlarda buraya yazılır.

## Buraya ne YAZILMAZ (doğrudan uygulanır)?

- Eklemeli (additive) sertleştirme: indeks, CHECK/UNIQUE/NOT NULL kısıtı (veri denetimi +
  backfill ile birlikte), `ondelete` semantiği, `selectinload` ile N+1 giderme, tipleme,
  saf fonksiyon ayrıştırması, hata yönetimi, servis/repository ayrımı.
- Bu maratonda **yeni yazılan** uçlardaki her türlü doğrulama sıkılaştırması.

## Girdi biçimi

Her girdi şu dört başlığı doldurur:

- **Mevcut tasarım** — bugün ne var.
- **Neden yanlış** — hangi somut sorun/risk.
- **Önerilen değişiklik** — ne yapılmalı.
- **Etki alanı (blast radius)** — etkilenen uçlar, FE bileşenleri, openapi tüketicileri
  (codegen tipleri, dış API anahtarı istemcileri, webhook alıcıları, mobil plan).

---

## Girdiler

<!-- Girdiler sprint sırasına göre eklenir. Henüz girdi yok. -->
