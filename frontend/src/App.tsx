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
import { ModulYerTutucu } from '@/components/ModulYerTutucu';
import { UygulamaKabugu } from '@/layouts/UygulamaKabugu';
import { EnerjiTuketimListesi } from '@/modules/enerji/EnerjiTuketimListesi';
import { IsEmriEkrani } from '@/modules/isemri/IsEmriEkrani';
import { KaliteKontrolListesi } from '@/modules/kalite/KaliteKontrolListesi';
import { UygunsuzlukListesi } from '@/modules/kalite/UygunsuzlukListesi';
import { GirisSayfasi } from '@/modules/kimlik/GirisSayfasi';
import { GercekZamanSaglayici } from '@/modules/ortak/GercekZamanSaglayici';
import { OnizlemePano } from '@/modules/pano/OnizlemePano';
import { PanoSayfasi } from '@/modules/pano/PanoSayfasi';
import { CihazListesi } from '@/modules/saha/CihazListesi';
import { KritikStok } from '@/modules/stok/KritikStok';
import { MalzemeDetay } from '@/modules/stok/MalzemeDetay';
import { MalzemeListesi } from '@/modules/stok/MalzemeListesi';
import { SatinalmaTalepListesi } from '@/modules/stok/SatinalmaTalepListesi';
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
        'kullanici:oku',
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
      <Spin tip={t('ortak.yukleniyor')} />
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
            path="bakim-planlari"
            element={
              <IzinKapisi izin="bakim:oku">
                <ModulYerTutucu baslikAnahtari="menu.bakim" />
              </IzinKapisi>
            }
          />
          <Route
            path="kullanicilar"
            element={
              <IzinKapisi izin="kullanici:oku">
                <ModulYerTutucu baslikAnahtari="menu.kullanicilar" />
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
