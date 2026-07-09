/**
 * Makineler çalışma alanı — KPI şeridi (üretim özeti) + Liste/Analiz görünüm geçişi.
 * Liste: varlık hücresi (ikon + ad + kod) · durum pimi · OEE mini-bar (eşik renkli) · hedef · ⋯
 * (detay / ikizde göster / durum değiştir). Analiz: durum donut'u + makine bazlı OEE çubukları.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  LineChartOutlined,
  MoreOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  RobotOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Button, Card, Col, Dropdown, Row, Select, Space } from 'antd';
import type { CSSProperties } from 'react';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';

import { DurumRozet, MAKINE_DURUMLARI } from '@/components/DurumRozet';
import { EGrafik } from '@/components/grafik/EGrafik';
import { cubukSecenek, donutSecenek, oeeRenk } from '@/components/grafik/grafikSecenek';
import { GorunumGecis, type Gorunum } from '@/components/GorunumGecis';
import { MiniBar } from '@/components/MiniBar';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { makineOeeCubuklari } from '@/modules/pano/panoVeri';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import {
  type Makine,
  useMakineDurumGuncelle,
  useMakineler,
  useOeeOzet,
  useUretimOzet,
} from './hooks';
import { MakineFormu } from './MakineFormu';

const HAT = BOLUM_RENGI['menu.bolum_uretim'];

const DURUM_RENK: Record<string, string> = {
  calisiyor: RENKLER.basari,
  durdu: RENKLER.metinSoluk,
  bakimda: RENKLER.uyari,
  ariza: RENKLER.hata,
};

export function MakineListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [formAcik, setFormAcik] = useState(false);

  const { data, isPending, isError } = useMakineler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useUretimOzet();
  const { data: oeeOzet } = useOeeOzet();
  const durumGuncelle = useMakineDurumGuncelle();

  const oeeHarita = useMemo(
    () => new Map((oeeOzet ?? []).map((s) => [s.makine_id, s.oee])),
    [oeeOzet],
  );

  const durumFiltre = (param.filtreler?.durum as string | undefined) ?? '';

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'toplam',
          baslik: t('uretim.kpi_toplam'),
          deger: String(ozet.toplam_makine),
          ikon: <RobotOutlined />,
        },
        {
          anahtar: 'calisan',
          baslik: t('uretim.kpi_calisan'),
          deger: String(ozet.calisan),
          ikon: <PlayCircleOutlined />,
        },
        {
          anahtar: 'sorunlu',
          baslik: t('uretim.kpi_sorunlu'),
          deger: String(ozet.arizali + ozet.bakimda),
          altMetin: t('uretim.arizali_n', { n: ozet.arizali }),
          ikon: <WarningOutlined />,
        },
        {
          anahtar: 'oee',
          baslik: t('uretim.kpi_oee'),
          deger: String(Math.round(ozet.ortalama_oee * 100)),
          birim: '%',
          ikon: <LineChartOutlined />,
        },
      ]
    : [];

  const aksiyonMenu = (m: Makine): MenuProps['items'] => {
    const items: MenuProps['items'] = [
      { key: 'detay', label: t('uretim.detay'), onClick: () => navigate(`/makineler/${m.id}`) },
      { key: 'ikiz', label: t('uretim.ikizde_goster'), onClick: () => navigate('/ikiz') },
    ];
    if (yazabilir) {
      items.push({
        key: 'durum',
        label: t('uretim.durum_degistir'),
        children: MAKINE_DURUMLARI.map((d) => ({
          key: d,
          label: t(`uretim.durum_${d}`),
          disabled: d === m.durum,
          onClick: () => durumGuncelle.mutate({ id: m.id, durum: d }),
        })),
      });
    }
    return items;
  };

  const kolonlar: ColumnsType<Makine> = [
    {
      title: t('uretim.ad'),
      key: 'ad',
      sorter: true,
      render: (_v: unknown, m: Makine) => (
        <span className="varlik-hucre">
          <span
            className="ikon-plaka kucuk"
            aria-hidden="true"
            style={{ '--plaka-renk': HAT } as CSSProperties}
          >
            <RobotOutlined />
          </span>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {m.ad}
            </span>
            <span className="varlik-alt sayisal">{m.kod}</span>
          </span>
        </span>
      ),
    },
    {
      title: t('uretim.durum'),
      dataIndex: 'durum',
      key: 'durum',
      sorter: true,
      render: (d: string) => <DurumRozet durum={d} />,
    },
    {
      title: t('uretim.oee_skoru'),
      key: 'oee',
      render: (_v: unknown, m: Makine) => {
        const oee = oeeHarita.get(m.id);
        if (oee == null) {
          return <span style={{ color: 'var(--metin-soluk)' }}>{t('uretim.veri_yok')}</span>;
        }
        const yuzde = Math.round(oee * 100);
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <MiniBar deger={yuzde} renk={oeeRenk(yuzde)} />
            <span className="sayisal" style={{ width: 42 }}>
              %{yuzde}
            </span>
          </span>
        );
      },
    },
    {
      title: t('uretim.oee_hedefi'),
      dataIndex: 'oee_hedefi',
      key: 'oee_hedefi',
      align: 'right',
      render: (v: number | null) =>
        v != null ? (
          <span className="sayisal">%{Math.round(v * 100)}</span>
        ) : (
          <span style={{ color: 'var(--metin-soluk)' }}>{t('uretim.veri_yok')}</span>
        ),
    },
    {
      title: '',
      key: 'aksiyon',
      width: 48,
      render: (_v: unknown, m: Makine) => (
        <div
          role="presentation"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <Dropdown menu={{ items: aksiyonMenu(m) }} trigger={['click']}>
            <button
              type="button"
              className="bar-dugme"
              aria-label={t('uretim.durum_degistir')}
              style={{ width: 32, height: 32, fontSize: 16 }}
            >
              <MoreOutlined />
            </button>
          </Dropdown>
        </div>
      ),
    },
  ];

  const araclar = (
    <Space wrap>
      <Select
        value={durumFiltre}
        onChange={(d) => paramDegistir({ filtreler: { durum: d || undefined } })}
        style={{ width: 160 }}
        options={[
          { value: '', label: t('ortak.tumu') },
          ...MAKINE_DURUMLARI.map((d) => ({ value: d, label: t(`uretim.durum_${d}`) })),
        ]}
      />
    </Space>
  );

  const donutVeri = (ozet?.durum_dagilimi ?? [])
    .filter((d) => d.adet > 0)
    .map((d) => ({
      ad: t(`uretim.durum_${d.durum}`),
      deger: d.adet,
      renk: DURUM_RENK[d.durum] ?? RENKLER.metinSoluk,
    }));
  const oeeCubuklar = makineOeeCubuklari(oeeOzet ?? []);

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.makineler')}
        alt={t('uretim.makine_alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} secenekler={['liste', 'analiz']} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('uretim.makine_ekle')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<Makine>
            kolonlar={kolonlar}
            veri={data?.veri ?? []}
            meta={data?.meta}
            yukleniyor={isPending}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            aramaYer={t('uretim.makine_ara')}
            araclar={araclar}
            bosMetin={isError ? t('ortak.hata_baslik') : t('tablo.bos')}
            onRow={(kayit) => ({
              onClick: () => navigate(`/makineler/${kayit.id}`),
              style: { cursor: 'pointer' },
            })}
          />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={10}>
            <PanelKart baslik={t('uretim.analiz_durum')} renk={HAT}>
              <EGrafik secenek={donutSecenek(donutVeri)} yukseklik={300} />
            </PanelKart>
          </Col>
          <Col xs={24} lg={14}>
            <PanelKart baslik={t('uretim.analiz_oee')} renk={HAT}>
              <EGrafik secenek={cubukSecenek(oeeCubuklar)} yukseklik={300} />
            </PanelKart>
          </Col>
        </Row>
      )}

      <MakineFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
