/**
 * Satış siparişleri (S31, ADR-0050) — KPI şeridi + durum/gecikme süzgeçli sunucu tablosu + detay
 * çekmecesi (MRP, onay, tetiklenen iş emri ve talepler) + sipariş formu. ``?kayit=<id>`` derin
 * bağlantısı detayı doğrudan açar.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CarOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Card, Checkbox, Select, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { kolonlardanSutunlar } from '@/components/disaAktar';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { paraBicim } from '@/modules/finans/hooks';
import { useDerinKayit } from '@/modules/ortak/useDerinKayit';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { type Siparis, useSatisOzet, useSiparisler } from './hooks';
import { SiparisDetay } from './SiparisDetay';
import { SiparisFormu } from './SiparisFormu';
import { SiparisPim } from './SiparisPim';

const HAT = BOLUM_RENGI['menu.bolum_ticari'];
const DURUMLAR = ['taslak', 'onaylandi', 'sevk_edildi', 'kapandi', 'iptal'];

export function SatisSiparisListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('satis:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [detayId, setDetayId, detayKapat] = useDerinKayit();
  const [formAcik, setFormAcik] = useState(false);
  const { data, isPending, isError } = useSiparisler(param);
  const ozet = useSatisOzet();
  const filtre = param.filtreler ?? {};
  const filtreYaz = (yama: Record<string, string | number | boolean | undefined>) =>
    paramDegistir({ sayfa: 1, filtreler: { ...filtre, ...yama } });

  const kolonlar: ColumnsType<Siparis> = [
    {
      title: t('satis.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('satis.musteri'),
      dataIndex: 'firma_ad',
      key: 'firma_ad',
      render: (v: string | null, s) => (
        <span>
          <span className="varlik-ad">{v ?? '—'}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {s.kalemler.map((k) => k.urun_ad).join(', ')}
          </span>
        </span>
      ),
    },
    {
      title: t('satis.durum'),
      dataIndex: 'durum',
      key: 'durum',
      sorter: true,
      render: (d: string) => <SiparisPim durum={d} />,
    },
    {
      title: t('satis.teslim'),
      dataIndex: 'teslim_tarihi',
      key: 'teslim_tarihi',
      sorter: true,
      render: (v: string, s) => (
        <span className="sayisal" style={{ color: s.gecikti ? 'var(--hata-metin)' : undefined }}>
          {dayjs(v).format('DD.MM.YYYY')}
          {s.gecikti && <span className="varlik-alt"> · {t('satis.gecikti')}</span>}
        </span>
      ),
    },
    {
      title: t('satis.tutar'),
      dataIndex: 'tutar',
      key: 'tutar',
      align: 'right',
      render: (v: number | null, s) => (
        <span className="sayisal" style={{ opacity: v == null ? 0.5 : 1 }}>
          {v == null ? '—' : paraBicim(v, s.para_birimi)}
        </span>
      ),
    },
  ];

  const o = ozet.data;
  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.satis_siparisleri')}
        alt={t('satis.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('satis.yeni')}
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
                  anahtar: 'taslak',
                  baslik: t('satis.onay_bekleyen'),
                  deger: String(o.taslak),
                  ikon: <FileTextOutlined />,
                },
                {
                  anahtar: 'onaylandi',
                  baslik: t('satis.uretimde'),
                  deger: String(o.onaylandi),
                  ikon: <CheckCircleOutlined />,
                },
                {
                  anahtar: 'sevk',
                  baslik: t('satis.durum_sevk_edildi'),
                  deger: String(o.sevk_edildi),
                  ikon: <CarOutlined />,
                },
                {
                  anahtar: 'geciken',
                  baslik: t('satis.geciken'),
                  deger: String(o.geciken),
                  ikon: <ClockCircleOutlined />,
                  olumlu: o.geciken === 0,
                },
              ]
            : []
        }
      />
      <div style={{ height: 20 }} />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Siparis>
          disaAktar={{
            yol: '/satis-siparisleri',
            dosya: 'satis-siparisleri',
            sutunlar: kolonlardanSutunlar(kolonlar),
          }}
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('satis.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('satis.bos')}
          araclar={
            <Space wrap>
              <Select
                allowClear
                style={{ minWidth: 160 }}
                placeholder={t('satis.durum')}
                aria-label={t('satis.durum')}
                value={(filtre.durum as string | undefined) ?? undefined}
                onChange={(v?: string) => filtreYaz({ durum: v })}
                options={DURUMLAR.map((d) => ({ value: d, label: t(`satis.durum_${d}`) }))}
              />
              <Checkbox
                checked={filtre.geciken === true || filtre.geciken === 'true'}
                onChange={(e) => filtreYaz({ geciken: e.target.checked || undefined })}
              >
                {t('satis.yalniz_geciken')}
              </Checkbox>
            </Space>
          }
          onRow={(s) => ({ onClick: () => setDetayId(s.id), style: { cursor: 'pointer' } })}
        />
      </Card>
      <SiparisDetay id={detayId} kapat={detayKapat} />
      <SiparisFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
