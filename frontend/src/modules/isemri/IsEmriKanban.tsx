/**
 * İş emri kanban panosu — durum sütunları (akış: açık→atandı→devam→kapandı) + kartlar.
 *
 * Kartlar tek çekimden (useIsEmriPano) istemci tarafında gruplanır. Kart aksiyonları durum
 * makinesine uyar (yalnız geçerli geçişler). Karta tıklayınca detay çekmecesi açılır.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Empty, Skeleton } from 'antd';

import { ToolOutlined, UserOutlined } from '@ant-design/icons';

/** Kolon başlığı durum rengi (renk + etiket birlikte; renk tek başına anlam taşımaz). */
const KOLON_RENK: Record<string, string> = {
  acik: 'var(--metin-soluk)',
  atandi: 'var(--cyan)',
  devam_ediyor: 'var(--mavi)',
  kapandi: 'var(--basari)',
};

import { useMakineSecenekleri } from '@/modules/uretim/hooks';

import { KANBAN_DURUMLARI } from './durum';
import { DurumGecis } from './DurumGecis';
import { type IsEmri, useIsEmriPano } from './hooks';
import { OncelikRozet } from './rozetler';

function Kart({ e, makineKod, ac }: { e: IsEmri; makineKod: string; ac: (id: number) => void }) {
  return (
    <div
      role="button"
      tabIndex={0}
      className="kanban-kart"
      onClick={() => ac(e.id)}
      onKeyDown={(ev) => {
        if (ev.key === 'Enter') ac(e.id);
      }}
    >
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}
      >
        <span className="sayisal" style={{ fontSize: 12, color: 'var(--metin-soluk)' }}>
          {e.kod}
        </span>
        <OncelikRozet oncelik={e.oncelik} />
      </div>
      <div style={{ color: 'var(--metin)', fontWeight: 600, lineHeight: 1.35 }}>{e.baslik}</div>
      <div
        style={{
          display: 'flex',
          gap: 14,
          color: 'var(--metin-soluk)',
          fontSize: 12,
          flexWrap: 'wrap',
        }}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
          <ToolOutlined /> {makineKod}
        </span>
        {e.atanan_kullanici_id != null && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <UserOutlined />
          </span>
        )}
      </div>
      <DurumGecis isEmri={e} />
    </div>
  );
}

export function IsEmriKanban({ ac }: { ac: (id: number) => void }) {
  const { t } = useTranslation();
  const { data, isPending, isError } = useIsEmriPano();
  const { data: makineler } = useMakineSecenekleri();
  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);

  if (isPending) return <Skeleton active paragraph={{ rows: 8 }} />;
  if (isError) return <Empty description={t('ortak.hata_baslik')} />;

  const gruplar = new Map<string, IsEmri[]>(KANBAN_DURUMLARI.map((d) => [d, []]));
  for (const e of data ?? []) {
    gruplar.get(e.durum)?.push(e);
  }

  return (
    <div style={{ display: 'flex', gap: 16, overflowX: 'auto', paddingBottom: 8 }}>
      {KANBAN_DURUMLARI.map((durum) => {
        const ogeler = gruplar.get(durum) ?? [];
        return (
          <div
            key={durum}
            style={{
              flex: '1 0 280px',
              minWidth: 280,
              background: 'var(--yuzey-2)',
              border: '1px solid var(--kenarlik)',
              borderRadius: 14,
              padding: 12,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: 12,
                padding: '0 4px',
              }}
            >
              <span
                style={{
                  fontWeight: 600,
                  color: 'var(--metin)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span
                  className="durum-nokta"
                  aria-hidden="true"
                  style={{ background: KOLON_RENK[durum] ?? 'var(--metin-soluk)' }}
                />
                {t(`isemri.durum_${durum}`)}
              </span>
              <span
                className="sayisal"
                style={{
                  fontSize: 12,
                  color: 'var(--metin-soluk)',
                  background: 'var(--yuzey-ust)',
                  borderRadius: 8,
                  padding: '1px 8px',
                }}
              >
                {ogeler.length}
              </span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {ogeler.map((e) => (
                <Kart
                  key={e.id}
                  e={e}
                  makineKod={makineHarita.get(e.makine_id)?.kod ?? `#${e.makine_id}`}
                  ac={ac}
                />
              ))}
              {ogeler.length === 0 && (
                <div style={{ color: 'var(--metin-soluk)', fontSize: 12, padding: '8px 4px' }}>
                  {t('tablo.bos')}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
