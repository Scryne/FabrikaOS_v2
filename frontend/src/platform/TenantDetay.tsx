/**
 * Tenant detayı — künye + plan değiştirme + koltuk kullanımı + entitlement matrisi
 * (modül/özellik switch'leri: değişiklik ANINDA etkili) + KVKK ihraçları + tehlikeli
 * bölge (askıya alma / silme: slug-yazarak-onay modalı).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { DownloadOutlined, ExportOutlined } from '@ant-design/icons';
import {
  App as AntdApp,
  Button,
  Card,
  Col,
  Progress,
  Row,
  Select,
  Skeleton,
  Switch,
  Tag,
} from 'antd';

import { platformIstekIndir, PLATFORM_PREFIX } from './api';
import {
  useIhracBaslat,
  useIhraclar,
  useModulHakkiAyarla,
  useOzellikBayragiAyarla,
  usePlanlar,
  useTenantAktiflik,
  useTenantDetay,
  useTenantGuncelle,
  useTenantSil,
} from './hooks';
import type { IhracCevap, ModulDurum, OzellikDurum } from './hooks';
import { TehlikeOnayModal } from './TehlikeOnayModal';

const IHRAC_DURUM_RENGI: Record<string, string> = {
  kuyrukta: 'default',
  hazirlaniyor: 'processing',
  hazir: 'success',
  basarisiz: 'error',
};

function dosyaKaydet(blob: Blob, ad: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = ad;
  a.click();
  URL.revokeObjectURL(url);
}

export function TenantDetay() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { message } = AntdApp.useApp();
  const { id: idParam } = useParams();
  const id = idParam ? Number(idParam) : null;

  const { data, isLoading } = useTenantDetay(id);
  const planlar = usePlanlar();
  const ihraclar = useIhraclar(id);

  const guncelle = useTenantGuncelle(id ?? 0);
  const aktiflik = useTenantAktiflik(id ?? 0);
  const sil = useTenantSil(id ?? 0);
  const modulAyarla = useModulHakkiAyarla(id ?? 0);
  const bayrakAyarla = useOzellikBayragiAyarla(id ?? 0);
  const ihracBaslat = useIhracBaslat(id ?? 0);

  const [silModal, setSilModal] = useState(false);
  const [askiModal, setAskiModal] = useState(false);

  if (isLoading || data == null) return <Skeleton active paragraph={{ rows: 8 }} />;

  const koltukOran =
    data.koltuk_limiti != null && data.koltuk_limiti > 0 && data.koltuk_kullanilan != null
      ? data.koltuk_kullanilan / data.koltuk_limiti
      : null;

  async function hataYut(islem: Promise<unknown>, basarim?: string) {
    try {
      await islem;
      if (basarim) message.success(basarim);
    } catch (h) {
      message.error(h instanceof Error ? h.message : t('platform.islem_hatasi'));
    }
  }

  async function ihracIndir(kayit: IhracCevap) {
    const { blob, dosyaAdi } = await platformIstekIndir(
      `${PLATFORM_PREFIX}/ihraclar/${kayit.id}/indir`,
    );
    dosyaKaydet(blob, dosyaAdi ?? `tenant-${kayit.slug}-ihrac-${kayit.id}.zip`);
  }

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, fontSize: 17 }}>
          <span className="sayisal">{data.slug}</span> — {data.ad}
        </h2>
        {data.aktif ? (
          <Tag color="success">{t('platform.aktif')}</Tag>
        ) : (
          <Tag color="warning">{t('platform.askida')}</Tag>
        )}
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={12}>
          <Card size="small" title={t('platform.plan')}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <Select
                style={{ minWidth: 180 }}
                value={data.plan_kodu}
                loading={guncelle.isPending}
                options={(planlar.data ?? []).map((p) => ({
                  value: p.kod,
                  label: `${p.ad} (${p.kod})`,
                }))}
                onChange={(plan_kodu) =>
                  void hataYut(guncelle.mutateAsync({ plan_kodu }), t('platform.plan_degisti'))
                }
              />
              <span style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>
                {t('platform.durum')}: {data.abonelik_durum ?? '—'}
              </span>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card size="small" title={t('platform.koltuk')}>
            <div className="sayisal" style={{ fontSize: 18 }}>
              {data.koltuk_kullanilan ?? '—'} /{' '}
              {data.koltuk_limiti ?? t('platform.koltuk_sinirsiz')}
            </div>
            {koltukOran != null && (
              <Progress
                percent={Math.min(100, Math.round(koltukOran * 100))}
                showInfo={false}
                size="small"
              />
            )}
          </Card>
        </Col>
      </Row>

      <Card size="small" title={t('platform.modul_matrisi')}>
        <Row gutter={[10, 10]}>
          {data.moduller.map((m: ModulDurum) => (
            <Col xs={24} sm={12} lg={8} key={m.kod}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 8,
                  padding: '8px 12px',
                  border: '1px solid var(--kenarlik)',
                  borderRadius: 8,
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: 13,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                    title={m.ad}
                  >
                    <span className="sayisal">{m.kod}</span>
                  </div>
                  {m.kaynak === 'hak' && (
                    <Button
                      type="link"
                      size="small"
                      style={{ padding: 0, height: 'auto', fontSize: 12 }}
                      onClick={() =>
                        void hataYut(modulAyarla.mutateAsync({ modulKodu: m.kod, acik: null }))
                      }
                    >
                      {t('platform.plana_don')}
                    </Button>
                  )}
                </div>
                <Switch
                  size="small"
                  checked={m.acik}
                  loading={modulAyarla.isPending}
                  onChange={(acik) =>
                    void hataYut(modulAyarla.mutateAsync({ modulKodu: m.kod, acik }))
                  }
                />
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      <Card size="small" title={t('platform.ozellik_bayraklari')}>
        <Row gutter={[10, 10]}>
          {data.ozellikler.map((o: OzellikDurum) => (
            <Col xs={24} sm={12} key={o.kod}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: 8,
                  padding: '8px 12px',
                  border: '1px solid var(--kenarlik)',
                  borderRadius: 8,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                  <span className="sayisal" style={{ fontSize: 13 }}>
                    {o.kod}
                  </span>
                  {o.deneysel && <Tag color="warning">{t('abonelik.deneysel')}</Tag>}
                  {o.kaynak === 'bayrak' && (
                    <Button
                      type="link"
                      size="small"
                      style={{ padding: 0, height: 'auto', fontSize: 12 }}
                      onClick={() =>
                        void hataYut(bayrakAyarla.mutateAsync({ kod: o.kod, acik: null }))
                      }
                    >
                      {t('platform.plana_don')}
                    </Button>
                  )}
                </div>
                <Switch
                  size="small"
                  checked={o.acik}
                  loading={bayrakAyarla.isPending}
                  onChange={(acik) => void hataYut(bayrakAyarla.mutateAsync({ kod: o.kod, acik }))}
                />
              </div>
            </Col>
          ))}
        </Row>
      </Card>

      <Card
        size="small"
        title={t('platform.ihrac')}
        extra={
          <Button
            size="small"
            icon={<ExportOutlined />}
            loading={ihracBaslat.isPending}
            onClick={() => void hataYut(ihracBaslat.mutateAsync(), t('platform.ihrac_baslatildi'))}
          >
            {t('platform.ihrac_baslat')}
          </Button>
        }
      >
        <p style={{ color: 'var(--metin-soluk)', fontSize: 13, marginTop: 0 }}>
          {t('platform.ihrac_aciklama')}
        </p>
        <div style={{ display: 'grid', gap: 8 }}>
          {(ihraclar.data?.veri ?? []).map((k) => (
            <div
              key={k.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 8,
                padding: '6px 12px',
                border: '1px solid var(--kenarlik)',
                borderRadius: 8,
              }}
            >
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
                <span className="sayisal" style={{ fontSize: 13 }}>
                  #{k.id}
                </span>
                <Tag color={IHRAC_DURUM_RENGI[k.durum]}>
                  {t(`platform.durum_${k.durum}`, { defaultValue: k.durum })}
                </Tag>
                <span style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>
                  {new Date(k.olusturma_tarihi).toLocaleString()}
                  {k.tablo_sayisi != null && ` · ${k.tablo_sayisi} ${t('platform.tablolar')}`}
                </span>
              </span>
              {k.durum === 'hazir' && (
                <Button
                  size="small"
                  icon={<DownloadOutlined />}
                  onClick={() => void hataYut(ihracIndir(k))}
                >
                  {t('platform.indir')}
                </Button>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card
        size="small"
        title={<span style={{ color: 'var(--hata)' }}>{t('platform.tehlikeli_bolge')}</span>}
      >
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          {data.aktif ? (
            <Button danger onClick={() => setAskiModal(true)}>
              {t('platform.askiya_al')}
            </Button>
          ) : (
            <Button
              type="primary"
              loading={aktiflik.isPending}
              onClick={() => void hataYut(aktiflik.mutateAsync(true), t('platform.islem_basarili'))}
            >
              {t('platform.aktiflestir')}
            </Button>
          )}
          <Button danger type="primary" onClick={() => setSilModal(true)}>
            {t('platform.sil')}
          </Button>
        </div>
      </Card>

      <TehlikeOnayModal
        acik={askiModal}
        baslik={t('platform.askiya_al')}
        aciklama={t('platform.askiya_uyari')}
        slug={data.slug}
        yukleniyor={aktiflik.isPending}
        onayla={() =>
          void hataYut(
            aktiflik.mutateAsync(false).then(() => setAskiModal(false)),
            t('platform.islem_basarili'),
          )
        }
        kapat={() => setAskiModal(false)}
      />
      <TehlikeOnayModal
        acik={silModal}
        baslik={t('platform.sil')}
        aciklama={t('platform.sil_uyari')}
        slug={data.slug}
        yukleniyor={sil.isPending}
        onayla={() =>
          void hataYut(
            sil.mutateAsync(data.slug).then(() => navigate('/platform', { replace: true })),
            t('platform.islem_basarili'),
          )
        }
        kapat={() => setSilModal(false)}
      />
    </div>
  );
}
