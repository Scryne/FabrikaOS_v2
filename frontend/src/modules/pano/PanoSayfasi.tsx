/**
 * Pano (gerçek veri) — OEE özeti + makineler + son üretimden yönetici 360° görünümü hesaplar
 * ve ``PanoIcerik`` sunum bileşenine besler. Boş tenant'ta dostça boş durum gösterir.
 */

import { useMemo } from 'react';

import { useMakineSecenekleri, useOeeOzet, useUretimVerileri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';

import { PanoIcerik, type PanoVerisi } from './PanoIcerik';
import { durumDagilimi, filoOrtalamalari, makineOeeCubuklari } from './panoVeri';

export function PanoSayfasi() {
  const kullanici = useAuthStore((s) => s.kullanici);
  const ozetSorgu = useOeeOzet();
  const makineSorgu = useMakineSecenekleri();
  const uretimSorgu = useUretimVerileri({ sayfa: 1, adet: 6, siralama: 'zaman', yon: 'desc' });

  const ozetVeri = ozetSorgu.data;
  const makineVeri = makineSorgu.data;
  const sonUretimVeri = uretimSorgu.data?.veri;

  const veri: PanoVerisi = useMemo(() => {
    const ozet = ozetVeri ?? [];
    const makineler = makineVeri ?? [];
    return {
      filo: filoOrtalamalari(ozet),
      makineSayisi: makineler.length,
      calisanSayisi: makineler.filter((m) => m.durum === 'calisiyor').length,
      izlenenSayisi: ozet.length,
      durumlar: durumDagilimi(makineler),
      makineOee: makineOeeCubuklari(ozet),
      sonUretim: sonUretimVeri ?? [],
      makineHarita: new Map(makineler.map((m) => [m.id, m])),
    };
  }, [ozetVeri, makineVeri, sonUretimVeri]);

  return (
    <PanoIcerik
      kullaniciAdi={kullanici?.ad_soyad || kullanici?.eposta || ''}
      yukleniyor={ozetSorgu.isPending || makineSorgu.isPending}
      veri={veri}
    />
  );
}
