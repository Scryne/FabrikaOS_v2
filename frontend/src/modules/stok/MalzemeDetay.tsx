/**
 * Malzeme detayı — zengin stok kontrol paneli. Stok KPI şeridi (mevcut/kritik eşik/giriş/çıkış) +
 * stok seviyesi göstergesi (mevcut, kritik & min eşik işaretli bar + seviye pimi) + bakiye trendi
 * (alan grafiği) + hareket kırılımı (giriş/çıkış/düzeltme donut) + zenginleştirilmiş hareket tablosu
 * (tür pimi + miktar/bakiye). ``stok:yaz`` ile "stok hareketi" ve "düzenle" açılır; canlı invalidate.
 */

import { useMemo, useState } from 'react';
import type { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  AlertOutlined,
  ArrowDownOutlined,
  ArrowLeftOutlined,
  ArrowUpOutlined,
  EditOutlined,
  GoldOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Result, Skeleton, Space, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { DurumPim } from '@/components/DurumPim';
import { EGrafik } from '@/components/grafik/EGrafik';
import { alanSecenek, donutSecenek } from '@/components/grafik/grafikSecenek';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { RENKLER } from '@/tema/tema';
import { useAuthStore } from '@/store/authStore';

import {
  type Malzeme,
  type StokHareketi,
  useMalzeme,
  useStokHareketleri,
  useStokHareketSerisi,
} from './hooks';
import { MalzemeFormu } from './MalzemeFormu';
import { StokHareketFormu } from './StokHareketFormu';

// Stok hat rengi (hex) — OzetSerit/PanelKart + grafik gradyanı hex bekler.
const HAT = '#2dd4bf';
const TUR_RENK: Record<string, string> = {
  giris: RENKLER.basari,
  cikis: RENKLER.hata,
  duzeltme: RENKLER.uyari,
};

/** Stok seviyesi barı — mevcut miktarı 0..tavan aralığında; kritik & min eşikleri işaretli. */
function StokSeviyeBar({
  mevcut,
  kritik,
  min,
  birim,
}: {
  mevcut: number;
  kritik: number;
  min: number;
  birim: string;
}) {
  const { t } = useTranslation();
  const tavan = Math.max(mevcut * 1.15, min * 1.3, kritik * 1.5, 10);
  const oranMevcut = Math.max(0, Math.min(1, mevcut / tavan));
  const yer = (v: number) => `${Math.max(0, Math.min(1, v / tavan)) * 100}%`;
  const seviye = mevcut <= kritik ? 'kritik' : mevcut <= min ? 'min' : 'normal';
  const renk =
    seviye === 'kritik' ? 'var(--hata)' : seviye === 'min' ? 'var(--uyari)' : 'var(--basari)';

  return (
    <div>
      <div
        style={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 10,
        }}
      >
        <div>
          <span
            className="sayisal"
            style={{ fontSize: 30, fontWeight: 700, letterSpacing: '-0.02em' }}
          >
            {mevcut.toLocaleString('tr-TR')}
          </span>
          <span style={{ color: 'var(--metin-soluk)', fontSize: 14, marginLeft: 6 }}>{birim}</span>
        </div>
        <DurumPim renk={renk} etiket={t(`stok.seviye_${seviye}`)} />
      </div>

      <div
        style={{
          position: 'relative',
          height: 14,
          marginTop: 16,
          borderRadius: 7,
          background: 'rgba(255,255,255,0.06)',
          overflow: 'hidden',
        }}
        aria-hidden="true"
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            width: '100%',
            background: renk,
            borderRadius: 7,
            transformOrigin: 'left',
            transform: `scaleX(${oranMevcut})`,
            transition: 'transform var(--gecis)',
          }}
        />
        <span
          style={{
            position: 'absolute',
            top: -3,
            bottom: -3,
            left: yer(kritik),
            width: 2,
            background: 'var(--hata)',
          }}
        />
        <span
          style={{
            position: 'absolute',
            top: -3,
            bottom: -3,
            left: yer(min),
            width: 2,
            background: 'var(--uyari)',
          }}
        />
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '8px 18px',
          marginTop: 14,
          fontSize: 12.5,
        }}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
          <span style={{ width: 2, height: 12, background: 'var(--hata)' }} aria-hidden="true" />
          <span style={{ color: 'var(--metin-soluk)' }}>{t('stok.kritik_esik')}</span>
          <span className="sayisal" style={{ color: 'var(--metin)' }}>
            {kritik}
          </span>
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 7 }}>
          <span style={{ width: 2, height: 12, background: 'var(--uyari)' }} aria-hidden="true" />
          <span style={{ color: 'var(--metin-soluk)' }}>{t('stok.min')}</span>
          <span className="sayisal" style={{ color: 'var(--metin)' }}>
            {min}
          </span>
        </span>
      </div>
    </div>
  );
}

