/**
 * İzin talebi listesi — sunucu-taraflı tablo (kod/personel/tür/tarih/gün/durum) + satır → detay
 * çekmecesi (onay akışı) + "yeni" (``ik:yaz``) + durum filtresi.
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

import { type IzinTalebi, useIzinler } from './hooks';
import { IzinDetay } from './IzinDetay';
import { IzinFormu } from './IzinFormu';
import { IzinDurumEtiketi, IzinTuruEtiketi } from './rozetler';

const DURUMLAR = ['taslak', 'onay_bekliyor', 'onaylandi', 'reddedildi', 'iptal'];

export function IzinListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useIzinler(param);
  const [detayId, setDetayId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<IzinTalebi> = [
    {
      title: t('ik.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.personel'),
      dataIndex: 'personel_id',
      key: 'personel_id',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.izin_turu'),
      dataIndex: 'izin_turu',
      key: 'izin_turu',
      render: (v: string) => <IzinTuruEtiketi tur={v} />,
    },
    {
      title: t('ik.baslangic'),
      dataIndex: 'baslangic_tarihi',
      key: 'baslangic_tarihi',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.gun_sayisi'),
      dataIndex: 'gun_sayisi',
      key: 'gun_sayisi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string) => <IzinDurumEtiketi durum={v} />,
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.izin_talepleri')}
        alt={t('ik.izin_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('ik.izin_yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<IzinTalebi>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('ik.izin_ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('ik.izin_bos')}
          araclar={
            <Select
              allowClear
              placeholder={t('ik.durum')}
              style={{ width: 180 }}
              value={param.filtreler?.durum as string | undefined}
              onChange={(v) => paramDegistir({ filtreler: { durum: v } })}
              options={DURUMLAR.map((x) => ({ value: x, label: t(`ik.durum_${x}`) }))}
            />
          }
          onRow={(kayit) => ({
            onClick: () => setDetayId(kayit.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <IzinDetay id={detayId} kapat={() => setDetayId(null)} />
      <IzinFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
