/**
 * İş emri board görünümü — genelleştirilmiş ``KanbanPano`` + ``VeriKart`` üstünde ince kabuk.
 * Durum sütunları (akış: açık→atandı→devam→kapandı; iptal gösterilmez), kartlar tek çekimden
 * (useIsEmriPano) istemcide gruplanır. Kart aksiyonları durum makinesine uyar; kart tıkla → detay.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ToolOutlined, UserOutlined } from '@ant-design/icons';
import { Empty, Skeleton } from 'antd';

import { KanbanPano, type KanbanKolon } from '@/components/KanbanPano';
import { VeriKart } from '@/components/VeriKart';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { RENKLER } from '@/tema/tema';

import { KANBAN_DURUMLARI } from './durum';
import { DurumGecis } from './DurumGecis';
import { type IsEmri, useIsEmriPano } from './hooks';
import { OncelikRozet } from './rozetler';

/** Kolon başlığı durum rengi (nokta + etiket birlikte anlam taşır). */
const KOLON_RENK: Record<string, string> = {
  acik: RENKLER.metinSoluk,
  atandi: RENKLER.cyan,
  devam_ediyor: RENKLER.mavi,
  kapandi: RENKLER.basari,
};

export function IsEmriKanban({ ac }: { ac: (id: number) => void }) {
  const { t } = useTranslation();
  const { data, isPending, isError } = useIsEmriPano();
  const { data: makineler } = useMakineSecenekleri();
  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);

  if (isPending) return <Skeleton active paragraph={{ rows: 8 }} />;
  if (isError) return <Empty description={t('ortak.hata_baslik')} />;

  const kolonlar: KanbanKolon[] = KANBAN_DURUMLARI.map((d) => ({
    anahtar: d,
    baslik: t(`isemri.durum_${d}`),
    renk: KOLON_RENK[d] ?? RENKLER.metinSoluk,
  }));

  return (
    <KanbanPano<IsEmri>
      kolonlar={kolonlar}
      ogeler={data ?? []}
      kolonAnahtar={(e) => e.durum}
      kartAnahtar={(e) => e.id}
      bosMetin={t('tablo.bos')}
      kartCiz={(e) => (
        <VeriKart
          ustSol={e.kod}
          ustSag={<OncelikRozet oncelik={e.oncelik} />}
          baslik={e.baslik}
          meta={
            <>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                <ToolOutlined /> {makineHarita.get(e.makine_id)?.kod ?? `#${e.makine_id}`}
              </span>
              {e.atanan_kullanici_id != null && (
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
                  <UserOutlined /> #{e.atanan_kullanici_id}
                </span>
              )}
            </>
          }
          alt={<DurumGecis isEmri={e} />}
          onClick={() => ac(e.id)}
        />
      )}
    />
  );
}
