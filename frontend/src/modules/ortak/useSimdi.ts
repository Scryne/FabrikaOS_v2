/**
 * Render sırasında okunabilen "şimdi" (ms). `Date.now()` render içinde çağrılınca bileşen saf
 * olmaz (React derleyicisi / react-hooks `purity`): aynı girdiyle farklı çıktı verir ve ekran
 * yalnız başka bir sebeple yeniden çizilince ilerler. Bu kanca zamanı duruma alır ve
 * `aralikMs`'de bir tazeler; gecikme rozeti ve "şimdi" çizgisi kendiliğinden ilerler.
 */

import { useEffect, useState } from 'react';

export function useSimdi(aralikMs = 60_000): number {
  const [simdi, setSimdi] = useState(() => Date.now());
  useEffect(() => {
    const zamanlayici = setInterval(() => setSimdi(Date.now()), aralikMs);
    return () => clearInterval(zamanlayici);
  }, [aralikMs]);
  return simdi;
}
