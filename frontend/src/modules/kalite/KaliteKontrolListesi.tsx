/**
 * Kalite kontrol listesi — sunucu-taraflı tablo (kod/tür/sonuç rozeti/numune) + "yeni kayıt"
 * (``kalite:yaz``) + sonuç filtresi. Denetim kayıtları salt-liste (satır detayı yok).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Select } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type KaliteKontrol, useKaliteKontroller } from './hooks';
import { KaliteKontrolFormu } from './KaliteKontrolFormu';
import { KontrolSonucEtiketi } from './rozetler';

const SONUCLAR = ['gecti', 'kaldi', 'sartli'];

export function KaliteKontrolListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useKaliteKontroller(param);
  const [formAcik, setFormAcik] = useState(false);

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
      render: (v: string) => <KontrolSonucEtiketi sonuc={v} />,
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
      render: (v: string) => <span className="sayisal">{new Date(v).toLocaleString()}</span>,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
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
    </div>
  );
}
