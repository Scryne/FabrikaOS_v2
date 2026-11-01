/**
 * Cari hesaplar — firma bazında bakiye (pozitif: firma bize borçlu, negatif: biz borçluyuz),
 * açık fatura ve vadesi geçen alacak; satır → ekstre çekmecesi (açılış + yürüyen bakiye).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, Checkbox, Drawer, Empty, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { DetayIstatSira } from '@/components/DetayOgeleri';
import { kolonlardanSutunlar } from '@/components/disaAktar';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';

import { type CariEkstre, type CariHesap, paraBicim, useCariler, useEkstre } from './hooks';

type Hareket = CariEkstre['hareketler'][number];

function bakiyeRengi(b: number): string | undefined {
  if (b > 0) return 'var(--basari)';
  if (b < 0) return 'var(--uyari)';
  return undefined;
}

export function CariHesaplar() {
  const { t } = useTranslation();
  const [param, paramDegistir] = useSayfaParam();
  const [firmaId, setFirmaId] = useState<number | null>(null);
  const { data, isPending, isError } = useCariler(param);
  const ekstre = useEkstre(firmaId ?? 0);

  const kolonlar: ColumnsType<CariHesap> = [
    {
      title: t('finans.firma'),
      dataIndex: 'firma_ad',
      key: 'firma_ad',
      render: (v: string, c) => (
        <span>
          <span className="varlik-ad">{v}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {t(`crm.tip_${c.firma_tip}`, { defaultValue: c.firma_tip })}
          </span>
        </span>
      ),
    },
    {
      title: t('finans.bakiye'),
      dataIndex: 'bakiye',
      key: 'bakiye',
      align: 'right',
      render: (v: number, c) => (
        <span>
          <span className="sayisal" style={{ color: bakiyeRengi(v) }}>
            {paraBicim(Math.abs(v), c.para_birimi)}
          </span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {v > 0 ? t('finans.alacagimiz') : v < 0 ? t('finans.borcumuz') : t('finans.kapali')}
          </span>
        </span>
      ),
    },
    {
      title: t('finans.acik_fatura'),
      dataIndex: 'acik_fatura',
      key: 'acik_fatura',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('finans.vadesi_gecen'),
      dataIndex: 'vadesi_gecen',
      key: 'vadesi_gecen',
      align: 'right',
      render: (v: number, c) => (
        <span className="sayisal" style={{ color: v > 0 ? 'var(--hata-metin)' : undefined }}>
          {v > 0 ? paraBicim(v, c.para_birimi) : '—'}
        </span>
      ),
    },
    {
      title: t('finans.son_hareket'),
      dataIndex: 'son_hareket',
      key: 'son_hareket',
      render: (v: string | null) => (
        <span className="sayisal">{v ? dayjs(v).format('DD.MM.YYYY') : '—'}</span>
      ),
    },
  ];

  const hareketKolon: ColumnsType<Hareket> = [
    {
      title: t('finans.tarih'),
      dataIndex: 'tarih',
      key: 'tarih',
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>,
    },
    {
      title: t('finans.aciklama'),
      dataIndex: 'aciklama',
      key: 'aciklama',
      render: (v: string, h) => (
        <span>
          {v}
          <span className="varlik-alt" style={{ display: 'block' }}>
            {t(`finans.hareket_${h.tur}`)}
          </span>
        </span>
      ),
    },
    {
      title: t('finans.borc'),
      dataIndex: 'borc',
      key: 'borc',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v ? paraBicim(v) : ''}</span>,
    },
    {
      title: t('finans.alacak'),
      dataIndex: 'alacak',
      key: 'alacak',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v ? paraBicim(v) : ''}</span>,
    },
    {
      title: t('finans.bakiye'),
      dataIndex: 'bakiye_sonrasi',
      key: 'bakiye_sonrasi',
      align: 'right',
      render: (v: number) => (
        <span className="sayisal" style={{ color: bakiyeRengi(v) }}>
          {paraBicim(v)}
        </span>
      ),
    },
  ];

  const e = ekstre.data;
  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('menu.cari_hesaplar')} alt={t('finans.cari_alt')} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<CariHesap>
          disaAktar={{
            yol: '/cari-hesaplar',
            dosya: 'cari-hesaplar',
            sutunlar: kolonlardanSutunlar(kolonlar),
          }}
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="firma_id"
          aramaYer={t('finans.firma_ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('finans.cari_bos')}
          araclar={
            <Checkbox
              checked={param.filtreler?.bakiyeli === true}
              onChange={(ev) =>
                paramDegistir({ filtreler: { bakiyeli: ev.target.checked || undefined } })
              }
            >
              {t('finans.yalniz_bakiyeli')}
            </Checkbox>
          }
          onRow={(c) => ({ onClick: () => setFirmaId(c.firma_id), style: { cursor: 'pointer' } })}
        />
      </Card>

      <Drawer
        open={firmaId != null}
        onClose={() => setFirmaId(null)}
        width={760}
        title={e ? t('finans.ekstre_baslik', { firma: e.firma_ad }) : t('finans.ekstre')}
      >
        {e && (
          <>
            <DetayIstatSira
              ogeler={[
                {
                  anahtar: 'acilis',
                  etiket: t('finans.acilis'),
                  deger: paraBicim(e.acilis_bakiyesi),
                },
                {
                  anahtar: 'bakiye',
                  etiket: t('finans.guncel_bakiye'),
                  deger: paraBicim(e.bakiye),
                  ton: bakiyeRengi(e.bakiye),
                },
                {
                  anahtar: 'adet',
                  etiket: t('finans.hareket_sayisi'),
                  deger: String(e.hareketler.length),
                },
              ]}
            />
            <p className="varlik-alt">{t('finans.ekstre_aciklama')}</p>
            {e.hareketler.length === 0 ? (
              <Empty description={t('finans.ekstre_bos')} />
            ) : (
              <Table<Hareket>
                rowKey="id"
                size="small"
                columns={hareketKolon}
                dataSource={e.hareketler}
                pagination={{ pageSize: 25, hideOnSinglePage: true }}
                scroll={{ x: 600 }}
              />
            )}
          </>
        )}
      </Drawer>
    </SayfaKapsayici>
  );
}
