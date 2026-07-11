/**
 * Ana pano (`/`) — persona/entitlement-farkındalıklı. Kullanıcının izin + açık modüllerine göre
 * görünür domain panellerini çözer ve ``PanoKompozit``e besler. Depo kullanıcısı yalnız stok
 * panellerini, kalite sorumlusu kalite panelini, yönetici tüm bento'yu görür — "her modül için
 * farklı pano". Panellerin her biri kendi ``/ozet`` verisini çeker (dar personada gereksiz çağrı yok).
 */

import { useMemo } from 'react';

import { useModulAcik } from '@/modules/abonelik/hooks';
import { useAuthStore } from '@/store/authStore';

import { PanoKompozit } from './PanoKompozit';
import { gorunurWidgetlar, personaAnahtari } from './personalar';

export function PanoSayfasi() {
  const kullanici = useAuthStore((s) => s.kullanici);
  const izinler = useAuthStore((s) => s.izinler);
  const modulAcik = useModulAcik();

  const widgetlar = useMemo(
    () => gorunurWidgetlar((izin) => izinler.has(izin), modulAcik),
    [izinler, modulAcik],
  );

  return (
    <PanoKompozit
      kullaniciAdi={kullanici?.ad_soyad || kullanici?.eposta || ''}
      personaAnahtari={personaAnahtari(widgetlar)}
      widgetlar={widgetlar}
    />
  );
}
