/**
 * Üst bar bildirim zili — okunmamış rozet + açılır son bildirimler paneli (S-VB).
 *
 * Rozet `GET /bildirimler/ozet`ten beslenir; `bildirim.yeni` WS sinyali olayIsle'de
 * özeti geçersizleştirir → sayaç yenilemesiz artar. Satıra tıklama okundu işaretler
 * ve (derin-bağlantı verisi varsa) ilgili kayda gider.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { BellOutlined, CheckOutlined, SettingOutlined } from '@ant-design/icons';
import { Badge, Button, Empty, Popover, Spin } from 'antd';

import type { Bildirim } from './hooks';
import { useBildirimOkundu, useBildirimOzet, useTumunuOkundu } from './hooks';

/** Derin-bağlantı: bildirim verisindeki kaynak türü → uygulama rotası. */
const KAYNAK_ROTASI: Record<string, (id: number | null) => string> = {
  malzeme: (id) => (id != null ? `/malzemeler/${id}` : '/stok/kritik'),
  sozlesme: () => '/sozlesmeler',
  makine: (id) => (id != null ? `/makineler/${id}` : '/makineler'),
  rapor: () => '/raporlar',
  ariza: () => '/makineler',
  duyuru: () => '/duyurular',
  is_emri: () => '/is-emirleri',
  talep: () => '/talepler',
};

const ONEM_RENGI: Record<string, string> = {
  bilgi: 'var(--mavi)',
  uyari: 'var(--uyari)',
  kritik: 'var(--hata)',
};

function goreliZaman(iso: string, dil: string): string {
  const fark = (new Date(iso).getTime() - Date.now()) / 1000;
  const birimler: [number, Intl.RelativeTimeFormatUnit][] = [
    [60, 'second'],
    [60, 'minute'],
    [24, 'hour'],
    [7, 'day'],
  ];
  let deger = fark;
  let birim: Intl.RelativeTimeFormatUnit = 'second';
  for (const [esik, b] of birimler) {
    birim = b;
    if (Math.abs(deger) < esik) break;
    deger /= esik;
  }
  return new Intl.RelativeTimeFormat(dil, { numeric: 'auto' }).format(Math.round(deger), birim);
}

function BildirimSatiri({ bildirim, tikla }: { bildirim: Bildirim; tikla: (b: Bildirim) => void }) {
  const { i18n } = useTranslation();
  return (
    <button type="button" className="bildirim-satir" onClick={() => tikla(bildirim)}>
      <span
        className="durum-nokta"
        aria-hidden="true"
        style={{
          background: ONEM_RENGI[bildirim.onem] ?? 'var(--mavi)',
          opacity: bildirim.okundu ? 0.35 : 1,
          marginTop: 6,
          flexShrink: 0,
        }}
      />
      <span style={{ minWidth: 0, flex: 1, textAlign: 'left' }}>
        <span
          style={{
            display: 'block',
            fontSize: 13,
            fontWeight: bildirim.okundu ? 400 : 600,
            color: bildirim.okundu ? 'var(--metin-soluk)' : 'var(--metin)',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {bildirim.baslik}
        </span>
        <span style={{ display: 'block', fontSize: 11.5, color: 'var(--metin-soluk)' }}>
          {goreliZaman(bildirim.olusturma_tarihi, i18n.language)}
        </span>
      </span>
    </button>
  );
}

export function BildirimZili() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [acik, setAcik] = useState(false);
  const ozet = useBildirimOzet();
  const okundu = useBildirimOkundu();
  const tumunuOkundu = useTumunuOkundu();

  const tikla = (b: Bildirim) => {
    if (!b.okundu) okundu.mutate(b.id);
    setAcik(false);
    const kaynakTur = typeof b.veri.kaynak_tur === 'string' ? b.veri.kaynak_tur : '';
    const kaynakId = typeof b.veri.kaynak_id === 'number' ? b.veri.kaynak_id : null;
    const rota = KAYNAK_ROTASI[kaynakTur];
    if (rota) navigate(rota(kaynakId));
  };

  const icerik = (
    <div style={{ width: 340 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '2px 4px 8px',
          borderBottom: '1px solid var(--kenarlik)',
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 13 }}>{t('ortak.bildirimler')}</span>
        <span style={{ display: 'flex', gap: 4 }}>
          <Button
            type="text"
            size="small"
            icon={<CheckOutlined />}
            disabled={(ozet.data?.okunmamis ?? 0) === 0}
            onClick={() => tumunuOkundu.mutate()}
          >
            {t('bildirim.tumunu_okundu')}
          </Button>
          <Button
            type="text"
            size="small"
            icon={<SettingOutlined />}
            aria-label={t('bildirim.tercihler')}
            onClick={() => {
              setAcik(false);
              navigate('/bildirim-tercihleri');
            }}
          />
        </span>
      </div>
      {ozet.isLoading ? (
        <div style={{ display: 'grid', placeItems: 'center', padding: 24 }}>
          <Spin size="small" />
        </div>
      ) : (ozet.data?.son.length ?? 0) === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={t('bildirim.bos')}
          style={{ margin: '20px 0' }}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', paddingTop: 4 }}>
          {ozet.data?.son.map((b) => (
            <BildirimSatiri key={b.id} bildirim={b} tikla={tikla} />
          ))}
        </div>
      )}
    </div>
  );

  return (
    <Popover
      content={icerik}
      trigger="click"
      placement="bottomRight"
      open={acik}
      onOpenChange={setAcik}
      arrow={false}
    >
      <button type="button" className="bar-dugme" aria-label={t('ortak.bildirimler')}>
        <Badge count={ozet.data?.okunmamis ?? 0} size="small" offset={[0, 2]} color="var(--mavi)">
          <BellOutlined style={{ fontSize: 17, color: 'inherit' }} />
        </Badge>
      </button>
    </Popover>
  );
}
