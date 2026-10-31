# ADR-0043 — Sertleştirme ve Kapasite: bandit kapısı, NFR-01 ölçümü, çok işçili API (S22)

- **Durum:** Kabul edildi (S22, Faz 5) — UAT ve GA `v1.0.0` pilot kabulüne bağlı, açık
- **Tarih:** 2026-11-01
- **İlgili:** NFR-01, NFR-02, NFR-05; ADR-0040 (metrikler), ADR-0041 (prod katmanı)

## Bağlam
GA kapısı "NFR'ler karşılanır, kritik güvenlik bulgusu yok, UAT kabul" ister. NFR-01 hiç
ölçülmemişti; statik güvenlik taraması CI'da yoktu; API tek süreçle çalışıyordu.

## Kararlar
1. **Bandit CI kapısı** (orta ve üstü). B608'in 22 noktası tek tek incelendi, hepsi güvenli
   (beyaz liste / doğrulanmış şema / katalog tablo adı); kural CI'da atlanır, gerekçe
   `docs/operasyon/guvenlik-ve-performans.md`'de. Kalan yüksek bulgu yok.
2. **NFR-01 ölçümü tekrarlanabilir**: `perf/k6/nfr01_liste.js`, uç başına p95 eşiği. Tek süreç
   20 kullanıcıda karşılıyor (p95 181 ms), 50'de kuyruk yüzünden aşıyor (469 ms).
3. **API çok işçili** (varsayılan 4): 50 kullanıcıda p95 154 ms, 340 istek/sn. Prometheus çok
   süreç modu (`PROMETHEUS_MULTIPROC_DIR`) eklendi; olmasa `/metrics` rastgele bir işçinin
   sayacını verirdi (canlı ölçümle doğrulandı).

## Sonuçlar
- (+) Kapasite sayıyla biliniyor; ölçek kolu (işçi sayısı) belli.
- (−) ZAP/pentest yapılmadı; 50 tenant ve büyük veriyle yük testi yapılmadı.
- **Açık (dışa bağlı):** UAT (pilot müşteri kabulü) ve GA `v1.0.0` sürüm etiketi. Pilotsuz GA
  ilan edilmez; CHANGELOG `Yayımlanmamış` başlığı altında tutulur.
