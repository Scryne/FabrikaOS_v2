/**
 * Üretim verileri — filo özeti (OEE KPI şeridi) + makine bazlı OEE çubukları + sunucu-taraflı
 * üretim kaydı tablosu (zaman/adet/duruş sıralanabilir, makine filtresi + sağlam oranı mini-bar).
 * Üretim verisi metin içermez; arama kutusu yoktur. ``uretim:yaz`` ile üretim girişi açılır.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  DashboardOutlined,
  EyeOutlined,
  PlusOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Button, Select, Skeleton, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { EGrafik } from '@/components/grafik/EGrafik';
import { cubukSecenek } from '@/components/grafik/grafikSecenek';
import { MiniBar } from '@/components/MiniBar';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { RENKLER } from '@/tema/tema';
import { useAuthStore } from '@/store/authStore';

import {
  type UretimVerisi,
  useMakineSecenekleri,
  useOeeOzet,
  useUretimOzet,
  useUretimVerileri,
} from './hooks';
import { UretimGirisFormu } from './UretimGirisFormu';

const HAT = RENKLER.cyan;

function sayi(v: number): string {
  return v.toLocaleString('tr-TR');
}

export function UretimVerileri() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));
  const [param, paramDegistir] = useSayfaParam({ siralama: 'zaman', yon: 'desc' });
  const { data, isPending, isError } = useUretimVerileri(param);
  const { data: makineler } = useMakineSecenekleri();
  const ozet = useUretimOzet();
  const oeeOzet = useOeeOzet();
  const [formAcik, setFormAcik] = useState(false);

  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);
  const makineFiltre = (param.filtreler?.makine_id as number | undefined) ?? undefined;

  const makineBar = useMemo(
    () =>
      cubukSecenek(
        (oeeOzet.data ?? [])
          .slice(0, 12)
          .map((s) => ({ ad: s.makine_kod, oee: Math.round(s.oee * 100) })),
      ),
    [oeeOzet.data],
  );

  const ozetMetrikler: OzetMetrik[] = [
    {
      anahtar: 'oee',
      baslik: t('pano.kpi_oee'),
      deger: `%${Math.round((ozet.data?.ortalama_oee ?? 0) * 100)}`,
      ikon: <DashboardOutlined />,
    },
    {
      anahtar: 'calisan',
      baslik: t('pano.kpi_calisan'),
      deger: `${ozet.data?.calisan ?? 0}/${ozet.data?.toplam_makine ?? 0}`,
      ikon: <ThunderboltOutlined />,
    },
    {
      anahtar: 'izlenen',
      baslik: t('pano.kpi_izlenen'),
      deger: String(ozet.data?.uretimli_makine ?? 0),
      ikon: <EyeOutlined />,
    },
    {
      anahtar: 'ariza',
      baslik: t('uretim.durum_ariza'),
      deger: String(ozet.data?.arizali ?? 0),
      ikon: <WarningOutlined />,
    },
  ];

  const kolonlar: ColumnsType<UretimVerisi> = [
    {
      title: t('uretim.zaman'),
      dataIndex: 'zaman',
      key: 'zaman',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM.YYYY HH:mm')}</span>,
    },
    {
      title: t('uretim.makine'),
      dataIndex: 'makine_id',
      key: 'makine_id',
      render: (id: number) => makineHarita.get(id)?.kod ?? `#${id}`,
    },
    { title: t('uretim.vardiya'), dataIndex: 'vardiya', key: 'vardiya', render: (v) => v ?? '—' },
    {
      title: t('uretim.toplam_adet'),
      dataIndex: 'toplam_adet',
      key: 'toplam_adet',
      align: 'right',
      sorter: true,
      render: (v: number) => <span className="sayisal">{sayi(v)}</span>,
    },
    {
      title: t('uretim.saglam_orani'),
      key: 'saglam_orani',
      width: 150,
      render: (_v, r) => {
        const oran = r.toplam_adet > 0 ? Math.round((r.saglam_adet / r.toplam_adet) * 100) : 0;
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="sayisal" style={{ minWidth: 38, color: 'var(--metin-soluk)' }}>
              %{oran}
            </span>
            <MiniBar
              deger={oran}
              renk={oran >= 97 ? 'var(--basari)' : oran >= 90 ? 'var(--uyari)' : 'var(--hata)'}
              genislik={64}
            />
          </div>
        );
      },
    },
    {
      title: t('uretim.durus_sure'),
      dataIndex: 'durus_sure_dk',
      key: 'durus_sure_dk',
      align: 'right',
      sorter: true,
      render: (v: number) => <span className="sayisal">{sayi(v)}</span>,
    },
  ];

  const araclar = (
    <Space wrap>
      <Select
        value={makineFiltre}
        onChange={(id) => paramDegistir({ filtreler: { makine_id: id ?? undefined } })}
        style={{ width: 220 }}
        allowClear
        showSearch
        optionFilterProp="label"
        placeholder={t('uretim.makine_filtre')}
        options={(makineler ?? []).map((m) => ({ value: m.id, label: `${m.kod} · ${m.ad}` }))}
      />
      {yazabilir && (
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
          {t('uretim.uretim_girisi')}
        </Button>
      )}
    </Space>
  );

  const makineVar = (oeeOzet.data?.length ?? 0) > 0;

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('uretim.uretim_verileri')} alt={t('uretim.uretim_alt')} />

      <div style={{ marginBottom: 16 }}>
        <OzetSerit metrikler={ozetMetrikler} renk={HAT} yukleniyor={ozet.isPending} />
      </div>

      {(makineVar || oeeOzet.isPending) && (
        <div style={{ marginBottom: 16 }}>
          <PanelKart baslik={t('pano.makine_oee')} renk={HAT}>
            {oeeOzet.isPending ? (
              <Skeleton active paragraph={{ rows: 4 }} />
            ) : (
              <EGrafik secenek={makineBar} yukseklik={220} />
            )}
          </PanelKart>
        </div>
      )}

      <PanelKart baslik={t('uretim.son_uretim')} renk={HAT}>
        <SunucuTablo<UretimVerisi>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          araclar={araclar}
          bosMetin={isError ? t('ortak.hata_baslik') : t('tablo.bos')}
        />
      </PanelKart>

      <UretimGirisFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
