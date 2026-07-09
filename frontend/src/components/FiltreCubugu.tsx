/**
 * Filtre çubuğu — board/grid görünümlerinin üstünde tutarlı araç şeridi (kayıt sayacı + arama +
 * filtreler). Liste görünümünde bu iş ``SunucuTablo``'nun kendi araç çubuğunda yapılır; bu çubuk
 * tabloyu olmayan görünümlere (kanban, kart grid) aynı düzeni taşır.
 */

import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';

export function FiltreCubugu({
  sayac,
  arama,
  children,
}: {
  /** Toplam kayıt sayacı (opsiyonel). */
  sayac?: number;
  /** Arama girişi (opsiyonel). */
  arama?: ReactNode;
  /** Segmented / select filtreleri. */
  children?: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        flexWrap: 'wrap',
        marginBottom: 16,
      }}
    >
      {sayac != null && (
        <span className="kayit-sayaci">
          <strong className="sayisal">{sayac.toLocaleString('tr-TR')}</strong>
          {t('tablo.kayit')}
        </span>
      )}
      <div
        style={{
          marginLeft: 'auto',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          flexWrap: 'wrap',
        }}
      >
        {arama}
        {children}
      </div>
    </div>
  );
}
