/**
 * Uyarı kartı — önem-renkli (bilgi/uyarı/kritik) hafif tint + eş-renk yumuşak kenar + renkli
 * ikon (AntD Alert token deseni). Kalite/İSG/bakım/stok panolarında kritik sinyalleri öne çıkarır.
 * Renk tek başına anlam taşımaz: ikon + başlık metni birlikte (erişilebilirlik).
 */

import type { CSSProperties, ReactNode } from 'react';
import { ExclamationCircleFilled, InfoCircleFilled, WarningFilled } from '@ant-design/icons';

export type Onem = 'bilgi' | 'uyari' | 'kritik';

const ONEM: Record<Onem, { renk: string; ikon: ReactNode }> = {
  bilgi: { renk: 'var(--cyan)', ikon: <InfoCircleFilled /> },
  uyari: { renk: 'var(--uyari)', ikon: <WarningFilled /> },
  kritik: { renk: 'var(--hata)', ikon: <ExclamationCircleFilled /> },
};

export function UyariKarti({
  onem = 'uyari',
  baslik,
  aciklama,
  aksiyon,
}: {
  onem?: Onem;
  baslik: ReactNode;
  aciklama?: ReactNode;
  /** Sağdaki aksiyon (ör. "Satınalma talebi" butonu). */
  aksiyon?: ReactNode;
}) {
  const { renk, ikon } = ONEM[onem];
  return (
    <div className="uyari-karti" style={{ '--onem-renk': renk } as CSSProperties}>
      <span className="uyari-ikon" aria-hidden="true">
        {ikon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ color: 'var(--metin)', fontWeight: 600 }}>{baslik}</div>
        {aciklama && (
          <div style={{ color: 'var(--metin-soluk)', fontSize: 13, marginTop: 2 }}>{aciklama}</div>
        )}
      </div>
      {aksiyon && <div style={{ flexShrink: 0 }}>{aksiyon}</div>}
    </div>
  );
}
