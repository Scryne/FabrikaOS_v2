/** Fatura ve ödeme durum/tür pimleri (nokta + etiket; renk tek başına anlam taşımaz). */

import { pimUret } from '@/components/DurumPim';
import { RENKLER } from '@/tema/tema';

const FATURA_DURUM_RENK: Record<string, string> = {
  taslak: RENKLER.metinSoluk,
  onay_bekliyor: RENKLER.mavi,
  kesildi: RENKLER.uyari,
  kapandi: RENKLER.basari,
  iptal: '#4b4b52',
};

export const FaturaPim = pimUret(FATURA_DURUM_RENK, 'finans.durum_');
export const OdemeTurPim = pimUret(
  { tahsilat: RENKLER.basari, odeme: RENKLER.uyari },
  'finans.tur_',
);
