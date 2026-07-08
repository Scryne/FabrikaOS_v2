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
import { TahminPanosu } from '@/modules/ai/TahminPanosu';
import { AnalitikPano } from '@/modules/analitik/AnalitikPano';
import { BakimPlanListesi } from '@/modules/bakim/BakimPlanListesi';
import { FirmaListesi } from '@/modules/crm/FirmaListesi';
import { DuyuruListesi } from '@/modules/duyuru/DuyuruListesi';
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
import { GirisSayfasi } from '@/modules/kimlik/GirisSayfasi';
import { KullaniciListesi } from '@/modules/kimlik/KullaniciListesi';
import { GercekZamanSaglayici } from '@/modules/ortak/GercekZamanSaglayici';
import { OnizlemePano } from '@/modules/pano/OnizlemePano';
import { RaporListesi } from '@/modules/rapor/RaporListesi';
import { PanoSayfasi } from '@/modules/pano/PanoSayfasi';
import { CihazListesi } from '@/modules/saha/CihazListesi';
import { SozlesmeListesi } from '@/modules/sozlesme/SozlesmeListesi';
import { KritikStok } from '@/modules/stok/KritikStok';
import { MalzemeDetay } from '@/modules/stok/MalzemeDetay';
import { MalzemeListesi } from '@/modules/stok/MalzemeListesi';
import { SatinalmaTalepListesi } from '@/modules/stok/SatinalmaTalepListesi';
import { TalepListesi } from '@/modules/talep/TalepListesi';
import { TicariPano } from '@/modules/ticari/TicariPano';
import { MakineDetay } from '@/modules/uretim/MakineDetay';
import { MakineListesi } from '@/modules/uretim/MakineListesi';
import { UretimVerileri } from '@/modules/uretim/UretimVerileri';
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
      <Route path="/giris" element={<GirisSayfasi />} />

      <Route element={<KorunanRota />}>
        <Route element={<CanliKabuk />}>
          <Route index element={<PanoSayfasi />} />
          <Route
            path="makineler"
            element={
              <IzinKapisi izin="uretim:oku">
                <MakineListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="makineler/:id"
            element={
              <IzinKapisi izin="uretim:oku">
                <MakineDetay />
              </IzinKapisi>
            }
          />
          <Route
            path="uretim-verileri"
            element={
              <IzinKapisi izin="uretim:oku">
                <UretimVerileri />
              </IzinKapisi>
            }
          />
          <Route
            path="is-emirleri"
            element={
              <IzinKapisi izin="isemri:oku">
                <IsEmriEkrani />
              </IzinKapisi>
            }
          />
          <Route
            path="saha/cihazlar"
            element={
              <IzinKapisi izin="saha:oku">
                <CihazListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="malzemeler"
            element={
              <IzinKapisi izin="stok:oku">
                <MalzemeListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="malzemeler/:id"
            element={
              <IzinKapisi izin="stok:oku">
                <MalzemeDetay />
              </IzinKapisi>
            }
          />
          <Route
            path="stok/kritik"
            element={
              <IzinKapisi izin="stok:oku">
                <KritikStok />
              </IzinKapisi>
            }
          />
          <Route
            path="satinalma-talepleri"
            element={
              <IzinKapisi izin="satinalma:oku">
                <SatinalmaTalepListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="kalite-kontrolleri"
            element={
              <IzinKapisi izin="kalite:oku">
                <KaliteKontrolListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="uygunsuzluklar"
            element={
              <IzinKapisi izin="kalite:oku">
                <UygunsuzlukListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="enerji-tuketimleri"
            element={
              <IzinKapisi izin="enerji:oku">
                <EnerjiTuketimListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="is-kazalari"
            element={
              <IzinKapisi izin="isg:oku">
                <KazaListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="risk-degerlendirmeleri"
            element={
              <IzinKapisi izin="isg:oku">
                <RiskListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="personeller"
            element={
              <IzinKapisi izin="ik:oku">
                <PersonelListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="personeller/:id"
            element={
              <IzinKapisi izin="ik:oku">
                <PersonelDetay />
              </IzinKapisi>
            }
          />
          <Route
            path="izin-talepleri"
            element={
              <IzinKapisi izin="ik:oku">
                <IzinListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="ticari"
            element={
              <IzinKapisi izin="crm:oku">
                <TicariPano />
              </IzinKapisi>
            }
          />
          <Route
            path="firmalar"
            element={
              <IzinKapisi izin="crm:oku">
                <FirmaListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="sozlesmeler"
            element={
              <IzinKapisi izin="sozlesme:oku">
                <SozlesmeListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="talepler"
            element={
              <IzinKapisi izin="talep:oku">
                <TalepListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="belgeler"
            element={
              <IzinKapisi izin="dys:oku">
                <BelgeListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="duyurular"
            element={
              <IzinKapisi izin="duyuru:oku">
                <DuyuruListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="bakim-planlari"
            element={
              <IzinKapisi izin="bakim:oku">
                <BakimPlanListesi />
              </IzinKapisi>
            }
          />
          <Route
            path="tahminler"
            element={
              <IzinKapisi izin="ai:oku">
                <TahminPanosu />
              </IzinKapisi>
            }
          />
          <Route
            path="analitik"
            element={
              <IzinKapisi izin="analitik:oku">
                <AnalitikPano />
              </IzinKapisi>
            }
          />
          <Route
            path="raporlar"
            element={
              <IzinKapisi izin="rapor:oku">
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
        </Route>
      </Route>

      {import.meta.env.DEV && (
        <Route path="/onizleme" element={<OnizlemeOturum />}>
          <Route element={<CanliKabuk />}>
            <Route index element={<OnizlemePano />} />
          </Route>
        </Route>
      )}

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
