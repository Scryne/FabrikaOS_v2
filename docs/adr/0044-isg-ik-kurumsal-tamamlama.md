# ADR-0044 — İSG ve İK Kurumsal Tamamlama (S26-B)

- **Durum:** Kabul edildi (S26-B, Faz 6)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0025 (S26-A kalite), ADR-0010 (CAPA), S11 İSG/İK çekirdeği (zimmet, sertifika),
  4857 sayılı İş Kanunu md. 53, Çalışanların İSG Eğitimleri Yönetmeliği (tekrar sıklığı)

## Bağlam

S11, İSG'de kaza ve risk kaydını, İK'da personel, izin talebi, mesai, zimmet ve sertifikayı
tutuyordu. Kurumsal kullanım beş boşluk bırakıyordu: izin onayı bakiyeye bakmıyordu, kimin kime
bağlı olduğu yoktu, işe giriş / çıkış adımları kayıt dışıydı, İSG eğitimlerinin geçerliliği ve
KKD teslimi izlenmiyordu, kazadan düzeltici faaliyete (CAPA) köprü yoktu.

---

## 1. Yıllık izin bakiyesi: kanuni tablo, kümülatif, onayda zorlanır

`ik/izin_hakedis.py` saf fonksiyondur. Hak her **tamamlanan** hizmet yılında doğar: 1–5 yıl 14,
6–14 yıl 20, 15 yıl ve üstü 26 gün; hakkın doğduğu gün 18 yaş ve altı ya da 50 yaş ve üstündeyse en
az 20. `Personel.yillik_izin_hakki` sözleşmeyle verilen daha cömert hak için alt sınırdır (az olan
değil, çok olan geçerli). Kullanılmayan izin devreder: bakiye = Σ hak − Σ onaylı yıllık izin.

**Kapı onayda.** Talepte bakiye yalnız uyarıdır (form gösterir); iki talep aynı bakiyeyi ayrı ayrı
"yeterli" görebilir. Onay, personel satırı `FOR UPDATE` ile kilitlenip bakiye yeniden hesaplanarak
verilir; aşım 409 `IZIN_BAKIYE_YETERSIZ`. Eşzamanlı iki onay testinde biri 200, diğeri 409 (kilit
mutasyonla kaldırılınca test düşüyor).

**İşe giriş tarihi yoksa kapı uygulanmaz.** Kıdem bilinmeden bakiye hesaplanamaz; ekran bunu açıkça
söyler. Reddedilen: tarihsiz personelde bakiyeyi 0 saymak (S11'den gelen tüm tarihsiz kayıtların
izinleri birden reddedilirdi).

**Bilinen sınır:** gün sayısı takvim günüdür (S11). Hafta tatili ve resmî tatil düşülmüyor; iş günü
takvimi (vardiya/tatil tablosu) bağlanınca `izin_gun_sayisi` değişir, bakiye kuralı aynı kalır.

## 2. Org şeması: tek alan, döngü yasak

`Personel.yonetici_id` (öz-FK, SET NULL). Atama ayrı uçtan (`PUT /personeller/{id}/yonetici`);
zincir yukarı yürünür, atanan kişi zincirde görünürse 409 `ORG_DONGU`, kendine atama 422. Ağaç
istemcide kurulur; departman süzgecinde yöneticisi dışarıda kalan kişi kök olur.

## 3. İşe giriş / çıkış kontrol listesi

`PersonelKontrolListesi` personel × tür tekildir; maddeler şablondan kopyalanan JSONB dizisidir
(şablon değişirse açık listeler etkilenmez). Açma idempotenttir. Çıkış listesinde "Zimmetler iade
alındı" maddesi personelin `zimmetli` kaydı varken işaretlenemez (409 `ACIK_ZIMMET`); liste
tamamlanınca personel pasifleşir.

## 4. İSG eğitim matrisi

`IsgEgitimi` bir oturumdur (konu, tarih, geçerlilik ayı; 0 = süresiz), `EgitimKatilimi` eğitim ×
personel tekildir. Hücre durumu en yeni katılımın geçerlilik sonuna göre: `gecerli`, `yaklasiyor`
(30 gün), `gecmis`, `eksik` (zorunlu ama katılım yok), `gerekmez`. Zorunluluk
`EgitimGereksinimi` (departman × konu; boş departman herkese). Tekrar sıklığı tehlike sınıfına bağlı
olduğu için kayıtta seçilir (12 / 24 / 36 ay), sistem işyerinin sınıfını varsaymaz.

## 5. KKD: zimmetin kategorisi

Reddedilen: ayrı bir KKD teslim tablosu. KKD teslimi `kategori='kkd'` zimmettir (S11 zimmet akışı,
iade ve denetim izi aynen kullanılır). `KkdGereksinimi` departman × KKD; eksik raporu aktif
`zimmetli` KKD adlarını gereksinimle büyük/küçük harf ve boşluk duyarsız eşler. İade edilen KKD
yeniden eksik görünür.

## 6. Acil durum tatbikatı

Tür, tarih, yer, katılımcı, tahliye süresi (sn), bulgular, planlanan sonraki tarih. Sonraki tarih
tatbikattan sonra olmalı (422). Ekran gecikmiş planları sayar.

## 7. Kaza → CAPA köprüsü

`POST /is-kazalari/{id}/capa` hem `isg:yaz` hem `kalite:yaz` ister ve kalite modülü aktif olmalıdır.
Kaza satırı kilitlenir; `uygunsuzluklar.kaynak_kaza_id` UNIQUE ikinci savunmadır. İkinci istek 409
`CAPA_ZATEN_VAR`. Önem kaza ağırlığından gelir (hafif → orta, orta → yüksek, ağır/ölümcül →
kritik). Kaza listesi bağlı vakayı tek sorguda getirir ve uygunsuzluk çekmecesine derin bağlantı
verir (`/uygunsuzluklar?uygunsuzluk=<id>`).

## Sonuçlar

- Göç `d4f6b8a0c2e3` (up/down testli): 6 tablo, 3 sütun.
- Demo tohumu: genel müdür + org, 5 eğitim, eğitim ve KKD gereksinimleri, KKD teslimleri, iki
  tatbikat (biri gecikmiş planlı), yarım işe giriş listesi, kazadan açılmış CAPA. Yıllık izin
  kapısı yüzünden demo personelinin işe giriş tarihleri en az 1 yıl öne alındı.
- Ön yüz: Eğitim & KKD (eğitimler, matris, KKD durumu, gereksinimler), Tatbikatlar, Org şeması;
  personel detayında izin bakiyesi, yönetici seçici, giriş/çıkış sekmesi; izin formunda bakiye
  uyarısı ve personel seçici; zimmet formunda kategori; kaza tablosunda CAPA sütunu.
