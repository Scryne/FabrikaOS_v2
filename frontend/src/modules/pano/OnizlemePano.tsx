/**
 * Pano önizlemesi (yalnız DEV) — backend olmadan tasarımı statik demo veriyle gösterir.
 * Aynı ``PanoIcerik`` sunum bileşenini besler (gerçek pano ile birebir görsel).
 */

import type { components } from '@/api/types.gen';

import { PanoIcerik, type PanoVerisi } from './PanoIcerik';

type Makine = components['schemas']['MakineCevapDTO'];
type UretimVerisi = components['schemas']['UretimVerisiCevapDTO'];

const MAKINELER: Makine[] = [
  { id: 1, kod: 'MAK-A1', ad: 'Pres Hattı', durum: 'calisiyor', oee_hedefi: 0.85 },
  { id: 2, kod: 'MAK-B2', ad: 'Enjeksiyon', durum: 'calisiyor', oee_hedefi: 0.8 },
  { id: 3, kod: 'MAK-C1', ad: 'CNC Freze', durum: 'durdu', oee_hedefi: 0.75 },
  { id: 4, kod: 'MAK-D3', ad: 'Montaj', durum: 'calisiyor', oee_hedefi: 0.9 },
  { id: 5, kod: 'MAK-E2', ad: 'Kaynak', durum: 'bakimda', oee_hedefi: 0.7 },
  { id: 6, kod: 'MAK-F1', ad: 'Boyama', durum: 'calisiyor', oee_hedefi: 0.82 },
];

function uretim(id: number, makine_id: number, vardiya: string, toplam: number): UretimVerisi {
  return {
    id,
    makine_id,
    zaman: new Date(Date.now() - id * 36e5).toISOString(),
    vardiya,
    planlanan_sure_dk: 480,
    durus_sure_dk: 42,
    toplam_adet: toplam,
    saglam_adet: Math.round(toplam * 0.97),
    ideal_cevrim_sn: 50,
  };
}

const DEMO: PanoVerisi = {
  filo: { oee: 84, kullanilabilirlik: 90, performans: 88, kalite: 96 },
  makineSayisi: 6,
  calisanSayisi: 4,
  izlenenSayisi: 5,
  durumlar: [
    { durum: 'calisiyor', adet: 4 },
    { durum: 'durdu', adet: 1 },
    { durum: 'bakimda', adet: 1 },
    { durum: 'ariza', adet: 0 },
  ],
  makineOee: [
    { ad: 'MAK-A1', oee: 87 },
    { ad: 'MAK-B2', oee: 79 },
    { ad: 'MAK-C1', oee: 64 },
    { ad: 'MAK-D3', oee: 91 },
    { ad: 'MAK-E2', oee: 72 },
  ],
  sonUretim: [
    uretim(1, 1, 'Gündüz', 1240),
    uretim(2, 2, 'Gündüz', 980),
    uretim(3, 4, 'Gündüz', 1520),
    uretim(4, 6, 'Gece', 430),
  ],
  makineHarita: new Map(MAKINELER.map((m) => [m.id, m])),
};

export function OnizlemePano() {
  return <PanoIcerik kullaniciAdi="Demo Yönetici" demo veri={DEMO} />;
}
