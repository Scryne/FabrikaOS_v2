/**
 * Rota ağacı + açılışta sessiz giriş (bootstrap).
 *
 * Mount'ta ``oturumBaslat`` saklı refresh ile sessiz giriş dener; tamamlanana dek tam ekran
 * yükleniyor gösterilir. Korunan rotalar oturum + (gerekiyorsa) izin kapılarından geçer.
 */

import { lazy, Suspense, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { Spin } from 'antd';

import { oturumBaslat } from '@/api/kimlik';
import { tenantSakla } from '@/api/tenant';
import { LogoIsareti } from '@/components/Marka';
import { UygulamaKabugu } from '@/layouts/UygulamaKabugu';
import { sadeceDisKullanici } from '@/modules/dis/hooks';
import { GercekZamanSaglayici } from '@/modules/ortak/GercekZamanSaglayici';
import { PlatformGiris } from '@/platform/PlatformGiris';
import { PlatformKabuk } from '@/platform/PlatformKabuk';
import { PlatformKorunanRota } from '@/platform/PlatformKorunanRota';
import { IzinKapisi, KorunanRota } from '@/routes/KorunanRota';
import { useAuthStore } from '@/store/authStore';

// Rota düzeyi code-split (S27-A, ADR-0045): her sayfa kendi parçasında, ilk açılışta yüklenir.
const Onaylarim = lazy(() =>
  import('@/modules/deneyim/Onaylarim').then((m) => ({ default: m.Onaylarim })),
);
const AbonelikSayfasi = lazy(() =>
  import('@/modules/abonelik/AbonelikSayfasi').then((m) => ({ default: m.AbonelikSayfasi })),
);
const TahminPanosu = lazy(() =>
  import('@/modules/ai/TahminPanosu').then((m) => ({ default: m.TahminPanosu })),
);
const AnalitikPano = lazy(() =>
  import('@/modules/analitik/AnalitikPano').then((m) => ({ default: m.AnalitikPano })),
);
const BakimPlanListesi = lazy(() =>
  import('@/modules/bakim/BakimPlanListesi').then((m) => ({ default: m.BakimPlanListesi })),
);
const BildirimTercihleri = lazy(() =>
  import('@/modules/bildirim/BildirimTercihleri').then((m) => ({ default: m.BildirimTercihleri })),
);
const FirmaListesi = lazy(() =>
  import('@/modules/crm/FirmaListesi').then((m) => ({ default: m.FirmaListesi })),
);
const DisPortalSayfasi = lazy(() =>
  import('@/modules/dis/DisPortalSayfasi').then((m) => ({ default: m.DisPortalSayfasi })),
);
const DuyuruListesi = lazy(() =>
  import('@/modules/duyuru/DuyuruListesi').then((m) => ({ default: m.DuyuruListesi })),
);
const EntegrasyonKapisi = lazy(() =>
  import('@/modules/entegrasyon/EntegrasyonKapisi').then((m) => ({ default: m.EntegrasyonKapisi })),
);
const WebhookSayfasi = lazy(() =>
  import('@/modules/entegrasyon/WebhookSayfasi').then((m) => ({ default: m.WebhookSayfasi })),
);
const BelgeListesi = lazy(() =>
  import('@/modules/dys/BelgeListesi').then((m) => ({ default: m.BelgeListesi })),
);
const EnerjiTuketimListesi = lazy(() =>
  import('@/modules/enerji/EnerjiTuketimListesi').then((m) => ({
    default: m.EnerjiTuketimListesi,
  })),
);
const IzinListesi = lazy(() =>
  import('@/modules/ik/IzinListesi').then((m) => ({ default: m.IzinListesi })),
);
const PersonelDetay = lazy(() =>
  import('@/modules/ik/PersonelDetay').then((m) => ({ default: m.PersonelDetay })),
);
const PersonelListesi = lazy(() =>
  import('@/modules/ik/PersonelListesi').then((m) => ({ default: m.PersonelListesi })),
);
const KazaListesi = lazy(() =>
  import('@/modules/isg/KazaListesi').then((m) => ({ default: m.KazaListesi })),
);
const RiskListesi = lazy(() =>
  import('@/modules/isg/RiskListesi').then((m) => ({ default: m.RiskListesi })),
);
const IsgEgitimleri = lazy(() =>
  import('@/modules/isg/IsgEgitimleri').then((m) => ({ default: m.IsgEgitimleri })),
);
const Tatbikatlar = lazy(() =>
  import('@/modules/isg/Tatbikatlar').then((m) => ({ default: m.Tatbikatlar })),
);
const OrgSemasi = lazy(() =>
  import('@/modules/ik/OrgSemasi').then((m) => ({ default: m.OrgSemasi })),
);
const IsEmriEkrani = lazy(() =>
  import('@/modules/isemri/IsEmriEkrani').then((m) => ({ default: m.IsEmriEkrani })),
);
const KaliteKontrolListesi = lazy(() =>
  import('@/modules/kalite/KaliteKontrolListesi').then((m) => ({
    default: m.KaliteKontrolListesi,
  })),
);
const UygunsuzlukListesi = lazy(() =>
  import('@/modules/kalite/UygunsuzlukListesi').then((m) => ({ default: m.UygunsuzlukListesi })),
);
const KontrolPlanlari = lazy(() =>
  import('@/modules/kalite/KontrolPlanlari').then((m) => ({ default: m.KontrolPlanlari })),
);
const KontrolPlaniDetay = lazy(() =>
  import('@/modules/kalite/KontrolPlaniDetay').then((m) => ({ default: m.KontrolPlaniDetay })),
);
const OlcumCihazlari = lazy(() =>
  import('@/modules/kalite/OlcumCihazlari').then((m) => ({ default: m.OlcumCihazlari })),
);
const OlcumCihaziDetay = lazy(() =>
  import('@/modules/kalite/OlcumCihaziDetay').then((m) => ({ default: m.OlcumCihaziDetay })),
);
const SpcKarti = lazy(() =>
  import('@/modules/kalite/SpcKarti').then((m) => ({ default: m.SpcKarti })),
);
const IkizSayfasi = lazy(() =>
  import('@/modules/ikiz/IkizSayfasi').then((m) => ({ default: m.IkizSayfasi })),
);
const GirisSayfasi = lazy(() =>
  import('@/modules/kimlik/GirisSayfasi').then((m) => ({ default: m.GirisSayfasi })),
);
const GuvenlikSayfasi = lazy(() =>
  import('@/modules/kimlik/GuvenlikSayfasi').then((m) => ({ default: m.GuvenlikSayfasi })),
);
const KullaniciListesi = lazy(() =>
  import('@/modules/kimlik/KullaniciListesi').then((m) => ({ default: m.KullaniciListesi })),
);
const SsoDonusSayfasi = lazy(() =>
  import('@/modules/kimlik/SsoDonusSayfasi').then((m) => ({ default: m.SsoDonusSayfasi })),
);
const DenetimKayitlari = lazy(() =>
  import('@/modules/uyum/DenetimKayitlari').then((m) => ({ default: m.DenetimKayitlari })),
);
const KvkkSayfasi = lazy(() =>
  import('@/modules/uyum/KvkkSayfasi').then((m) => ({ default: m.KvkkSayfasi })),
);
const IceAktarma = lazy(() =>
  import('@/modules/aktarim/IceAktarma').then((m) => ({ default: m.IceAktarma })),
);
const KioskSayfasi = lazy(() =>
  import('@/modules/kiosk/KioskSayfasi').then((m) => ({ default: m.KioskSayfasi })),
);
const PrimitifVitrini = lazy(() =>
  import('@/modules/onizleme/PrimitifVitrini').then((m) => ({ default: m.PrimitifVitrini })),
);
const OnizlemePano = lazy(() =>
  import('@/modules/pano/OnizlemePano').then((m) => ({ default: m.OnizlemePano })),
);
const RaporListesi = lazy(() =>
  import('@/modules/rapor/RaporListesi').then((m) => ({ default: m.RaporListesi })),
);
const PanoSayfasi = lazy(() =>
  import('@/modules/pano/PanoSayfasi').then((m) => ({ default: m.PanoSayfasi })),
);
const CihazListesi = lazy(() =>
  import('@/modules/saha/CihazListesi').then((m) => ({ default: m.CihazListesi })),
);
const SozlesmeListesi = lazy(() =>
  import('@/modules/sozlesme/SozlesmeListesi').then((m) => ({ default: m.SozlesmeListesi })),
);
const TanitimSayfasi = lazy(() =>
  import('@/modules/tanitim/TanitimSayfasi').then((m) => ({ default: m.TanitimSayfasi })),
);
const DepoBakiye = lazy(() =>
  import('@/modules/stok/DepoBakiye').then((m) => ({ default: m.DepoBakiye })),
);
const KritikStok = lazy(() =>
  import('@/modules/stok/KritikStok').then((m) => ({ default: m.KritikStok })),
);
const SayimDetay = lazy(() =>
  import('@/modules/stok/SayimDetay').then((m) => ({ default: m.SayimDetay })),
);
const SayimListesi = lazy(() =>
  import('@/modules/stok/SayimListesi').then((m) => ({ default: m.SayimListesi })),
);
const SiparisDetay = lazy(() =>
  import('@/modules/stok/SiparisDetay').then((m) => ({ default: m.SiparisDetay })),
);
const SiparisListesi = lazy(() =>
  import('@/modules/stok/SiparisListesi').then((m) => ({ default: m.SiparisListesi })),
);
const MalzemeDetay = lazy(() =>
  import('@/modules/stok/MalzemeDetay').then((m) => ({ default: m.MalzemeDetay })),
);
const MalzemeListesi = lazy(() =>
  import('@/modules/stok/MalzemeListesi').then((m) => ({ default: m.MalzemeListesi })),
);
const SatinalmaTalepListesi = lazy(() =>
  import('@/modules/stok/SatinalmaTalepListesi').then((m) => ({
    default: m.SatinalmaTalepListesi,
  })),
);
const TalepListesi = lazy(() =>
  import('@/modules/talep/TalepListesi').then((m) => ({ default: m.TalepListesi })),
);
const TicariPano = lazy(() =>
  import('@/modules/ticari/TicariPano').then((m) => ({ default: m.TicariPano })),
);
const DurusEkrani = lazy(() =>
  import('@/modules/durus/DurusEkrani').then((m) => ({ default: m.DurusEkrani })),
);
const IzlenebilirlikSayfasi = lazy(() =>
  import('@/modules/uretim/IzlenebilirlikSayfasi').then((m) => ({
    default: m.IzlenebilirlikSayfasi,
  })),
);
const MakineDetay = lazy(() =>
  import('@/modules/uretim/MakineDetay').then((m) => ({ default: m.MakineDetay })),
);
const MakineListesi = lazy(() =>
  import('@/modules/uretim/MakineListesi').then((m) => ({ default: m.MakineListesi })),
);
const UretimVerileri = lazy(() =>
  import('@/modules/uretim/UretimVerileri').then((m) => ({ default: m.UretimVerileri })),
);
const UrunListesi = lazy(() =>
  import('@/modules/urun/UrunListesi').then((m) => ({ default: m.UrunListesi })),
);
const PlatformAbonelikListesi = lazy(() =>
  import('@/platform/AbonelikListesi').then((m) => ({ default: m.AbonelikListesi })),
);
const ProvizyonSihirbazi = lazy(() =>
  import('@/platform/ProvizyonSihirbazi').then((m) => ({ default: m.ProvizyonSihirbazi })),
);
const SaglikPano = lazy(() =>
  import('@/platform/SaglikPano').then((m) => ({ default: m.SaglikPano })),
);
const TenantDetay = lazy(() =>
  import('@/platform/TenantDetay').then((m) => ({ default: m.TenantDetay })),
);
const TenantListesi = lazy(() =>
  import('@/platform/TenantListesi').then((m) => ({ default: m.TenantListesi })),
);

/** Yalnız geliştirme: gerçek backend olmadan kabuk + pano tasarımını önizler (auth bypass). */
function OnizlemeOturum() {
  const ayarlaOturum = useAuthStore((s) => s.ayarlaOturum);
  useEffect(() => {
    tenantSakla('alfa');
    ayarlaOturum('onizleme', {
      id: 0,
      eposta: 'demo@alfa.test',
      ad_soyad: 'Demo Yönetici',
      roller: ['admin'],
      izinler: [
        'uretim:oku',
        'uretim:yaz',
        'saha:oku',
        'saha:yaz',
        'isemri:oku',
        'isemri:yaz',
        'bakim:oku',
        'bakim:yaz',
        'stok:oku',
        'stok:yaz',
        'satinalma:oku',
        'satinalma:yaz',
        'satinalma:onay',
        'kalite:oku',
        'kalite:yaz',
        'enerji:oku',
        'enerji:yaz',
        'isg:oku',
        'isg:yaz',
        'ik:oku',
        'ik:yaz',
        'ik:onay',
        'crm:oku',
        'crm:yaz',
        'sozlesme:oku',
        'sozlesme:yaz',
        'talep:oku',
        'talep:yaz',
        'dys:oku',
        'dys:yaz',
        'duyuru:oku',
        'duyuru:yaz',
        'ai:oku',
        'ai:egit',
        'analitik:oku',
        'rapor:oku',
        'rapor:yaz',
        'kullanici:oku',
        'kullanici:yaz',
        'rol:oku',
        'abonelik:oku',
      ],
      iki_asama_aktif: false,
    });
  }, [ayarlaOturum]);
  return <Outlet />;
}

/** Uygulama kabuğu + gerçek-zaman sağlayıcı (canlı WS aboneliği). */
function CanliKabuk() {
  return (
    <GercekZamanSaglayici>
      <UygulamaKabugu />
    </GercekZamanSaglayici>
  );
}

/** `/pano` rotası: yalnız dış portal kullanıcısı (tek izni dis:erisim) `/dis`e yönlenir. */
function PanoRota() {
  const kullanici = useAuthStore((s) => s.kullanici);
  if (kullanici && sadeceDisKullanici(kullanici.izinler)) {
    return <Navigate to="/dis" replace />;
  }
  return <PanoSayfasi />;
}

function TamEkranYukleniyor() {
  const { t } = useTranslation();
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 18,
      }}
    >
      <LogoIsareti boyut={40} />
      <Spin />
      <span style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>{t('ortak.yukleniyor')}</span>
    </div>
  );
}

