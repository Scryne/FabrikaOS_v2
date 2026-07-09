/**
 * Malzemeler çalışma alanı — KPI şeridi (stok özeti) + Liste/Analiz. Liste: malzeme varlık
 * hücresi (kod + ad + birim) · bakiye (mono) · stok seviye mini-bar'ı (bakiye vs min/kritik
 * eşikleri, semantik renk) · seviye pimi · ⋯ (detay / hareket ekle). Analiz: stok seviye donut'u.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  AlertOutlined,
  GoldOutlined,
  MoreOutlined,
  PlusOutlined,
  SwapOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Button, Card, Col, Dropdown, Row, Space } from 'antd';
import type { CSSProperties } from 'react';
import type { ColumnsType } from 'antd/es/table';
import type { MenuProps } from 'antd';

import { DurumPim } from '@/components/DurumPim';
import { EGrafik } from '@/components/grafik/EGrafik';
import { donutSecenek } from '@/components/grafik/grafikSecenek';
import { GorunumGecis, type Gorunum } from '@/components/GorunumGecis';
import { MiniBar } from '@/components/MiniBar';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type Malzeme, useMalzemeler, useStokOzet } from './hooks';
import { MalzemeFormu } from './MalzemeFormu';
import { StokHareketFormu } from './StokHareketFormu';

const HAT = BOLUM_RENGI['menu.bolum_stok'];

/** Malzemenin stok seviyesi (renk + etiket): kritik altı / min altı / normal. */
function seviye(m: Malzeme): { renk: string; etiket: string } {
  if (m.kritik) return { renk: RENKLER.hata, etiket: 'kritik' };
  if (m.min_stok > 0 && m.mevcut_miktar <= m.min_stok)
    return { renk: RENKLER.uyari, etiket: 'min' };
  return { renk: RENKLER.basari, etiket: 'normal' };
}

export function MalzemeListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('stok:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [formAcik, setFormAcik] = useState(false);
  const [hareketMalzeme, setHareketMalzeme] = useState<Malzeme | null>(null);

  const { data, isPending, isError } = useMalzemeler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useStokOzet();

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'toplam',
          baslik: t('stok.kpi_toplam'),
          deger: String(ozet.toplam_malzeme),
          ikon: <GoldOutlined />,
        },
        {
          anahtar: 'kritik',
          baslik: t('stok.kpi_kritik'),
          deger: String(ozet.kritik_alti),
          ikon: <AlertOutlined />,
        },
        {
          anahtar: 'min',
          baslik: t('stok.kpi_min'),
          deger: String(ozet.min_alti),
          ikon: <WarningOutlined />,
        },
        {
          anahtar: 'hareket',
          baslik: t('stok.kpi_hareket'),
          deger: String(ozet.bugun_hareket),
          ikon: <SwapOutlined />,
        },
      ]
    : [];

  const aksiyonMenu = (m: Malzeme): MenuProps['items'] => {
    const items: MenuProps['items'] = [
      { key: 'detay', label: t('stok.detay'), onClick: () => navigate(`/malzemeler/${m.id}`) },
    ];
    if (yazabilir) {
      items.push({
        key: 'hareket',
        label: t('stok.hareket_ekle'),
        onClick: () => setHareketMalzeme(m),
      });
    }
    return items;
  };

  const kolonlar: ColumnsType<Malzeme> = [
    {
      title: t('stok.ad'),
      key: 'kod',
      sorter: true,
      render: (_v: unknown, m: Malzeme) => (
        <span className="varlik-hucre">
          <span
            className="ikon-plaka kucuk"
            aria-hidden="true"
            style={{ '--plaka-renk': HAT } as CSSProperties}
          >
            <GoldOutlined />
          </span>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {m.ad}
            </span>
            <span className="varlik-alt sayisal">
              {m.kod} · {m.birim}
            </span>
          </span>
        </span>
      ),
    },
    {
      title: t('stok.mevcut'),
      dataIndex: 'mevcut_miktar',
      key: 'mevcut_miktar',
      sorter: true,
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('stok.seviye'),
      key: 'seviye',
      render: (_v: unknown, m: Malzeme) => {
        const s = seviye(m);
        const ref = m.max_stok ?? Math.max(m.min_stok * 2, m.kritik_stok * 2, m.mevcut_miktar, 1);
        return (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
            <MiniBar deger={m.mevcut_miktar} enBuyuk={ref} renk={s.renk} />
            <DurumPim renk={s.renk} etiket={t(`stok.seviye_${s.etiket}`)} />
          </span>
        );
      },
    },
    {
      title: t('stok.kritik_esik'),
      dataIndex: 'kritik_stok',
      key: 'kritik_stok',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('stok.durum'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (aktif: boolean) => (
        <DurumPim
          renk={aktif ? RENKLER.basari : RENKLER.metinSoluk}
          etiket={aktif ? t('stok.aktif') : t('stok.pasif')}
          solgun={!aktif}
        />
      ),
    },
    {
      title: '',
      key: 'aksiyon',
      width: 48,
      render: (_v: unknown, m: Malzeme) => (
        <div
          role="presentation"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <Dropdown menu={{ items: aksiyonMenu(m) }} trigger={['click']}>
            <button
              type="button"
              className="bar-dugme"
              aria-label={t('stok.detay')}
              style={{ width: 32, height: 32, fontSize: 16 }}
            >
              <MoreOutlined />
            </button>
          </Dropdown>
        </div>
      ),
    },
  ];

  const kritik = ozet?.kritik_alti ?? 0;
  const minAlti = ozet?.min_alti ?? 0;
  const toplam = ozet?.toplam_malzeme ?? 0;
  const donutVeri = [
    { ad: t('stok.seviye_kritik'), deger: kritik, renk: RENKLER.hata },
    { ad: t('stok.seviye_min'), deger: Math.max(0, minAlti - kritik), renk: RENKLER.uyari },
    { ad: t('stok.seviye_normal'), deger: Math.max(0, toplam - minAlti), renk: RENKLER.basari },
  ].filter((d) => d.deger > 0);

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.malzemeler')}
        alt={t('stok.alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} secenekler={['liste', 'analiz']} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('stok.yeni')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <SunucuTablo<Malzeme>
            kolonlar={kolonlar}
            veri={data?.veri ?? []}
            meta={data?.meta}
            yukleniyor={isPending}
            param={param}
            paramDegistir={paramDegistir}
            rowKey="id"
            aramaYer={t('stok.ara')}
            bosMetin={isError ? t('ortak.hata_baslik') : t('stok.bos')}
            onRow={(kayit) => ({
              onClick: () => navigate(`/malzemeler/${kayit.id}`),
              style: { cursor: 'pointer' },
            })}
          />
        </Card>
      ) : (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <PanelKart baslik={t('stok.analiz_dagilim')} renk={HAT}>
              <EGrafik secenek={donutSecenek(donutVeri)} yukseklik={300} />
            </PanelKart>
          </Col>
        </Row>
      )}

      <MalzemeFormu acik={formAcik} kapat={() => setFormAcik(false)} />
      <StokHareketFormu malzeme={hareketMalzeme} kapat={() => setHareketMalzeme(null)} />
    </SayfaKapsayici>
  );
}
