/** Tahsilat ve ödemeler — tür süzgeçli liste + yeni tahsilat / ödeme (ödeme ``finans:onay``). */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons';
import { Button, Card, Segmented, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { kolonlardanSutunlar } from '@/components/disaAktar';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { OdemeTurPim } from './FaturaPim';
import { type Odeme, paraBicim, useOdemeler } from './hooks';
import { OdemeFormu } from './OdemeFormu';

export function Odemeler() {
  const { t } = useTranslation();
  const yaz = useAuthStore((s) => s.izinVar('finans:yaz'));
  const onay = useAuthStore((s) => s.izinVar('finans:onay'));
  const [param, paramDegistir] = useSayfaParam();
  const [form, setForm] = useState<'tahsilat' | 'odeme' | null>(null);
  const { data, isPending, isError } = useOdemeler(param);

  const kolonlar: ColumnsType<Odeme> = [
    {
      title: t('finans.kod'),
      dataIndex: 'kod',
      key: 'kod',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('finans.odeme_turu'),
      dataIndex: 'tur',
      key: 'tur',
      render: (v: string) => <OdemeTurPim durum={v} />,
    },
    { title: t('finans.firma'), dataIndex: 'firma_ad', key: 'firma_ad' },
    {
      title: t('finans.bagli_fatura'),
      dataIndex: 'fatura_kod',
      key: 'fatura_kod',
      render: (v: string | null) => <span className="sayisal">{v ?? '—'}</span>,
    },
    {
      title: t('finans.tarih'),
      dataIndex: 'tarih',
      key: 'tarih',
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>,
    },
    {
      title: t('finans.yontem'),
      dataIndex: 'yontem',
      key: 'yontem',
      render: (v: string) => t(`finans.yontem_${v}`),
    },
    {
      title: t('finans.tutar'),
      dataIndex: 'tutar',
      key: 'tutar',
      align: 'right',
      render: (v: number) => <span className="sayisal">{paraBicim(v)}</span>,
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.odemeler')}
        alt={t('finans.odeme_alt')}
        sag={
          <Space wrap>
            {yaz && (
              <Button
                type="primary"
                icon={<ArrowDownOutlined />}
                onClick={() => setForm('tahsilat')}
              >
                {t('finans.yeni_tahsilat')}
              </Button>
            )}
            {onay && (
              <Button icon={<ArrowUpOutlined />} onClick={() => setForm('odeme')}>
                {t('finans.yeni_odeme')}
              </Button>
            )}
          </Space>
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Odeme>
          disaAktar={{
            yol: '/odemeler',
            dosya: 'odemeler',
            sutunlar: kolonlardanSutunlar(kolonlar),
          }}
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('finans.odeme_ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('finans.odeme_bos')}
          araclar={
            <Segmented
              value={(param.filtreler?.tur as string | undefined) ?? 'tum'}
              onChange={(v) =>
                paramDegistir({ filtreler: { tur: v === 'tum' ? undefined : String(v) } })
              }
              options={[
                { value: 'tum', label: t('finans.tumu') },
                { value: 'tahsilat', label: t('finans.tur_tahsilat') },
                { value: 'odeme', label: t('finans.tur_odeme') },
              ]}
            />
          }
        />
      </Card>
      <OdemeFormu
        acik={form != null}
        kapat={() => setForm(null)}
        varsayilanTur={form ?? 'tahsilat'}
      />
    </SayfaKapsayici>
  );
}
