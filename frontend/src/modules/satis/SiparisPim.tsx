/** Satış siparişi durum pimi (nokta + etiket; renk tek başına anlam taşımaz). */

import { pimUret } from '@/components/DurumPim';
import { RENKLER } from '@/tema/tema';

const SIPARIS_DURUM_RENK: Record<string, string> = {
  taslak: RENKLER.metinSoluk,
  onaylandi: RENKLER.mavi,
  sevk_edildi: RENKLER.uyari,
  kapandi: RENKLER.basari,
  iptal: '#4b4b52',
};

export const SiparisPim = pimUret(SIPARIS_DURUM_RENK, 'satis.durum_');
