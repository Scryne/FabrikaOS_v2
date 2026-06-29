/**
 * Makine detayı — OEE göstergesi (gauge) + bileşen kırılımı (kullanılabilirlik/performans/kalite)
 * + bu makinenin son üretim kayıtları. ``uretim:yaz`` ile durum güncelleme ve üretim girişi açılır.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeftOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Card, Col, Result, Row, Select, Skeleton, Space, Statistic } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { DurumRozet, MAKINE_DURUMLARI } from '@/components/DurumRozet';
import { EGrafik } from '@/components/grafik/EGrafik';
import { gostergeSecenek, oeeRenk } from '@/components/grafik/grafikSecenek';
import { OranSatiri } from '@/components/OranSatiri';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { RENKLER } from '@/tema/tema';
import { useAuthStore } from '@/store/authStore';

import {
  type UretimVerisi,
  useMakine,
  useMakineDurumGuncelle,
  useMakineOee,
  useUretimVerileri,
} from './hooks';
import { UretimGirisFormu } from './UretimGirisFormu';

export function MakineDetay() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id: idParam } = useParams();
  const id = Number(idParam);
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));

  const makine = useMakine(id);
  const oee = useMakineOee(id);
  const durumGuncelle = useMakineDurumGuncelle();
  const [param, paramDegistir] = useSayfaParam({
    adet: 8,
    siralama: 'zaman',
    yon: 'desc',
    filtreler: { makine_id: id },
  });
  const uretim = useUretimVerileri(param);
  const [formAcik, setFormAcik] = useState(false);

  const yuzde = (oee.data?.oee ?? 0) * 100;
  const gaugeSecenek = useMemo(() => gostergeSecenek(yuzde), [yuzde]);

  const kolonlar: ColumnsType<UretimVerisi> = [
    {
      title: t('uretim.zaman'),
      dataIndex: 'zaman',
      key: 'zaman',
      sorter: true,
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM HH:mm')}</span>,
    },
    { title: t('uretim.vardiya'), dataIndex: 'vardiya', key: 'vardiya', render: (v) => v ?? '—' },
    {
      title: t('uretim.toplam_adet'),
      dataIndex: 'toplam_adet',
      key: 'toplam_adet',
      align: 'right',
      sorter: true,
      render: (v: number) => <span className="sayisal">{v.toLocaleString('tr-TR')}</span>,
    },
    {
      title: t('uretim.saglam_adet'),
      dataIndex: 'saglam_adet',
      key: 'saglam_adet',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v.toLocaleString('tr-TR')}</span>,
    },
  ];

  if (makine.isPending) {
    return (
      <div style={{ maxWidth: 1320 }}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </div>
    );
  }

  if (makine.isError || !makine.data) {
    return (
      <Result
        status="404"
        title={t('uretim.makine_bulunamadi')}
        extra={
          <Button type="primary" onClick={() => navigate('/makineler')}>
            {t('ortak.geri')}
          </Button>
        }
      />
    );
  }

  const m = makine.data;

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={
          <Space size={12} align="center" wrap>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/makineler')}
              aria-label={t('ortak.geri')}
            />
            <span className="sayisal">{m.kod}</span>
            <span style={{ color: 'var(--metin-soluk)', fontWeight: 400 }}>{m.ad}</span>
          </Space>
        }
        sag={
          <Space wrap>
            {yazabilir ? (
              <Select
                value={m.durum}
                style={{ width: 160 }}
                loading={durumGuncelle.isPending}
                onChange={(durum) => durumGuncelle.mutate({ id, durum })}
                options={MAKINE_DURUMLARI.map((d) => ({
                  value: d,
                  label: t(`uretim.durum_${d}`),
                }))}
              />
            ) : (
              <DurumRozet durum={m.durum} />
            )}
            {yazabilir && (
              <Button icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('uretim.uretim_girisi')}
              </Button>
            )}
          </Space>
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={9}>
          <Card title={t('uretim.oee_skoru')} style={{ height: '100%' }}>
            {oee.isPending ? (
              <Skeleton active />
            ) : (
              <>
                <EGrafik secenek={gaugeSecenek} yukseklik={220} />
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginTop: 8 }}>
                  <OranSatiri
                    etiket={t('pano.kullanilabilirlik')}
                    yuzde={(oee.data?.kullanilabilirlik ?? 0) * 100}
                    renk={RENKLER.basari}
                  />
                  <OranSatiri
                    etiket={t('pano.performans')}
                    yuzde={(oee.data?.performans ?? 0) * 100}
                    renk={RENKLER.mavi}
                  />
                  <OranSatiri
                    etiket={t('pano.kalite')}
                    yuzde={(oee.data?.kalite ?? 0) * 100}
                    renk={RENKLER.uyari}
                  />
                </div>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginTop: 18,
                    paddingTop: 16,
                    borderTop: '1px solid var(--kenarlik)',
                  }}
                >
                  <Statistic
                    title={t('uretim.kayit_sayisi')}
                    value={oee.data?.kayit_sayisi ?? 0}
                    valueStyle={{ fontFamily: 'var(--font-mono)', fontSize: 20 }}
                  />
                  <Statistic
                    title={t('uretim.oee_hedefi')}
                    value={m.oee_hedefi != null ? Math.round(m.oee_hedefi * 100) : '—'}
                    suffix={m.oee_hedefi != null ? '%' : ''}
                    valueStyle={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 20,
                      color: oeeRenk(yuzde),
                    }}
                  />
                </div>
              </>
            )}
          </Card>
        </Col>

        <Col xs={24} xl={15}>
          <Card title={t('uretim.son_uretim')} style={{ height: '100%' }}>
            <SunucuTablo<UretimVerisi>
              kolonlar={kolonlar}
              veri={uretim.data?.veri ?? []}
              meta={uretim.data?.meta}
              yukleniyor={uretim.isPending}
              param={param}
              paramDegistir={paramDegistir}
              rowKey="id"
              bosMetin={t('uretim.bu_makine_uretim_yok')}
            />
          </Card>
        </Col>
      </Row>

      <UretimGirisFormu acik={formAcik} kapat={() => setFormAcik(false)} makineId={id} />
    </div>
  );
}