export function App() {
  const [hazir, setHazir] = useState(false);

  useEffect(() => {
    void oturumBaslat().finally(() => setHazir(true));
  }, []);

  if (!hazir) return <TamEkranYukleniyor />;

  return (
    <Suspense fallback={<TamEkranYukleniyor />}>
      <Routes>
        {/* Kök `/` = kurumsal tanıtım (public landing) — doğrudan açılır, oturum gerektirmez. */}
        <Route path="/" element={<TanitimSayfasi />} />
        <Route path="/giris" element={<GirisSayfasi />} />
        {/* SSO dönüş adresi — IdP'de kayıtlı redirect_uri ile birebir aynı olmalı (S23). */}
        <Route path="/sso/donus" element={<SsoDonusSayfasi />} />

        {/* Platform (control-plane) düzlemi — tenant kabuğundan ayrık (S17/ADR-0019). */}
        <Route path="/platform/giris" element={<PlatformGiris />} />
        <Route path="/platform" element={<PlatformKorunanRota />}>
          <Route element={<PlatformKabuk />}>
            <Route index element={<TenantListesi />} />
            <Route path="tenantlar/:id" element={<TenantDetay />} />
            <Route path="yeni" element={<ProvizyonSihirbazi />} />
            <Route path="abonelikler" element={<PlatformAbonelikListesi />} />
            <Route path="saglik" element={<SaglikPano />} />
          </Route>
        </Route>

        <Route element={<KorunanRota />}>
          {/* Kiosk: kabuksuz tam ekran büyük pano (salt-okunur; ADR-0017). */}
          <Route
            path="kiosk"
            element={
              <IzinKapisi izin="uretim:oku" modul="uretim">
                <GercekZamanSaglayici>
                  <KioskSayfasi />
                </GercekZamanSaglayici>
              </IzinKapisi>
            }
          />
          {/* Dış portal: kabuksuz hafif kabuk (kiosk deseni) — yalnız dis-panel yüzeyi. */}
          <Route
            path="dis"
            element={
              <IzinKapisi izin="dis:erisim" modul="dis-portal">
                <DisPortalSayfasi />
              </IzinKapisi>
            }
          />
          <Route element={<CanliKabuk />}>
            <Route path="pano" element={<PanoRota />} />
            {/* Birleşik onay kutusu — oturum yeterli; kalemler izne göre süzülür (S27-A). */}
            <Route path="onaylarim" element={<Onaylarim />} />
            {/* Kişisel ayar — izin/modül kapısı yok (oturum yeterli; S-VB). */}
            <Route path="bildirim-tercihleri" element={<BildirimTercihleri />} />
            {/* Kişisel güvenlik: 2FA + oturum/cihaz yönetimi (oturum yeterli; S23). */}
            <Route path="guvenlik" element={<GuvenlikSayfasi />} />
            {/* S21 içe aktarma: tür başına izin + modül kapısı backend'de; sayfa yetkisizi kilitler. */}
            <Route path="ice-aktarma" element={<IceAktarma />} />
            {/* Uyum yüzeyi — modül kapısı YOK (çekirdek hak); yalnız izinle korunur. */}
            <Route
              path="denetim-kayitlari"
              element={
                <IzinKapisi izin="denetim:oku">
                  <DenetimKayitlari />
                </IzinKapisi>
              }
            />
            <Route
              path="kvkk"
              element={
                <IzinKapisi izin="kvkk:yonet">
                  <KvkkSayfasi />
                </IzinKapisi>
              }
            />
            <Route
              path="makineler"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <MakineListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="makineler/:id"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <MakineDetay />
                </IzinKapisi>
              }
            />
            <Route
              path="uretim-verileri"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <UretimVerileri />
                </IzinKapisi>
              }
            />
            <Route
              path="is-emirleri"
              element={
                <IzinKapisi izin="isemri:oku" modul="isemri">
                  <IsEmriEkrani />
                </IzinKapisi>
              }
            />
            {/* S24 — MES derinleşmesi: vardiya & duruş (tek çalışma alanı, iki rota), ürün/BOM, izlenebilirlik. */}
            <Route
              path="durus-kayitlari"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <DurusEkrani />
                </IzinKapisi>
              }
            />
            <Route
              path="vardiyalar"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <DurusEkrani baslangicGorunum="vardiyalar" />
                </IzinKapisi>
              }
            />
            <Route
              path="urunler"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <UrunListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="izlenebilirlik"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <IzlenebilirlikSayfasi />
                </IzinKapisi>
              }
            />
            <Route
              path="ikiz"
              element={
                <IzinKapisi izin="uretim:oku" modul="uretim">
                  <IkizSayfasi />
                </IzinKapisi>
              }
            />
            <Route
              path="saha/cihazlar"
              element={
                <IzinKapisi izin="saha:oku" modul="saha">
                  <CihazListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="malzemeler"
              element={
                <IzinKapisi izin="stok:oku" modul="stok">
                  <MalzemeListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="malzemeler/:id"
              element={
                <IzinKapisi izin="stok:oku" modul="stok">
                  <MalzemeDetay />
                </IzinKapisi>
              }
            />
            <Route
              path="stok/kritik"
              element={
                <IzinKapisi izin="stok:oku" modul="stok">
                  <KritikStok />
                </IzinKapisi>
              }
            />
            <Route
              path="depolar"
              element={
                <IzinKapisi izin="stok:oku" modul="stok">
                  <DepoBakiye />
                </IzinKapisi>
              }
            />
            <Route
              path="sayimlar"
              element={
                <IzinKapisi izin="stok:oku" modul="stok">
                  <SayimListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="sayimlar/:id"
              element={
                <IzinKapisi izin="stok:oku" modul="stok">
                  <SayimDetay />
                </IzinKapisi>
              }
            />
            <Route
              path="satinalma-talepleri"
              element={
                <IzinKapisi izin="satinalma:oku" modul="stok">
                  <SatinalmaTalepListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="satinalma-siparisleri"
              element={
                <IzinKapisi izin="satinalma:oku" modul="stok">
                  <SiparisListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="satinalma-siparisleri/:id"
              element={
                <IzinKapisi izin="satinalma:oku" modul="stok">
                  <SiparisDetay />
                </IzinKapisi>
              }
            />
            <Route
              path="kalite-kontrolleri"
              element={
                <IzinKapisi izin="kalite:oku" modul="kalite">
                  <KaliteKontrolListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="uygunsuzluklar"
              element={
                <IzinKapisi izin="kalite:oku" modul="kalite">
                  <UygunsuzlukListesi />
                </IzinKapisi>
              }
            />
            {/* S26-A: kontrol planı + SPC, ölçüm cihazı + kalibrasyon (ADR-0025). */}
            {(
              [
                ['kontrol-planlari', <KontrolPlanlari key="kp" />],
                ['kontrol-planlari/:id', <KontrolPlaniDetay key="kpd" />],
                ['karakteristikler/:id/spc', <SpcKarti key="spc" />],
                ['olcum-cihazlari', <OlcumCihazlari key="oc" />],
                ['olcum-cihazlari/:id', <OlcumCihaziDetay key="ocd" />],
              ] as const
            ).map(([yol, sayfa]) => (
              <Route
                key={yol}
                path={yol}
                element={
                  <IzinKapisi izin="kalite:oku" modul="kalite">
                    {sayfa}
                  </IzinKapisi>
                }
              />
            ))}
            <Route
              path="enerji-tuketimleri"
              element={
                <IzinKapisi izin="enerji:oku" modul="enerji">
                  <EnerjiTuketimListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="is-kazalari"
              element={
                <IzinKapisi izin="isg:oku" modul="isg">
                  <KazaListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="risk-degerlendirmeleri"
              element={
                <IzinKapisi izin="isg:oku" modul="isg">
                  <RiskListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="isg/egitimler"
              element={
                <IzinKapisi izin="isg:oku" modul="isg">
                  <IsgEgitimleri />
                </IzinKapisi>
              }
            />
            <Route
              path="isg/tatbikatlar"
              element={
                <IzinKapisi izin="isg:oku" modul="isg">
                  <Tatbikatlar />
                </IzinKapisi>
              }
            />
            <Route
              path="ik/org-semasi"
              element={
                <IzinKapisi izin="ik:oku" modul="ik">
                  <OrgSemasi />
                </IzinKapisi>
              }
            />
            <Route
              path="personeller"
              element={
                <IzinKapisi izin="ik:oku" modul="ik">
                  <PersonelListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="personeller/:id"
              element={
                <IzinKapisi izin="ik:oku" modul="ik">
                  <PersonelDetay />
                </IzinKapisi>
              }
            />
            <Route
              path="izin-talepleri"
              element={
                <IzinKapisi izin="ik:oku" modul="ik">
                  <IzinListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="ticari"
              element={
                <IzinKapisi izin="crm:oku" modul="crm">
                  <TicariPano />
                </IzinKapisi>
              }
            />
            <Route
              path="firmalar"
              element={
                <IzinKapisi izin="crm:oku" modul="crm">
                  <FirmaListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="sozlesmeler"
              element={
                <IzinKapisi izin="sozlesme:oku" modul="sozlesme">
                  <SozlesmeListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="talepler"
              element={
                <IzinKapisi izin="talep:oku" modul="talep">
                  <TalepListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="belgeler"
              element={
                <IzinKapisi izin="dys:oku" modul="dys">
                  <BelgeListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="duyurular"
              element={
                <IzinKapisi izin="duyuru:oku" modul="duyuru">
                  <DuyuruListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="bakim-planlari"
              element={
                <IzinKapisi izin="bakim:oku" modul="bakim">
                  <BakimPlanListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="tahminler"
              element={
                <IzinKapisi izin="ai:oku" modul="ai">
                  <TahminPanosu />
                </IzinKapisi>
              }
            />
            <Route
              path="analitik"
              element={
                <IzinKapisi izin="analitik:oku" modul="analitik">
                  <AnalitikPano />
                </IzinKapisi>
              }
            />
            <Route
              path="raporlar"
              element={
                <IzinKapisi izin="rapor:oku" modul="rapor">
                  <RaporListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="kullanicilar"
              element={
                <IzinKapisi izin="kullanici:oku">
                  <KullaniciListesi />
                </IzinKapisi>
              }
            />
            <Route
              path="abonelik"
              element={
                <IzinKapisi izin="abonelik:oku">
                  <AbonelikSayfasi />
                </IzinKapisi>
              }
            />
            <Route
              path="webhooklar"
              element={
                // Modül kapısı özel: `entegrasyon` modülü VEYA `webhook-onizleme` bayrağı
                // (backend `modul_veya_ozellik_gerekli` ile hizalı; S18/ADR-0020).
                <IzinKapisi izin="entegrasyon:oku">
                  <EntegrasyonKapisi>
                    <WebhookSayfasi />
                  </EntegrasyonKapisi>
                </IzinKapisi>
              }
            />
          </Route>
        </Route>

        {import.meta.env.DEV && (
          <Route path="/onizleme" element={<OnizlemeOturum />}>
            <Route element={<CanliKabuk />}>
              <Route index element={<OnizlemePano />} />
              <Route path="primitifler" element={<PrimitifVitrini />} />
            </Route>
          </Route>
        )}

        <Route path="*" element={<Navigate to="/pano" replace />} />
      </Routes>
    </Suspense>
  );
}
