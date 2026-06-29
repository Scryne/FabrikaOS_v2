/**
 * Liste ekranı sorgu parametresi durumu (sayfa/adet/sıralama/arama/filtre).
 *
 * ``guncelle`` kısmi yama uygular; arama/sıralama/filtre değişince (sayfa açıkça verilmediyse)
 * sayfayı 1'e döndürür — kullanıcı yeni filtrede boş sayfada kalmaz. Filtreler sığ birleştirilir.
 */

import { useCallback, useState } from 'react';

import { type SayfaParam, VARSAYILAN_SAYFA } from '@/api/sayfalama';

export function useSayfaParam(baslangic?: Partial<SayfaParam>) {
  const [param, setParam] = useState<SayfaParam>({ ...VARSAYILAN_SAYFA, ...baslangic });

  const guncelle = useCallback((yama: Partial<SayfaParam>) => {
    setParam((onceki) => {
      const sonraki: SayfaParam = { ...onceki, ...yama };
      if (yama.filtreler) {
        sonraki.filtreler = { ...onceki.filtreler, ...yama.filtreler };
      }
      const sayfaDisiDegisim =
        yama.arama !== undefined ||
        yama.siralama !== undefined ||
        yama.yon !== undefined ||
        yama.filtreler !== undefined;
      if (yama.sayfa === undefined && sayfaDisiDegisim) {
        sonraki.sayfa = 1;
      }
      return sonraki;
    });
  }, []);

  return [param, guncelle] as const;
}
