/**
 * Makine durum rozeti — renk + nokta + etiket. Renk tek başına anlam taşımaz (renk körlüğü
 * için nokta + metin birlikte). Etiket i18n'den gelir; bilinmeyen durum ham gösterilir.
 */

import { useTranslation } from 'react-i18next';

import { RENKLER } from '@/tema/tema';

export const MAKINE_DURUMLARI = ['calisiyor', 'durdu', 'bakimda', 'ariza'] as const;
export type MakineDurum = (typeof MAKINE_DURUMLARI)[number];

const RENK: Record<string, string> = {
  calisiyor: RENKLER.basari,
  durdu: RENKLER.metinSoluk,
  bakimda: RENKLER.uyari,
  ariza: RENKLER.hata,
};

export function DurumRozet({ durum }: { durum: string }) {
  const { t } = useTranslation();
  const renk = RENK[durum] ?? RENKLER.metinSoluk;
  const etiket = MAKINE_DURUMLARI.includes(durum as MakineDurum)
    ? t(`uretim.durum_${durum}`)
    : durum;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8, whiteSpace: 'nowrap' }}>
      <span
        aria-hidden="true"
        style={{ width: 8, height: 8, borderRadius: '50%', background: renk, flexShrink: 0 }}
      />
      <span style={{ color: 'var(--metin)' }}>{etiket}</span>
    </span>
  );
}
