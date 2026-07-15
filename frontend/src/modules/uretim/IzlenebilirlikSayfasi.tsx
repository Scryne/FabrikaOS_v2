/**
 * Lot izlenebilirliği (S24) — lot numarası girilir, tek uçtan ileri/geri zincir gelir:
 * geri izleme = lotu üreten iş emirleri + BOM'la tüketilen malzemeler; ileri izleme =
 * makine bazında üretim kayıtları. KPI şeridi zincirden türetilir.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BarcodeOutlined,
  CheckCircleOutlined,
  ExperimentOutlined,
  FileDoneOutlined,
} from '@ant-design/icons';
import { Card, Col, Empty, Input, Row, Table, Tag, Typography } from 'antd';

import { BosDurum } from '@/components/BosDurum';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { DurumEtiketi } from '@/modules/isemri/rozetler';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { useIzlenebilirlik } from './hooks';

const HAT = BOLUM_RENGI['menu.bolum_uretim'];

export function IzlenebilirlikSayfasi() {
  const { t } = useTranslation();
  const [lot, setLot] = useState('');
  const { data, isFetching, isError } = useIzlenebilirlik(lot);

  const toplamUretim = (data?.uretim ?? []).reduce((s, u) => s + u.toplam_adet, 0);
  const toplamSaglam = (data?.uretim ?? []).reduce((s, u) => s + u.saglam_adet, 0);
  const metrikler: OzetMetrik[] = data
    ? [
        {
          anahtar: 'isemri',
          baslik: t('uretim.iz_kpi_isemri'),
          deger: String(data.is_emirleri.length),
          ikon: <FileDoneOutlined />,
        },
        {
          anahtar: 'uretim',
          baslik: t('uretim.iz_kpi_uretim'),
          deger: String(toplamUretim),
          ikon: <BarcodeOutlined />,
        },
        {
          anahtar: 'saglam',
          baslik: t('uretim.iz_kpi_saglam'),
          deger: toplamUretim > 0 ? `%${Math.round((toplamSaglam / toplamUretim) * 100)}` : '—',
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'malzeme',
          baslik: t('uretim.iz_kpi_malzeme'),
          deger: String(data.tuketilen_malzemeler.length),
          ikon: <ExperimentOutlined />,
        },
      ]
    : [];

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('menu.izlenebilirlik')} alt={t('uretim.iz_alt')} />
      <Card styles={{ body: { padding: 18 } }} style={{ marginBottom: 20 }}>
        <Input.Search
          size="large"
          allowClear
          placeholder={t('uretim.iz_lot_ipucu')}
          enterButton={t('uretim.iz_sorgula')}
          loading={isFetching}
          onSearch={(v) => setLot(v.trim())}
          style={{ maxWidth: 480 }}
        />
      </Card>

      {lot.length === 0 ? (
        <BosDurum baslik={t('uretim.iz_bos_baslik')} aciklama={t('uretim.iz_bos_aciklama')} />
      ) : isError ? (
        <BosDurum baslik={t('ortak.hata_baslik')} aciklama={t('uretim.iz_hata')} />
      ) : (
        data && (
          <>
            <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={isFetching} />
            <div style={{ height: 20 }} />
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={8}>
                <Card
                  title={t('uretim.iz_geri_izleme')}
                  styles={{ body: { padding: 18 } }}
                  className="tam-yukseklik"
                >
                  <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                    {t('uretim.iz_isemri_aciklama')}
                  </Typography.Text>
                  <Table
                    size="small"
                    rowKey="id"
                    pagination={false}
                    dataSource={data.is_emirleri}
                    locale={{
                      emptyText: (
                        <Empty
                          description={t('uretim.iz_isemri_yok')}
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                        />
                      ),
                    }}
                    columns={[
                      {
                        title: t('isemri.kod'),
                        dataIndex: 'kod',
                        key: 'kod',
                        render: (v: string) => <span className="sayisal">{v}</span>,
                      },
                      {
                        title: t('isemri.durum'),
                        dataIndex: 'durum',
                        key: 'durum',
                        render: (v: string) => <DurumEtiketi durum={v} />,
                      },
                      {
                        title: t('urun.miktar'),
                        dataIndex: 'miktar',
                        key: 'miktar',
                        align: 'right',
                        render: (v: number | null) =>
                          v != null ? <span className="sayisal">{v}</span> : '—',
                      },
                    ]}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card
                  title={t('uretim.iz_tuketilen')}
                  styles={{ body: { padding: 18 } }}
                  className="tam-yukseklik"
                >
                  <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                    {t('uretim.iz_tuketilen_aciklama')}
                  </Typography.Text>
                  <Table
                    size="small"
                    rowKey={(k) => `${k.is_emri_kod}-${k.malzeme_id}`}
                    pagination={false}
                    dataSource={data.tuketilen_malzemeler}
                    locale={{
                      emptyText: (
                        <Empty
                          description={t('uretim.iz_tuketilen_yok')}
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                        />
                      ),
                    }}
                    columns={[
                      {
                        title: t('urun.malzeme'),
                        key: 'malzeme',
                        render: (_, k) => (
                          <span>
                            <span className="sayisal">{k.malzeme_kod}</span>
                            <span style={{ color: 'var(--metin-soluk)' }}> · {k.malzeme_ad}</span>
                          </span>
                        ),
                      },
                      {
                        title: t('urun.miktar'),
                        dataIndex: 'miktar',
                        key: 'miktar',
                        align: 'right',
                        render: (v: number) => <span className="sayisal">{v}</span>,
                      },
                      {
                        title: t('isemri.kod'),
                        dataIndex: 'is_emri_kod',
                        key: 'is_emri_kod',
                        render: (v: string) => <Tag>{v}</Tag>,
                      },
                    ]}
                  />
                </Card>
              </Col>
              <Col xs={24} lg={8}>
                <Card
                  title={t('uretim.iz_ileri_izleme')}
                  styles={{ body: { padding: 18 } }}
                  className="tam-yukseklik"
                >
                  <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 12 }}>
                    {t('uretim.iz_uretim_aciklama')}
                  </Typography.Text>
                  <Table
                    size="small"
                    rowKey="makine_id"
                    pagination={false}
                    dataSource={data.uretim}
                    locale={{
                      emptyText: (
                        <Empty
                          description={t('uretim.iz_uretim_yok')}
                          image={Empty.PRESENTED_IMAGE_SIMPLE}
                        />
                      ),
                    }}
                    columns={[
                      {
                        title: t('uretim.makine'),
                        dataIndex: 'makine_kod',
                        key: 'makine_kod',
                        render: (v: string) => <span className="sayisal">{v}</span>,
                      },
                      {
                        title: t('uretim.toplam_adet'),
                        dataIndex: 'toplam_adet',
                        key: 'toplam_adet',
                        align: 'right',
                        render: (v: number) => <span className="sayisal">{v}</span>,
                      },
                      {
                        title: t('uretim.saglam_adet'),
                        dataIndex: 'saglam_adet',
                        key: 'saglam_adet',
                        align: 'right',
                        render: (v: number) => <span className="sayisal">{v}</span>,
                      },
                      {
                        title: t('uretim.iz_son_kayit'),
                        dataIndex: 'son_zaman',
                        key: 'son_zaman',
                        render: (v: string | null) =>
                          v ? <span className="sayisal">{new Date(v).toLocaleString()}</span> : '—',
                      },
                    ]}
                  />
                </Card>
              </Col>
            </Row>
          </>
        )
      )}
    </SayfaKapsayici>
  );
}
