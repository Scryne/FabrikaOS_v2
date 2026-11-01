# Tatbikat takvimi (S28)

Bir runbook ancak son çalıştırıldığı gün kadar doğrudur. Her tatbikat bu klasöre
`YYYY-MM-DD-<tür>.md` kaydı bırakır ve aşağıdaki tabloyu günceller; bulunan her tuzak ilgili
runbook'a işlenmeden tatbikat kapanmaz.

## Sıklık

| Tatbikat | Sıklık | Nasıl | Başarı ölçütü |
|---|---|---|---|
| Tenant yedek → geri yükleme | Çeyrekte bir (her tenant yılda en az bir kez) | `yedek.py tatbikat <tenant> --rapor docs/operasyon/tatbikatlar` ([dr.md §5](../dr.md#5-tatbikat-çeyrekte-bir)) | Satır sayıları eşit, doğrulama yeşil, süre kayıtlı |
| PITR (küme bir ana dönüş) | Yılda iki kez, ayrı sunucuda | [dr.md §2](../dr.md#2-tüm-kümeyi-bir-ana-döndür-pitr) | Hedef andaki veri birebir; RPO ≤ 15 dk ölçülmüş |
| Bağımlılık kesintisi (Redis, MinIO, MQTT) | Her sürümde otomatik + yılda bir canlı | `pytest backend/tests/test_s28_dayaniklilik.py` (CI); canlıda staging'de servisi durdur | [olay-mudahale.md §7](../olay-mudahale.md#7-bağımlılık-kesintisinde-beklenen-davranış-s28-testli)'deki davranış birebir |
| Göç geri alma | Her şema değiştiren sürümden önce, staging'de | `goc_dagit.py --yedek-dizini` → `alembic downgrade -1` ([dr.md §3](../dr.md#3-göç-dağıtımı-ve-geri-alma)) | Geri alma sonrası uygulama açılıyor, veri tam |
| Nöbet hattı | Her nöbet devrinde | `amtool alert add FabrikaOSTestAlarmi …` ([nobet.md](../nobet.md#alarm-yönlendirmesi)) | Nöbetçi 15 dk içinde kabul etti |
| Masa başı olay tatbikatı | Yarıyılda bir | Bir Ö1 senaryosu (ör. "yanlış tenant'a geri yükleme") ekiple sesli yürütülür | Herkes rolünü ve ilk üç adımı biliyor; boşluklar aksiyona dönüştü |

## Plan ve kayıt

| Tarih | Tatbikat | Durum | Kayıt |
|---|---|---|---|
| 2026-10-31 | Tenant yedek → geri yükleme (demo) | ✅ 1,9 sn | [kayıt](2026-10-31-demo.md) |
| 2026-10-31 | PITR (yerel küme) | ✅ 0,8 sn, RPO = `archive_timeout` | [kayıt](2026-10-31-pitr.md) |
| 2026-11-01 | Bağımlılık kesintisi (otomatik, 6 senaryo) | ✅ veri kaybı yok | `backend/tests/test_s28_dayaniklilik.py` |
| 2027-01 | Tenant yedek → geri yükleme (pilot tenant) | ⏳ | — |
| 2027-01 | Masa başı: yanlış tenant'a geri yükleme | ⏳ | — |
| 2027-04 | PITR (staging sunucusu, WAL arşivi ayrı birimde) | ⏳ | — |
| 2027-04 | Canlı kesinti: staging'de Redis + MQTT durdurma | ⏳ | — |
