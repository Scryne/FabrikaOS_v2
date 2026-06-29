/** İş emri liste görünümü — sunucu-taraflı tablo (sıralama/arama) + durum filtresi. */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';

import { DURUMLAR } from './durum';
import { type IsEmri, useIsEmirleri } from './hooks';
import { DurumEtiketi, OncelikRozet } from './rozetler';

export function IsEmriListesi({ ac }: { ac: (id: number) => void }) {
  const { t } = useTranslation();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useIsEmirleri(param);
  const { data: makineler } = useMakineSecenekleri();
  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);

  const durumFiltre = (param.filtreler?.durum as string | undefined) ?? '';

  const kolonlar: ColumnsType<IsEmri> = [
    {
      title: t('isemri.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('isemri.baslik'), dataIndex: 'baslik', key: 'baslik', sorter: true },
    {
      title: t('isemri.makine'),
      dataIndex: 'makine_id',
      key: 'makine_id',
      render: (id: number) => makineHarita.get(id)?.kod ?? `#${id}`,
    },
    {
      title: t('isemri.oncelik'),
      dataIndex: 'oncelik',
      key: 'oncelik',
      sorter: true,
      render: (o: string) => <OncelikRozet oncelik={o} />,
    },
    {
      title: t('isemri.durum'),
      dataIndex: 'durum',
      key: 'durum',
      sorter: true,
      render: (d: string) => <DurumEtiketi durum={d} />,
    },
    {
      title: t('isemri.olusturma'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>,
    },
  ];

  const araclar = (
    <Select
      value={durumFiltre}
      onChange={(d) => paramDegistir({ filtreler: { durum: d || undefined } })}
      style={{ width: 170 }}
      options={[
        { value: '', label: t('ortak.tumu') },
        ...DURUMLAR.map((d) => ({ value: d, label: t(`isemri.durum_${d}`) })),
      ]}
    />
  );

  return (
    <SunucuTablo<IsEmri>
      kolonlar={kolonlar}
      veri={data?.veri ?? []}
      meta={data?.meta}
      yukleniyor={isPending}
      param={param}
      paramDegistir={paramDegistir}
      rowKey="id"
      aramaYer={t('isemri.ara')}
      araclar={araclar}
      bosMetin={isError ? t('ortak.hata_baslik') : t('tablo.bos')}
      onRow={(kayit) => ({ onClick: () => ac(kayit.id), style: { cursor: 'pointer' } })}
    />
  );
}
