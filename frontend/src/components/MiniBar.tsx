/**
 * Satır-içi mini oran barı — ``deger``/``enBuyuk`` oranınca dolan ince bar. Renk semantiktir
 * (eşik geçişini çağıran ekran verir: OEE ≥85 yeşil / stok kritik altı kırmızı vb.). Tablolarda
 * "sayı + bar" birlikte okunur; bar tek başına değil (erişilebilirlik). Saf sunum.
 */

import type { CSSProperties } from 'react';

export function MiniBar({
  deger,
  enBuyuk = 100,
  renk = 'var(--mavi)',
  genislik = 72,
}: {
  deger: number;
  /** %100 karşılığı değer (varsayılan 100). */
  enBuyuk?: number;
  renk?: string;
  /** Bar piksel genişliği. */
  genislik?: number;
}) {
  const oran = enBuyuk > 0 ? Math.max(0, Math.min(1, deger / enBuyuk)) : 0;
  return (
    <div className="mini-bar" style={{ width: genislik }} aria-hidden="true">
      <div
        className="mini-bar-dolu"
        style={{ background: renk, transform: `scaleX(${oran})` } as CSSProperties}
      />
    </div>
  );
}
