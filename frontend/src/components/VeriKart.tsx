/**
 * Board/grid varlık kartı — üst satır (kod + durum/öncelik pimi) + başlık + meta çipleri + alt
 * (footer: durum geçiş butonları / yaş). Kanban kartları ve belge grid'i bu kartı kullanır.
 * ``onClick`` varsa tümüyle tıklanabilir + klavye erişilebilir (Enter). ``.kanban-kart`` deseni.
 */

import type { KeyboardEvent, ReactNode } from 'react';

export function VeriKart({
  ustSol,
  ustSag,
  baslik,
  meta,
  alt,
  onClick,
}: {
  /** Üst satır sol (ör. kod — mono). */
  ustSol?: ReactNode;
  /** Üst satır sağ (ör. öncelik/durum pimi). */
  ustSag?: ReactNode;
  baslik: ReactNode;
  /** Meta çipleri satırı (ör. makine, atanan, yaş). */
  meta?: ReactNode;
  /** Alt/footer (ör. durum geçiş butonları). */
  alt?: ReactNode;
  onClick?: () => void;
}) {
  const tiklanabilir = Boolean(onClick);
  return (
    <div
      className="kanban-kart"
      role={tiklanabilir ? 'button' : undefined}
      tabIndex={tiklanabilir ? 0 : undefined}
      onClick={onClick}
      onKeyDown={
        tiklanabilir
          ? (e: KeyboardEvent) => {
              if (e.key === 'Enter') onClick?.();
            }
          : undefined
      }
      style={tiklanabilir ? undefined : { cursor: 'default' }}
    >
      {(ustSol || ustSag) && (
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <span className="sayisal" style={{ fontSize: 12, color: 'var(--metin-soluk)' }}>
            {ustSol}
          </span>
          {ustSag}
        </div>
      )}
      <div style={{ color: 'var(--metin)', fontWeight: 600, lineHeight: 1.35 }}>{baslik}</div>
      {meta && (
        <div
          style={{
            display: 'flex',
            gap: 14,
            color: 'var(--metin-soluk)',
            fontSize: 12,
            flexWrap: 'wrap',
          }}
        >
          {meta}
        </div>
      )}
      {alt}
    </div>
  );
}
