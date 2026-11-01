/**
 * Liste ekranlarının detay çekmecesi için derin bağlantı (S27-A): ``?kayit=<id>`` çekmeceyi açık
 * başlatır; kapatınca parametre geçmişi kirletmeden (replace) URL'den silinir. Onay kutusu ve ⌘K
 * araması kayda bu yolla gider.
 */

import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

export function useDerinKayit(param = 'kayit') {
  const [arama, setArama] = useSearchParams();
  const [id, setId] = useState<number | null>(() => Number(arama.get(param)) || null);
  const kapat = () => {
    setId(null);
    if (arama.has(param))
      setArama(
        (p) => {
          p.delete(param);
          return p;
        },
        { replace: true },
      );
  };
  return [id, setId, kapat] as const;
}