export function MalzemeDetay() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { id: idParam } = useParams();
  const id = Number(idParam);
  const yazabilir = useAuthStore((s) => s.izinVar('stok:yaz'));

  const malzeme = useMalzeme(id);
  const seriSorgu = useStokHareketSerisi(id);
  const [param, paramDegistir] = useSayfaParam({ adet: 8 });
  const hareketler = useStokHareketleri(param, id);
  const [hareketAcik, setHareketAcik] = useState(false);
  const [duzenleAcik, setDuzenleAcik] = useState(false);

  // Seri türevleri: kronolojik bakiye trendi + tür kırılımı + giriş/çıkış toplamı.
  const turev = useMemo(() => {
    const seri = [...(seriSorgu.data ?? [])].sort((a, b) =>
      a.olusturma_tarihi.localeCompare(b.olusturma_tarihi),
    );
    const kategoriler = seri.map((h) => dayjs(h.olusturma_tarihi).format('DD.MM HH:mm'));
    const bakiye = seri.map((h) => h.bakiye_sonrasi);
    const turMap = new Map<string, number>();
    for (const h of seri) turMap.set(h.tur, (turMap.get(h.tur) ?? 0) + h.miktar);
    const turSeg = [...turMap.entries()].map(([tur, deger]) => ({
      ad: t(`stok.${tur}`),
      deger,
      renk: TUR_RENK[tur] ?? RENKLER.metinSoluk,
    }));
    return {
      bos: seri.length === 0,
      kategoriler,
      bakiye,
      turSeg,
      giris: turMap.get('giris') ?? 0,
      cikis: turMap.get('cikis') ?? 0,
    };
  }, [seriSorgu.data, t]);

  const trendSecenek = useMemo(
    () =>
      alanSecenek(turev.kategoriler, [
        { ad: t('stok.bakiye_sonrasi'), veri: turev.bakiye, renk: HAT },
      ]),
    [turev, t],
  );
  const turSecenek = useMemo(() => donutSecenek(turev.turSeg), [turev.turSeg]);

  const kolonlar: ColumnsType<StokHareketi> = [
    {
      title: t('stok.tur'),
      dataIndex: 'tur',
      key: 'tur',
      render: (v: string) => (
        <DurumPim renk={TUR_RENK[v] ?? RENKLER.metinSoluk} etiket={t(`stok.${v}`)} />
      ),
    },
    {
      title: t('stok.miktar'),
      dataIndex: 'miktar',
      key: 'miktar',
      align: 'right',
      render: (v: number, r) => (
        <span
          className="sayisal"
          style={{ color: r.tur === 'cikis' ? 'var(--hata)' : 'var(--metin)' }}
        >
          {r.tur === 'cikis' ? '−' : r.tur === 'giris' ? '+' : ''}
          {v}
        </span>
      ),
    },
    {
      title: t('stok.bakiye_sonrasi'),
      dataIndex: 'bakiye_sonrasi',
      key: 'bakiye_sonrasi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('stok.aciklama'),
      dataIndex: 'aciklama',
      key: 'aciklama',
      render: (v: string) => v || '—',
    },
    {
      title: t('stok.son_hareketler'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      align: 'right',
      render: (v: string) => <span className="sayisal">{dayjs(v).format('DD.MM HH:mm')}</span>,
    },
  ];

  if (malzeme.isPending) {
    return (
      <SayfaKapsayici enGenis={1160}>
        <Skeleton active paragraph={{ rows: 6 }} />
      </SayfaKapsayici>
    );
  }

  if (malzeme.isError || !malzeme.data) {
    return (
      <Result
        status="404"
        title={t('stok.bos')}
        extra={
          <Button type="primary" onClick={() => navigate('/malzemeler')}>
            {t('ortak.geri')}
          </Button>
        }
      />
    );
  }

  const m: Malzeme = malzeme.data;

  const ozetMetrikler: OzetMetrik[] = [
    {
      anahtar: 'mevcut',
      baslik: t('stok.mevcut'),
      deger: m.mevcut_miktar.toLocaleString('tr-TR'),
      birim: m.birim,
      ikon: <GoldOutlined />,
      seri: turev.bakiye.length >= 2 ? turev.bakiye : undefined,
    },
    {
      anahtar: 'kritik',
      baslik: t('stok.kritik_esik'),
      deger: m.kritik_stok.toLocaleString('tr-TR'),
      birim: m.birim,
      ikon: <AlertOutlined />,
    },
    {
      anahtar: 'giris',
      baslik: t('stok.giris'),
      deger: turev.giris.toLocaleString('tr-TR'),
      ikon: <ArrowUpOutlined />,
    },
    {
      anahtar: 'cikis',
      baslik: t('stok.cikis'),
      deger: turev.cikis.toLocaleString('tr-TR'),
      ikon: <ArrowDownOutlined />,
    },
  ];

  return (
    <SayfaKapsayici enGenis={1160}>
      <SayfaBaslik
        baslik={
          <Space size={12} align="center" wrap>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/malzemeler')}
              aria-label={t('ortak.geri')}
            />
            <span className="sayisal">{m.kod}</span>
            <span style={{ color: 'var(--metin-soluk)', fontWeight: 400 }}>{m.ad}</span>
            {m.kritik && (
              <Tag color="red" bordered={false}>
                {t('stok.kritik_rozet')}
              </Tag>
            )}
          </Space>
        }
        sag={
          yazabilir && (
            <Space wrap>
              <Button icon={<EditOutlined />} onClick={() => setDuzenleAcik(true)}>
                {t('stok.duzenle')}
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setHareketAcik(true)}>
                {t('stok.hareket_ekle')}
              </Button>
            </Space>
          )
        }
      />

      <div style={{ marginBottom: 16 }}>
        <OzetSerit metrikler={ozetMetrikler} renk={HAT} />
      </div>

      <div
        className="pano-bento"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}
      >
        <PanelKart baslik={t('stok.seviye')} renk={HAT} sinif="tam-yukseklik">
          <StokSeviyeBar
            mevcut={m.mevcut_miktar}
            kritik={m.kritik_stok}
            min={m.min_stok}
            birim={m.birim}
          />
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '10px 22px',
              marginTop: 18,
              paddingTop: 16,
              borderTop: '1px solid var(--kenarlik)',
            }}
          >
            <span style={{ fontSize: 12.5, color: 'var(--metin-soluk)' }}>
              {t('stok.max')}:{' '}
              <span className="sayisal" style={{ color: 'var(--metin)' }}>
                {m.max_stok ?? '—'}
              </span>
            </span>
            <span style={{ fontSize: 12.5, color: 'var(--metin-soluk)' }}>
              {t('stok.kategori')}:{' '}
              <span style={{ color: 'var(--metin)' }}>{m.kategori || '—'}</span>
            </span>
            <span style={{ fontSize: 12.5, color: 'var(--metin-soluk)' }}>
              {t('stok.durum')}:{' '}
              <span style={{ color: m.aktif ? 'var(--basari)' : 'var(--metin-soluk)' }}>
                {m.aktif ? t('stok.aktif') : t('stok.pasif')}
              </span>
            </span>
          </div>
        </PanelKart>

        <div className="genis">
          <PanelKart baslik={t('stok.bakiye_sonrasi')} renk={HAT} sinif="tam-yukseklik">
            {seriSorgu.isPending ? (
              <Skeleton active paragraph={{ rows: 5 }} />
            ) : turev.bos ? (
              <div className="widget-bos">{t('stok.bos')}</div>
            ) : (
              <EGrafik secenek={trendSecenek} yukseklik={252} />
            )}
          </PanelKart>
        </div>

        <PanelKart baslik={t('stok.analiz_dagilim')} renk={HAT} sinif="tam-yukseklik">
          {seriSorgu.isPending ? (
            <Skeleton active />
          ) : turev.turSeg.length === 0 ? (
            <div className="widget-bos">{t('stok.bos')}</div>
          ) : (
            <>
              <EGrafik secenek={turSecenek} yukseklik={180} />
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px', marginTop: 8 }}>
                {turev.turSeg.map((s) => (
                  <span
                    key={s.ad}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5 }}
                  >
                    <span
                      style={
                        {
                          width: 9,
                          height: 9,
                          borderRadius: 3,
                          background: s.renk,
                        } as CSSProperties
                      }
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

        <div className="genis">
          <PanelKart baslik={t('stok.son_hareketler')} renk={HAT} sinif="tam-yukseklik">
            <SunucuTablo<StokHareketi>
              kolonlar={kolonlar}
              veri={hareketler.data?.veri ?? []}
              meta={hareketler.data?.meta}
              yukleniyor={hareketler.isPending}
              param={param}
              paramDegistir={paramDegistir}
              rowKey="id"
              bosMetin={t('stok.bos')}
            />
          </PanelKart>
        </div>
      </div>

      <MalzemeFormu acik={duzenleAcik} kapat={() => setDuzenleAcik(false)} malzeme={m} />
      <StokHareketFormu malzeme={hareketAcik ? m : null} kapat={() => setHareketAcik(false)} />
    </SayfaKapsayici>
  );
}
