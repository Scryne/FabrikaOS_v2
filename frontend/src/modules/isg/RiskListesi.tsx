/**
 * Risk değerlendirme çalışma alanı — KPI şeridi + **5×5 RiskMatrisi** ısı görseli (hücre tıkla →
 * seviye filtresi) + zengin tablo (skor mini-bar + seviye/durum pimi). Matris hücre sayaçları
 * ``/isg/ozet`` sunucu toplulaştırmasından; skor/seviye saf ``riskMatris`` (backend aynası) ile.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertOutlined, PlusOutlined, SafetyOutlined, WarningOutlined } from '@ant-design/icons';
import { Button, Card, Col, Row, Select, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { pimUret } from '@/components/DurumPim';
import { MiniBar } from '@/components/MiniBar';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { RiskMatrisi } from '@/components/RiskMatrisi';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type RiskDegerlendirme, useIsgOzet, useRiskler } from './hooks';
import { riskSeviyesi, riskSkoru } from './riskMatris';
import { RiskFormu } from './RiskFormu';

const HAT = BOLUM_RENGI['menu.bolum_isg_ik'];
const SEVIYELER = ['dusuk', 'orta', 'yuksek', 'cok_yuksek'];

const SEVIYE_RENK: Record<string, string> = {
  dusuk: RENKLER.basari,
  orta: RENKLER.cyan,
  yuksek: RENKLER.uyari,
  cok_yuksek: RENKLER.hata,
};
const DURUM_RENK: Record<string, string> = {
  acik: RENKLER.metinSoluk,
  devam: RENKLER.mavi,
  kapandi: RENKLER.basari,
};
const SeviyePim = pimUret(SEVIYE_RENK, 'isg.seviye_');
const RiskDurumPim = pimUret(DURUM_RENK, 'isg.risk_durum_');

export function RiskListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const [formAcik, setFormAcik] = useState(false);
  const { data, isPending, isError } = useRiskler(param);
  const { data: ozet, isPending: ozetYukleniyor } = useIsgOzet();

  const seviyeFiltre = param.filtreler?.risk_seviyesi as string | undefined;

  // (olasılık, şiddet) → hücre sayaç haritası (sunucu toplulaştırmasından).
  const hucreHarita = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of ozet?.risk_matrisi ?? []) m.set(`${c.olasilik}-${c.siddet}`, c.adet);
    return m;
  }, [ozet]);

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'acik',
          baslik: t('isg.kpi_acik_risk'),
          deger: String(ozet.acik_risk),
          ikon: <AlertOutlined />,
        },
        {
          anahtar: 'yuksek',
          baslik: t('isg.kpi_yuksek_risk'),
          deger: String(ozet.yuksek_risk),
          ikon: <WarningOutlined />,
        },
        {
          anahtar: 'toplam',
          baslik: t('isg.kpi_toplam_risk'),
          deger: String(ozet.toplam_risk),
          ikon: <SafetyOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<RiskDegerlendirme> = [
    {
      title: t('isg.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('isg.baslik'), dataIndex: 'baslik', key: 'baslik' },
    { title: t('isg.bolum'), dataIndex: 'bolum', key: 'bolum' },
    {
      title: t('isg.risk_skoru'),
      dataIndex: 'risk_skoru',
      key: 'risk_skoru',
      sorter: true,
      render: (v: number, r) => (
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
          <MiniBar
            deger={v}
            enBuyuk={25}
            renk={SEVIYE_RENK[r.risk_seviyesi] ?? RENKLER.metinSoluk}
          />
          <span className="sayisal" style={{ width: 24 }}>
            {v}
          </span>
        </span>
      ),
    },
    {
      title: t('isg.risk_seviyesi'),
      dataIndex: 'risk_seviyesi',
      key: 'risk_seviyesi',
      render: (v: string) => <SeviyePim durum={v} />,
    },
    {
      title: t('isg.risk_durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string) => <RiskDurumPim durum={v} />,
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.risk_degerlendirme')}
        alt={t('isg.risk_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('isg.risk_yeni')}
            </Button>
          )
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={9}>
          <PanelKart baslik={t('isg.matris_baslik')} renk={HAT}>
            <RiskMatrisi
              sayac={(o, s) => hucreHarita.get(`${o}-${s}`) ?? 0}
              renk={(o, s) => SEVIYE_RENK[riskSeviyesi(riskSkoru(o, s))] ?? RENKLER.metinSoluk}
              onHucre={(o, s) =>
                paramDegistir({ filtreler: { risk_seviyesi: riskSeviyesi(riskSkoru(o, s)) } })
              }
            />
          </PanelKart>
        </Col>
        <Col xs={24} lg={15}>
          <Card styles={{ body: { padding: 18 } }}>
            <SunucuTablo<RiskDegerlendirme>
              kolonlar={kolonlar}
              veri={data?.veri ?? []}
              meta={data?.meta}
              yukleniyor={isPending}
              param={param}
              paramDegistir={paramDegistir}
              rowKey="id"
              aramaYer={t('isg.ara')}
              bosMetin={isError ? t('ortak.hata_baslik') : t('isg.risk_bos')}
              araclar={
                <Space>
                  <Select
                    allowClear
                    placeholder={t('isg.risk_seviyesi')}
                    style={{ width: 180 }}
                    value={seviyeFiltre}
                    onChange={(v) => paramDegistir({ filtreler: { risk_seviyesi: v } })}
                    options={SEVIYELER.map((x) => ({ value: x, label: t(`isg.seviye_${x}`) }))}
                  />
                </Space>
              }
            />
          </Card>
        </Col>
      </Row>

      <RiskFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
