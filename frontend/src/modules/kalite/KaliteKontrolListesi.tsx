/**
 * Kalite kontrol çalışma alanı — KPI şeridi (geçti oranı + toplam/geçen kontrol + açık
 * uygunsuzluk; `/kalite/ozet` yeniden kullanılır) + zengin tablo (sonuç pimi, tür, numune/uygunsuz,
 * zaman) + sonuç filtresi. Denetim kayıtları salt-liste.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  IssuesCloseOutlined,
  PercentageOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Button, Card, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { pimUret } from '@/components/DurumPim';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type KaliteKontrol, useKaliteKontroller, useKaliteOzet } from './hooks';
import { KaliteKontrolFormu } from './KaliteKontrolFormu';

const HAT = BOLUM_RENGI['menu.bolum_kalite'];
const SONUCLAR = ['gecti', 'kaldi', 'sartli'];

const SONUC_RENK: Record<string, string> = {
  gecti: RENKLER.basari,
  kaldi: RENKLER.hata,
  sartli: RENKLER.uyari,
};
const SonucPim = pimUret(SONUC_RENK, 'kalite.sonuc_');

export function KaliteKontrolListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useKaliteKontroller(param);
  const { data: ozet, isPending: ozetYukleniyor } = useKaliteOzet();
  const [formAcik, setFormAcik] = useState(false);

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'oran',
          baslik: t('kalite.kpi_gecti_orani'),
          deger: String(Math.round(ozet.gecti_orani * 100)),
          birim: '%',
          ikon: <PercentageOutlined />,
        },
        {
          anahtar: 'toplam',
          baslik: t('kalite.kpi_toplam_kontrol'),
          deger: String(ozet.toplam_kontrol),
          ikon: <SafetyCertificateOutlined />,
        },
        {
          anahtar: 'gecti',
          baslik: t('kalite.kpi_gecti'),
          deger: String(ozet.gecti_kontrol),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'uygunsuzluk',
          baslik: t('kalite.kpi_acik'),
          deger: String(ozet.acik_uygunsuzluk),
          ikon: <IssuesCloseOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<KaliteKontrol> = [
    {
      title: t('kalite.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('kalite.kontrol_turu'),
      dataIndex: 'kontrol_turu',
      key: 'kontrol_turu',
      render: (v: string) => t(`kalite.tur_${v}`),
    },
    {
      title: t('kalite.sonuc'),
      dataIndex: 'sonuc',
      key: 'sonuc',
      sorter: true,
      render: (v: string) => <SonucPim durum={v} />,
    },
    {
      title: t('kalite.numune_adedi'),
      dataIndex: 'numune_adedi',
      key: 'numune_adedi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('kalite.uygunsuz_adet'),
      dataIndex: 'uygunsuz_adet',
      key: 'uygunsuz_adet',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('kalite.zaman'),
      dataIndex: 'zaman',
      key: 'zaman',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY HH:mm')}</span>,
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.kalite')}
        alt={t('kalite.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('kalite.yeni')}
            </Button>
          )
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<KaliteKontrol>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('kalite.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('kalite.bos')}
          araclar={
            <Select
              allowClear
              placeholder={t('kalite.sonuc')}
              style={{ width: 160 }}
              value={param.filtreler?.sonuc as string | undefined}
              onChange={(v) => paramDegistir({ filtreler: { sonuc: v } })}
              options={SONUCLAR.map((x) => ({ value: x, label: t(`kalite.sonuc_${x}`) }))}
            />
          }
        />
      </Card>
      <KaliteKontrolFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
