/**
 * Makine detayı — zengin makine kontrol paneli. Üretim KPI şeridi (OEE, sağlam oranı, toplam
 * üretim, duruş) + OEE enstrümanı (gauge + bileşen kırılımı + hedef) + üretim trendi (alan
 * grafiği: toplam/sağlam) + vardiya kırılımı (donut) + zenginleştirilmiş üretim kaydı tablosu
 * (sağlam oranı mini-bar + duruş). ``uretim:yaz`` ile durum güncelleme + üretim girişi açılır.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  DashboardOutlined,
  LineChartOutlined,
  PauseCircleOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Col, Result, Row, Segmented, Select, Skeleton, Space, Statistic } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { DurumRozet, MAKINE_DURUMLARI } from '@/components/DurumRozet';
import { EGrafik } from '@/components/grafik/EGrafik';
import {
  alanSecenek,
  donutSecenek,
  gostergeSecenek,
  oeeRenk,
} from '@/components/grafik/grafikSecenek';
import { MiniBar } from '@/components/MiniBar';
import { OranSatiri } from '@/components/OranSatiri';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useBakimMetrikleri } from '@/modules/bakim/hooks';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { GRAFIK_PALETI, RENKLER } from '@/tema/tema';
import { useAuthStore } from '@/store/authStore';

import {
  type UretimVerisi,
  useMakine,
  useMakineDurumGuncelle,
  useMakineOee,
  useMakineUretimSerisi,
  useUretimVerileri,
} from './hooks';
import { UretimGirisFormu } from './UretimGirisFormu';

// Üretim hat rengi (hex) — OzetSerit/PanelKart + sparkline gradyanı hex bekler (BOLUM_RENGI deseni).
const HAT = RENKLER.cyan;

export function MakineDetay() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id: idParam } = useParams();
  const id = Number(idParam);
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));

  const makine = useMakine(id);
  const oee = useMakineOee(id);
  const seriSorgu = useMakineUretimSerisi(id);
  const durumGuncelle = useMakineDurumGuncelle();
  const [param, paramDegistir] = useSayfaParam({
    adet: 8,
    siralama: 'zaman',
    yon: 'desc',
    filtreler: { makine_id: id },
  });
  const uretim = useUretimVerileri(param);
  const [formAcik, setFormAcik] = useState(false);

  // Güvenilirlik metrikleri (S24) — bakim:oku olmayan kullanıcıda sorgu hiç atılmaz.
  const bakimOku = useAuthStore((s) => s.izinVar('bakim:oku'));
  const [metrikGun, setMetrikGun] = useState(90);
  const metrikler = useBakimMetrikleri(id, metrikGun, bakimOku);

  const yuzde = (oee.data?.oee ?? 0) * 100;
  const gaugeSecenek = useMemo(() => gostergeSecenek(yuzde), [yuzde]);

  // Seri türevleri: kronolojik trend + vardiya kırılımı + toplulaştırma.
  const turev = useMemo(() => {
    const seri = seriSorgu.data ?? [];
    const kron = [...seri].reverse();
    const kategoriler = kron.map((r) => dayjs(r.zaman).format('DD.MM HH:mm'));
    const toplamSeri = kron.map((r) => r.toplam_adet);
    const saglamSeri = kron.map((r) => r.saglam_adet);
    const toplamUretim = seri.reduce((a, r) => a + r.toplam_adet, 0);
    const saglamToplam = seri.reduce((a, r) => a + r.saglam_adet, 0);
    const toplamDurus = seri.reduce((a, r) => a + (r.durus_sure_dk ?? 0), 0);
    const saglamOrani = toplamUretim > 0 ? Math.round((saglamToplam / toplamUretim) * 100) : 0;
    const vardiyaMap = new Map<string, number>();
    for (const r of seri) {
      const v = r.vardiya ?? '—';
      vardiyaMap.set(v, (vardiyaMap.get(v) ?? 0) + r.toplam_adet);
    }
    const vardiyaSeg = [...vardiyaMap.entries()].map(([ad, deger], i) => ({
      ad,
      deger,
      renk: GRAFIK_PALETI[i % GRAFIK_PALETI.length]!,
    }));
    return {
      bos: seri.length === 0,
      kategoriler,
      toplamSeri,
      saglamSeri,
      toplamUretim,
      toplamDurus,
      saglamOrani,
      vardiyaSeg,
    };
  }, [seriSorgu.data]);

  const trendSecenek = useMemo(
    () =>
      alanSecenek(turev.kategoriler, [
        { ad: t('uretim.seri_toplam'), veri: turev.toplamSeri, renk: RENKLER.cyan },
        { ad: t('uretim.seri_saglam'), veri: turev.saglamSeri, renk: RENKLER.basari },
      ]),
    [turev, t],
  );
  const vardiyaSecenek = useMemo(() => donutSecenek(turev.vardiyaSeg), [turev.vardiyaSeg]);

  const ozetMetrikler: OzetMetrik[] = [
    {
      anahtar: 'oee',
      baslik: t('uretim.oee_skoru'),
      deger: `%${Math.round(yuzde)}`,
      ikon: <DashboardOutlined />,
    },
    {
      anahtar: 'saglam',
      baslik: t('uretim.saglam_orani'),
      deger: `%${turev.saglamOrani}`,
      ikon: <CheckCircleOutlined />,
    },
    {
      anahtar: 'toplam',
      baslik: t('uretim.toplam_uretim'),
      deger: turev.toplamUretim.toLocaleString('tr-TR'),
      ikon: <LineChartOutlined />,
      seri: turev.toplamSeri.length >= 2 ? turev.toplamSeri : undefined,
    },
    {
      anahtar: 'durus',
      baslik: t('uretim.toplam_durus'),
      deger: turev.toplamDurus.toLocaleString('tr-TR'),
      birim: t('pano.birim_dk'),
      ikon: <PauseCircleOutlined />,
    },
  ];

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
      render: (v: number | null) => <span className="sayisal">{v ?? 0}</span>,
    },
  ];

  if (makine.isPending) {
    return (
      <SayfaKapsayici>
        <Skeleton active paragraph={{ rows: 6 }} />
      </SayfaKapsayici>
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
    <SayfaKapsayici>
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

      <div style={{ marginBottom: 16 }}>
        <OzetSerit metrikler={ozetMetrikler} renk={HAT} yukleniyor={oee.isPending} />
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={9}>
          <PanelKart baslik={t('uretim.oee_skoru')} renk={HAT} sinif="tam-yukseklik">
            {oee.isPending ? (
              <Skeleton active />
            ) : (
              <>
                <EGrafik secenek={gaugeSecenek} yukseklik={200} />
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
          </PanelKart>
        </Col>

        <Col xs={24} xl={15}>
          <PanelKart baslik={t('pano.uretim_trendi')} renk={HAT} sinif="tam-yukseklik">
            {seriSorgu.isPending ? (
              <Skeleton active paragraph={{ rows: 5 }} />
            ) : turev.bos ? (
              <div className="widget-bos">{t('uretim.bu_makine_uretim_yok')}</div>
            ) : (
              <EGrafik secenek={trendSecenek} yukseklik={286} />
            )}
          </PanelKart>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} xl={9}>
          <PanelKart baslik={t('uretim.vardiya_kirilimi')} renk={HAT} sinif="tam-yukseklik">
            {seriSorgu.isPending ? (
              <Skeleton active />
            ) : turev.vardiyaSeg.length === 0 ? (
              <div className="widget-bos">{t('uretim.bu_makine_uretim_yok')}</div>
            ) : (
              <>
                <EGrafik secenek={vardiyaSecenek} yukseklik={200} />
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px', marginTop: 8 }}>
                  {turev.vardiyaSeg.map((s) => (
                    <span
                      key={s.ad}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        fontSize: 12.5,
                      }}
                    >
                      <span
                        style={{ width: 9, height: 9, borderRadius: 3, background: s.renk }}
                        aria-hidden="true"
                      />
                      <span style={{ color: 'var(--metin-soluk)' }}>{s.ad}</span>
                      <span className="sayisal" style={{ color: 'var(--metin)' }}>
                        {s.deger.toLocaleString('tr-TR')}
                      </span>
                    </span>
                  ))}
                </div>
              </>
            )}
          </PanelKart>
        </Col>

        <Col xs={24} xl={15}>
          <PanelKart baslik={t('uretim.son_uretim')} renk={HAT} sinif="tam-yukseklik">
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
          </PanelKart>
        </Col>
      </Row>

      {bakimOku && (
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24}>
            <PanelKart
              baslik={t('bakim.metrik_baslik')}
              renk={HAT}
              sag={
                <Segmented<number>
                  size="small"
                  value={metrikGun}
                  onChange={setMetrikGun}
                  options={[
                    { value: 30, label: t('bakim.gun_30') },
                    { value: 90, label: t('bakim.gun_90') },
                    { value: 365, label: t('bakim.gun_365') },
                  ]}
                />
              }
            >
              {metrikler.isPending ? (
                <Skeleton active paragraph={{ rows: 1 }} />
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px 48px' }}>
                  <Statistic
                    title={t('bakim.mtbf')}
                    value={metrikler.data?.mtbf_saat ?? '—'}
                    suffix={metrikler.data?.mtbf_saat != null ? t('bakim.saat') : ''}
                    valueStyle={{ fontFamily: 'var(--font-mono)', fontSize: 22 }}
                  />
                  <Statistic
                    title={t('bakim.mttr')}
                    value={metrikler.data?.mttr_saat ?? '—'}
                    suffix={metrikler.data?.mttr_saat != null ? t('bakim.saat') : ''}
                    valueStyle={{ fontFamily: 'var(--font-mono)', fontSize: 22 }}
                  />
                  <Statistic
                    title={t('bakim.ariza_sayisi')}
                    value={metrikler.data?.ariza_sayisi ?? 0}
                    valueStyle={{ fontFamily: 'var(--font-mono)', fontSize: 22 }}
                  />
                  <Statistic
                    title={t('bakim.toplam_ariza_saat')}
                    value={metrikler.data?.toplam_ariza_saat ?? 0}
                    suffix={t('bakim.saat')}
                    valueStyle={{ fontFamily: 'var(--font-mono)', fontSize: 22 }}
                  />
                </div>
              )}
            </PanelKart>
          </Col>
        </Row>
      )}

      <UretimGirisFormu acik={formAcik} kapat={() => setFormAcik(false)} makineId={id} />
    </SayfaKapsayici>
  );
}
