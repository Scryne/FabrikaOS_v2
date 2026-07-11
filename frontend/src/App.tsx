/**
 * Rota ağacı + açılışta sessiz giriş (bootstrap).
 *
 * Mount'ta ``oturumBaslat`` saklı refresh ile sessiz giriş dener; tamamlanana dek tam ekran
 * yükleniyor gösterilir. Korunan rotalar oturum + (gerekiyorsa) izin kapılarından geçer.
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { Spin } from 'antd';

import { oturumBaslat } from '@/api/kimlik';
import { tenantSakla } from '@/api/tenant';
import { LogoIsareti } from '@/components/Marka';
import { UygulamaKabugu } from '@/layouts/UygulamaKabugu';
import { AbonelikSayfasi } from '@/modules/abonelik/AbonelikSayfasi';
import { TahminPanosu } from '@/modules/ai/TahminPanosu';
import { AnalitikPano } from '@/modules/analitik/AnalitikPano';
import { BakimPlanListesi } from '@/modules/bakim/BakimPlanListesi';
import { FirmaListesi } from '@/modules/crm/FirmaListesi';
import { DisPortalSayfasi } from '@/modules/dis/DisPortalSayfasi';
import { sadeceDisKullanici } from '@/modules/dis/hooks';
import { DuyuruListesi } from '@/modules/duyuru/DuyuruListesi';
import { EntegrasyonKapisi } from '@/modules/entegrasyon/EntegrasyonKapisi';
import { WebhookSayfasi } from '@/modules/entegrasyon/WebhookSayfasi';
import { BelgeListesi } from '@/modules/dys/BelgeListesi';
import { EnerjiTuketimListesi } from '@/modules/enerji/EnerjiTuketimListesi';
import { IzinListesi } from '@/modules/ik/IzinListesi';
import { PersonelDetay } from '@/modules/ik/PersonelDetay';
import { PersonelListesi } from '@/modules/ik/PersonelListesi';
import { KazaListesi } from '@/modules/isg/KazaListesi';
import { RiskListesi } from '@/modules/isg/RiskListesi';
import { IsEmriEkrani } from '@/modules/isemri/IsEmriEkrani';
import { KaliteKontrolListesi } from '@/modules/kalite/KaliteKontrolListesi';
import { UygunsuzlukListesi } from '@/modules/kalite/UygunsuzlukListesi';
import { IkizSayfasi } from '@/modules/ikiz/IkizSayfasi';
import { GirisSayfasi } from '@/modules/kimlik/GirisSayfasi';
import { KullaniciListesi } from '@/modules/kimlik/KullaniciListesi';
import { KioskSayfasi } from '@/modules/kiosk/KioskSayfasi';
import { PrimitifVitrini } from '@/modules/onizleme/PrimitifVitrini';
import { GercekZamanSaglayici } from '@/modules/ortak/GercekZamanSaglayici';
import { OnizlemePano } from '@/modules/pano/OnizlemePano';
import { RaporListesi } from '@/modules/rapor/RaporListesi';
import { PanoSayfasi } from '@/modules/pano/PanoSayfasi';
import { CihazListesi } from '@/modules/saha/CihazListesi';
import { SozlesmeListesi } from '@/modules/sozlesme/SozlesmeListesi';
import { TanitimSayfasi } from '@/modules/tanitim/TanitimSayfasi';
import { KritikStok } from '@/modules/stok/KritikStok';
import { MalzemeDetay } from '@/modules/stok/MalzemeDetay';
import { MalzemeListesi } from '@/modules/stok/MalzemeListesi';
import { SatinalmaTalepListesi } from '@/modules/stok/SatinalmaTalepListesi';
import { TalepListesi } from '@/modules/talep/TalepListesi';
import { TicariPano } from '@/modules/ticari/TicariPano';
import { MakineDetay } from '@/modules/uretim/MakineDetay';
import { MakineListesi } from '@/modules/uretim/MakineListesi';
import { UretimVerileri } from '@/modules/uretim/UretimVerileri';
import { AbonelikListesi as PlatformAbonelikListesi } from '@/platform/AbonelikListesi';
import { PlatformGiris } from '@/platform/PlatformGiris';
import { PlatformKabuk } from '@/platform/PlatformKabuk';
import { PlatformKorunanRota } from '@/platform/PlatformKorunanRota';
import { ProvizyonSihirbazi } from '@/platform/ProvizyonSihirbazi';
import { SaglikPano } from '@/platform/SaglikPano';
import { TenantDetay } from '@/platform/TenantDetay';
import { TenantListesi } from '@/platform/TenantListesi';
import { IzinKapisi, KorunanRota } from '@/routes/KorunanRota';
import { useAuthStore } from '@/store/authStore';

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
    <Routes>
      {/* Kök `/` = kurumsal tanıtım (public landing) — doğrudan açılır, oturum gerektirmez. */}
      <Route path="/" element={<TanitimSayfasi />} />
      <Route path="/giris" element={<GirisSayfasi />} />

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
            path="satinalma-talepleri"
            element={
              <IzinKapisi izin="satinalma:oku" modul="stok">
                <SatinalmaTalepListesi />
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
  );
}
