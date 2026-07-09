/**
 * Durum pimi — birleşik "nokta + etiket" göstergesi (renk körlüğü güvenli: renk tek başına
 * anlam taşımaz, nokta + metin birlikte). Modül durumları AntD ``Tag`` yerine bu tek dili
 * konuşur; ikiz/kiosk LED'leri de aynı sözlükten beslenir. Saf sunum: etiket çevrilmiş gelir.
 */

import type { CSSProperties, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

export function DurumPim({
  renk,
  etiket,
  solgun,
}: {
  /** Nokta rengi (hex ya da CSS değişkeni, ör. ``var(--basari)``). */
  renk: string;
  etiket: ReactNode;
  /** İkincil durumlar için etiketi sönükleştir. */
  solgun?: boolean;
}) {
  return (
    <span
      className={solgun ? 'durum-pim solgun' : 'durum-pim'}
      style={{ '--pim-renk': renk } as CSSProperties}
    >
      <span className="pim-nokta" aria-hidden="true" />
      {etiket}
    </span>
  );
}

/**
 * Bir ``durum → renk`` haritası + i18n anahtar önekinden ``durum`` alan bir pim bileşeni üretir.
 * Örn: ``const IsEmriPim = pimUret(RENK, 'isemri.durum_')`` → ``<IsEmriPim durum="acik" />``.
 * Bilinmeyen durum sönük gri + ham anahtar (i18n eksikse görünür kalır) ile gösterilir.
 */
// Fabrika fonksiyonu bileşen döndürür; react-refresh bunu bileşen-dışı export sanır (HMR uyarısı, hata değil).
// eslint-disable-next-line react-refresh/only-export-components
export function pimUret(renkler: Record<string, string>, anahtarOnek: string) {
  return function Pim({ durum, solgun }: { durum: string; solgun?: boolean }) {
    const { t } = useTranslation();
    return (
      <DurumPim
        renk={renkler[durum] ?? 'var(--metin-soluk)'}
        etiket={t(`${anahtarOnek}${durum}`)}
        solgun={solgun}
      />
    );
  };
}
