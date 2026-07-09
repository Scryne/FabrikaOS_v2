/**
 * Rapor listesi — sunucu-taraflı tablo (kod/tür/biçim/durum/boyut) + tür/durum filtresi +
 * yeni rapor + indirme. Üretim sürerken durum canlı tazelenir (yoklama + `rapor.hazir`).
 * Yazma ``rapor:yaz``.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DownloadOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Select, Tag, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { ApiHata } from '@/api/client';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { raporuIndir, useRaporlar } from './hooks';
import { RaporFormu } from './RaporFormu';
import { boyutMetni, DURUM_RENK, indirilebilir, type Rapor, RAPOR_TURLERI } from './sunum';

const DURUMLAR = ['kuyrukta', 'hazirlaniyor', 'hazir', 'basarisiz'] as const;

export function RaporListesi() {
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const yazabilir = useAuthStore((s) => s.izinVar('rapor:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useRaporlar(param);
  const [formAcik, setFormAcik] = useState(false);
  const [indirilen, setIndirilen] = useState<number | null>(null);

  const indir = async (kayit: Rapor) => {
    setIndirilen(kayit.id);
    try {
      await raporuIndir(kayit.id, kayit.dosya_adi);
    } catch (hata) {
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
    } finally {
      setIndirilen(null);
    }
  };

  const kolonlar: ColumnsType<Rapor> = [
    {
      title: t('rapor.kod'),
      dataIndex: 'kod',
      key: 'kod',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('rapor.tur'),
      dataIndex: 'tur',
      key: 'tur',
      render: (v: string) => t(`rapor.tur_${v}`),
    },
    {
      title: t('rapor.bicim'),
      dataIndex: 'bicim',
      key: 'bicim',
      render: (v: string) => <Tag bordered={false}>{v.toUpperCase()}</Tag>,
    },
    {
      title: t('rapor.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string, kayit) => {
        const rozet = (
          <Tag color={DURUM_RENK[v] ?? 'default'} bordered={false}>
            {t(`rapor.durum_${v}`)}
          </Tag>
        );
        return v === 'basarisiz' && kayit.hata ? (
          <Tooltip title={kayit.hata}>{rozet}</Tooltip>
        ) : (
          rozet
        );
      },
    },
    {
      title: t('rapor.satir'),
      dataIndex: 'satir_sayisi',
      key: 'satir_sayisi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('rapor.boyut'),
      dataIndex: 'boyut',
      key: 'boyut',
      align: 'right',
      render: (v: number) => <span className="sayisal">{boyutMetni(v)}</span>,
    },
    {
      title: t('rapor.olusturma'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      render: (v: string) =>
        new Intl.DateTimeFormat(i18n.language, {
          dateStyle: 'medium',
          timeStyle: 'short',
        }).format(new Date(v)),
    },
    {
      title: '',
      key: 'aksiyon',
      align: 'right',
      render: (_v, kayit) => (
        <Button
          size="small"
          icon={<DownloadOutlined />}
          disabled={!indirilebilir(kayit.durum)}
          loading={indirilen === kayit.id}
          onClick={() => void indir(kayit)}
        >
          {t('rapor.indir')}
        </Button>
      ),
    },
  ];

  const filtre = (anahtar: 'tur' | 'durum', secenekler: readonly string[], onek: string) => (
    <Select
      allowClear
      placeholder={t(`rapor.${anahtar}`)}
      style={{ minWidth: 150 }}
      value={(param.filtreler?.[anahtar] as string | undefined) ?? undefined}
      onChange={(v?: string) =>
        paramDegistir({ sayfa: 1, filtreler: { ...param.filtreler, [anahtar]: v } })
      }
      options={secenekler.map((s) => ({ value: s, label: t(`rapor.${onek}_${s}`) }))}
    />
  );

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.raporlar')}
        alt={t('rapor.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('rapor.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Rapor>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          araclar={
            <>
              {filtre('tur', RAPOR_TURLERI, 'tur')}
              {filtre('durum', DURUMLAR, 'durum')}
            </>
          }
          bosMetin={isError ? t('ortak.hata_baslik') : t('rapor.bos')}
        />
      </Card>
      <RaporFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
