/** Gerçek-zaman bağlantı durumu context'i (WS bağlı mı?) — canlı gösterge için. */

import { createContext, useContext } from 'react';

export type GercekZamanDurum = { bagli: boolean };

export const GercekZamanBaglam = createContext<GercekZamanDurum>({ bagli: false });

export function useGercekZaman(): GercekZamanDurum {
  return useContext(GercekZamanBaglam);
}
