/**
 * Faturalar — KPI şeridi + tür/durum/vade süzgeçli sunucu tablosu + detay çekmecesi + form.
 * ``?kayit=<id>`` derin bağlantısı (Onaylarım, arama, bildirim) detayı doğrudan açar.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useSearchParams } from 'react-router-dom';
import {
  ClockCircleOutlined,
  FallOutlined,
  FileSearchOutlined,
  PlusOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import { Button, Card, Checkbox, Segmented, Select, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { kolonlardanSutunlar } from '@/components/disaAktar';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useDerinKayit } from '@/modules/ortak/useDerinKayit';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { FaturaDetay } from './FaturaDetay';
import { FaturaFormu } from './FaturaFormu';
import { FaturaPim } from './FaturaPim';
import { type Fatura, paraBicim, paraKisa, useFaturalar, useFinansOzet } from './hooks';

const HAT = BOLUM_RENGI['menu.bolum_finans'];
const DURUMLAR = ['taslak', 'onay_bekliyor', 'kesildi', 'kapandi', 'iptal'];

export function FaturaListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('finans:yaz'));
  // ``?firma=<id>``: panodaki alacak tablosundan tek firmanın faturalarına iner.
  const [sorgu] = useSearchParams();
  const firmaParam = Number(sorgu.get('firma')) || undefined;
  const [param, paramDegistir] = useSayfaParam(
    firmaParam ? { filtreler: { firma_id: firmaParam } } : undefined,
  );
  const [detayId, setDetayId, detayKapat] = useDerinKayit();
  const [formAcik, setFormAcik] = useState(false);
  const { data, isPending, isError } = useFaturalar(param);
  const ozet = useFinansOzet();
  const filtre = param.filtreler ?? {};
  const filtreYaz = (yama: Record<string, string | number | boolean | undefined>) =>
    paramDegistir({ sayfa: 1, filtreler: { ...filtre, ...yama } });

  const kolonlar: ColumnsType<Fatura> = [
    {
      title: t('finans.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('finans.firma'),
      dataIndex: 'firma_ad',
      key: 'firma_ad',
      render: (v: string, f) => (
        <span>
          <span className="varlik-ad">{v}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {t(`finans.tur_${f.tur}`)}
          </span>
        </span>
      ),
    },
    {
      title: t('finans.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (d: string) => <FaturaPim durum={d} />,
    },
    {
      title: t('finans.fatura_tarihi'),
      dataIndex: 'fatura_tarihi',
      key: 'fatura_tarihi',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY')}</span>,
    },
    {
      title: t('finans.vade'),
      dataIndex: 'vade_tarihi',
      key: 'vade_tarihi',
      sorter: true,
      render: (v: string, f) => (
        <span
          className="sayisal"
          style={{ color: f.vadesi_gecti ? 'var(--hata-metin)' : undefined }}
        >
          {dayjs(v).format('DD.MM.YYYY')}
        </span>
      ),
    },
    {
      title: t('finans.genel_toplam'),
      dataIndex: 'genel_toplam',
      key: 'genel_toplam',
      align: 'right',
      sorter: true,
      render: (v: number, f) => <span className="sayisal">{paraBicim(v, f.para_birimi)}</span>,
    },
    {
      title: t('finans.acik'),
      dataIndex: 'acik_tutar',
      key: 'acik_tutar',
      align: 'right',
      render: (v: number, f) => (
        <span className="sayisal" style={{ opacity: v > 0 ? 1 : 0.5 }}>
          {paraBicim(v, f.para_birimi)}
        </span>
      ),
    },
  ];

  const o = ozet.data;
  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.faturalar')}
        alt={t('finans.fatura_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('finans.yeni_fatura')}
            </Button>
          )
        }
      />
      <OzetSerit
        renk={HAT}
        yukleniyor={ozet.isPending}
        metrikler={
          o
            ? [
                {
                  anahtar: 'alacak',
                  baslik: t('finans.acik_alacak'),
                  deger: paraKisa(o.acik_alacak),
                  ikon: <RiseOutlined />,
                },
                {
                  anahtar: 'borc',
                  baslik: t('finans.acik_borc'),
                  deger: paraKisa(o.acik_borc),
                  ikon: <FallOutlined />,
                },
                {
                  anahtar: 'vadesi',
                  baslik: t('finans.vadesi_gecen'),
                  deger: paraKisa(o.vadesi_gecen_alacak),
                  ikon: <ClockCircleOutlined />,
                  olumlu: o.vadesi_gecen_alacak === 0,
                },
                {
                  anahtar: 'onay',
                  baslik: t('finans.onay_bekleyen'),
                  deger: String(o.onay_bekleyen),
                  ikon: <FileSearchOutlined />,
                },
              ]
            : []
        }
      />
      <div style={{ height: 20 }} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Fatura>
          disaAktar={{
            yol: '/faturalar',
            dosya: 'faturalar',
            sutunlar: kolonlardanSutunlar(kolonlar),
          }}
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('finans.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('finans.bos')}
          araclar={
            <Space wrap>
              {filtre.firma_id != null && (
                <Tag closable onClose={() => filtreYaz({ firma_id: undefined })}>
                  {t('finans.firma_suzgeci')}:{' '}
                  {data?.veri[0]?.firma_ad ?? `#${String(filtre.firma_id)}`}
                </Tag>
              )}
              <Segmented
                value={(filtre.tur as string | undefined) ?? 'tum'}
                onChange={(v) => filtreYaz({ tur: v === 'tum' ? undefined : String(v) })}
                options={[
                  { value: 'tum', label: t('finans.tumu') },
                  { value: 'satis', label: t('finans.tur_satis') },
                  { value: 'alis', label: t('finans.tur_alis') },
                ]}
              />
              <Select
                allowClear
                style={{ minWidth: 150 }}
                placeholder={t('finans.durum')}
                aria-label={t('finans.durum')}
                value={(filtre.durum as string | undefined) ?? undefined}
                onChange={(v?: string) => filtreYaz({ durum: v })}
                options={DURUMLAR.map((d) => ({ value: d, label: t(`finans.durum_${d}`) }))}
              />
              <Checkbox
                checked={filtre.vadesi_gecmis === true || filtre.vadesi_gecmis === 'true'}
                onChange={(e) => filtreYaz({ vadesi_gecmis: e.target.checked || undefined })}
              >
                {t('finans.yalniz_vadesi_gecen')}
              </Checkbox>
            </Space>
          }
          onRow={(f) => ({ onClick: () => setDetayId(f.id), style: { cursor: 'pointer' } })}
        />
      </Card>
      <FaturaDetay id={detayId} kapat={detayKapat} />
      <FaturaFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
