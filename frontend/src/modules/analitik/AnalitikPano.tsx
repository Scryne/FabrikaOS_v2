/**
 * Analitik pano — modüller-arası KPI kartları + günlük üretim/OEE trend çizgileri.
 * Dönem seçici (7/30/90 gün) tüm bloğu yeniden sorgular. ``analitik:oku`` korumalı (rota kapısı).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertOutlined,
  DashboardOutlined,
  FileDoneOutlined,
  LineChartOutlined,
  MedicineBoxOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import { Card, Col, Row, Segmented, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { EGrafik } from '@/components/grafik/EGrafik';
import { cizgiSecenek } from '@/components/grafik/grafikSecenek';
import { KpiKart } from '@/components/KpiKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';

import { type KpiCevap, useKpi, useTrend } from './hooks';

const DONEMLER = [7, 30, 90] as const;

function yuzde(oran: number | undefined): string {
  return oran === undefined ? '—' : `%${Math.round(oran * 100)}`;
}

type EnerjiSatiri = KpiCevap['enerji']['kirilim'][number];

export function AnalitikPano() {
  const { t } = useTranslation();
  const [gun, setGun] = useState<number>(30);
  const { data: kpi } = useKpi(gun);
  const { data: trend } = useTrend(gun);

  const enerjiKolon: ColumnsType<EnerjiSatiri> = [
    {
      title: t('analitik.enerji_turu'),
      dataIndex: 'enerji_turu',
      key: 'enerji_turu',
      render: (v: string) => t(`analitik.enerji_${v}`, { defaultValue: v }),
    },
    {
      title: t('analitik.enerji_toplam'),
      dataIndex: 'toplam',
      key: 'toplam',
      align: 'right',
      render: (v: number, kayit) => (
        <span className="sayisal">
          {v.toLocaleString('tr-TR', { maximumFractionDigits: 1 })} {kayit.birim}
        </span>
      ),
    },
  ];

  const oeeSerisi = (trend ?? []).map((n) => ({
    zaman: n.gun,
    deger: Math.round(n.oee * 1000) / 10,
  }));
  const adetSerisi = (trend ?? []).map((n) => ({ zaman: n.gun, deger: n.toplam_adet }));

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.analitik')}
        alt={t('analitik.alt')}
        sag={
          <Segmented
            value={gun}
            onChange={(v) => setGun(Number(v))}
            options={DONEMLER.map((g) => ({ label: t('analitik.gun_n', { n: g }), value: g }))}
          />
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.donem_oee')}
            renk="var(--hat-zeka)"
            deger={yuzde(kpi?.uretim.oee)}
            ikon={<DashboardOutlined />}
            altMetin={t('analitik.oee_bilesen', {
              k: yuzde(kpi?.uretim.kullanilabilirlik),
              p: yuzde(kpi?.uretim.performans),
              q: yuzde(kpi?.uretim.kalite),
            })}
          />
        </Col>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.toplam_uretim')}
            renk="var(--hat-uretim)"
            deger={(kpi?.uretim.toplam_adet ?? 0).toLocaleString('tr-TR')}
            ikon={<LineChartOutlined />}
            altMetin={t('analitik.fire_n', { oran: yuzde(kpi?.uretim.fire_orani) })}
          />
        </Col>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.makineler')}
            renk="var(--cyan)"
            deger={`${kpi?.makine.durumlar['calisiyor'] ?? 0}/${kpi?.makine.toplam ?? 0}`}
            ikon={<RobotOutlined />}
            altMetin={t('analitik.arizali_n', { n: kpi?.makine.durumlar['ariza'] ?? 0 })}
          />
        </Col>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.acik_isemri')}
            renk="var(--mavi)"
            deger={String(kpi?.isemri.acik ?? '—')}
            ikon={<FileDoneOutlined />}
            altMetin={
              kpi?.isemri.ortalama_kapanma_saat != null
                ? t('analitik.ort_kapanma', {
                    saat: kpi.isemri.ortalama_kapanma_saat.toLocaleString('tr-TR', {
                      maximumFractionDigits: 1,
                    }),
                  })
                : t('analitik.kapanan_n', { n: kpi?.isemri.kapanan ?? 0 })
            }
          />
        </Col>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.kritik_stok')}
            renk="var(--uyari)"
            deger={String(kpi?.stok.kritik_sayisi ?? '—')}
            ikon={<AlertOutlined />}
            altMetin={t('analitik.malzeme_n', { n: kpi?.stok.toplam_malzeme ?? 0 })}
          />
        </Col>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.kalite_gecme')}
            renk="var(--hat-kalite)"
            deger={kpi?.kalite.gecme_orani != null ? yuzde(kpi.kalite.gecme_orani) : '—'}
            ikon={<SafetyCertificateOutlined />}
            altMetin={t('analitik.acik_uygunsuzluk_n', { n: kpi?.kalite.acik_uygunsuzluk ?? 0 })}
          />
        </Col>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.isg_olay')}
            renk="var(--hat-isg)"
            deger={String(kpi?.isg.olay_sayisi ?? '—')}
            ikon={<MedicineBoxOutlined />}
            altMetin={t('analitik.kaza_n', { n: kpi?.isg.kaza_sayisi ?? 0 })}
          />
        </Col>
        <Col xs={12} md={8} lg={6}>
          <KpiKart
            baslik={t('analitik.geciken_bakim')}
            renk="var(--hata)"
            deger={String(kpi?.bakim.geciken ?? '—')}
            ikon={<ToolOutlined />}
            altMetin={t('analitik.aktif_plan_n', { n: kpi?.bakim.aktif_plan ?? 0 })}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={t('analitik.oee_trendi')} styles={{ body: { padding: 12 } }}>
            <EGrafik secenek={cizgiSecenek(oeeSerisi)} yukseklik={260} />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title={t('analitik.uretim_trendi')} styles={{ body: { padding: 12 } }}>
            <EGrafik secenek={cizgiSecenek(adetSerisi)} yukseklik={260} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title={t('analitik.enerji_kirilimi')} styles={{ body: { padding: 12 } }}>
            <Table<EnerjiSatiri>
              rowKey={(s) => `${s.enerji_turu}-${s.birim}`}
              size="small"
              pagination={false}
              dataSource={kpi?.enerji.kirilim ?? []}
              columns={enerjiKolon}
              locale={{ emptyText: t('analitik.enerji_bos') }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
