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
import { IsEmriEkrani } from '@/modules/isemri/IsEmriEkrani';
import { GirisSayfasi } from '@/modules/kimlik/GirisSayfasi';
import { OnizlemePano } from '@/modules/pano/OnizlemePano';
import { PanoSayfasi } from '@/modules/pano/PanoSayfasi';
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
        'kullanici:oku',
      ],
    });
  }, [ayarlaOturum]);
  return <Outlet />;
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
        <Route element={<UygulamaKabugu />}>
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
          <Route element={<UygulamaKabugu />}>
            <Route index element={<OnizlemePano />} />
          </Route>
        </Route>
      )}

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
