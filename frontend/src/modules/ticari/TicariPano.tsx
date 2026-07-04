/**
 * Ticari pano — odaklı özet: KPI kartları (firma/aktif sözleşme/yaklaşan/açık talep/duyuru) +
 * yaklaşan sözleşme tablosu + son duyurular. ``crm:oku`` korumalı (rota kapısı).
 */

import { useTranslation } from 'react-i18next';
import {
  BankOutlined,
  BellOutlined,
  ClockCircleOutlined,
  FileProtectOutlined,
  InboxOutlined,
} from '@ant-design/icons';
import { Card, Col, List, Row, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { KpiKart } from '@/components/KpiKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';

import { type TicariOzet, useTicariOzet } from './hooks';

type Yaklasan = TicariOzet['yaklasan_sozlesmeler'][number];
type Duyuru = TicariOzet['son_duyurular'][number];

const ONEM_RENK: Record<string, string> = { bilgi: 'blue', uyari: 'orange', kritik: 'error' };

export function TicariPano() {
  const { t } = useTranslation();
  const { data, isPending } = useTicariOzet();
  const s = data?.sayaclar;

  const yaklasanKolon: ColumnsType<Yaklasan> = [
    {
      title: t('sozlesme.kod'),
      dataIndex: 'kod',
      key: 'kod',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('sozlesme.baslik'), dataIndex: 'baslik', key: 'baslik' },
    { title: t('sozlesme.bitis'), dataIndex: 'bitis_tarihi', key: 'bitis_tarihi' },
    {
      title: t('ticari.kalan'),
      dataIndex: 'kalan_gun',
      key: 'kalan_gun',
      align: 'right',
      render: (v: number) => (
        <Tag color={v <= 7 ? 'error' : 'warning'} bordered={false}>
          {t('sozlesme.kalan_gun', { gun: v })}
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik baslik={t('menu.ticari_pano')} alt={t('ticari.alt')} />
      <Row gutter={[16, 16]}>
        <Col xs={12} md={8} lg={4}>
          <KpiKart
            baslik={t('ticari.firma_sayisi')}
            deger={String(s?.firma_sayisi ?? '—')}
            ikon={<BankOutlined />}
            altMetin={t('ticari.aktif_n', { n: s?.aktif_firma ?? 0 })}
          />
        </Col>
        <Col xs={12} md={8} lg={5}>
          <KpiKart
            baslik={t('ticari.aktif_sozlesme')}
            deger={String(s?.aktif_sozlesme ?? '—')}
            ikon={<FileProtectOutlined />}
          />
        </Col>
        <Col xs={12} md={8} lg={5}>
          <KpiKart
            baslik={t('ticari.yaklasan_sozlesme')}
            deger={String(s?.yaklasan_sozlesme ?? '—')}
            ikon={<ClockCircleOutlined />}
            altMetin={t('ticari.gun30')}
          />
        </Col>
        <Col xs={12} md={8} lg={5}>
          <KpiKart
            baslik={t('ticari.acik_talep')}
            deger={String(s?.acik_talep ?? '—')}
            ikon={<InboxOutlined />}
          />
        </Col>
        <Col xs={12} md={8} lg={5}>
          <KpiKart
            baslik={t('ticari.yayinli_duyuru')}
            deger={String(s?.yayinli_duyuru ?? '—')}
            ikon={<BellOutlined />}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={15}>
          <Card title={t('ticari.yaklasan_sozlesmeler')} styles={{ body: { padding: 12 } }}>
            <Table<Yaklasan>
              rowKey="id"
              size="small"
              loading={isPending}
              pagination={false}
              dataSource={data?.yaklasan_sozlesmeler ?? []}
              columns={yaklasanKolon}
              locale={{ emptyText: t('ticari.yaklasan_bos') }}
            />
          </Card>
        </Col>
        <Col xs={24} lg={9}>
          <Card title={t('ticari.son_duyurular')} styles={{ body: { padding: 12 } }}>
            <List<Duyuru>
              size="small"
              dataSource={data?.son_duyurular ?? []}
              locale={{ emptyText: t('ticari.duyuru_bos') }}
              renderItem={(d) => (
                <List.Item>
                  <List.Item.Meta
                    title={d.baslik}
                    description={<span className="sayisal">{d.kod}</span>}
                  />
                  <Tag color={ONEM_RENK[d.onem] ?? 'default'} bordered={false}>
                    {t(`duyuru.onem_${d.onem}`)}
                  </Tag>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
