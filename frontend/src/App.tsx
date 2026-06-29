/**
 * Rota ağacı + açılışta sessiz giriş (bootstrap).
 *
 * Mount'ta ``oturumBaslat`` saklı refresh ile sessiz giriş dener; tamamlanana dek tam ekran
 * yükleniyor gösterilir. Korunan rotalar oturum + (gerekiyorsa) izin kapılarından geçer.
 */

import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Spin } from 'antd';

import { oturumBaslat } from '@/api/kimlik';
import { LogoIsareti } from '@/components/Marka';
import { ModulYerTutucu } from '@/components/ModulYerTutucu';
import { UygulamaKabugu } from '@/layouts/UygulamaKabugu';
import { GirisSayfasi } from '@/modules/kimlik/GirisSayfasi';
import { PanoSayfasi } from '@/modules/pano/PanoSayfasi';
import { IzinKapisi, KorunanRota } from '@/routes/KorunanRota';

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
        <Route element={<UygulamaKabugu />}>
          <Route index element={<PanoSayfasi />} />
          <Route
            path="makineler"
            element={
              <IzinKapisi izin="uretim:oku">
                <ModulYerTutucu baslikAnahtari="menu.makineler" />
              </IzinKapisi>
            }
          />
          <Route
            path="is-emirleri"
            element={
              <IzinKapisi izin="isemri:oku">
                <ModulYerTutucu baslikAnahtari="menu.is_emirleri" />
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

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
