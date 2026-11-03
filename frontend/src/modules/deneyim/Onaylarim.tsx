/**
 * Onaylarım (S27-A, ADR-0045): kullanıcının onaylayabileceği bekleyen işler tek listede —
 * satınalma talebi, izin talebi, fazla mesai, sayım farkı. Her satırın onay/red düğmesi modülün
 * kendi ucuna gider; yetki ve görev ayrımı modülde de denetlenir (bu ekran yalnız toplar).
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { CheckOutlined, CloseOutlined, InboxOutlined } from '@ant-design/icons';
import { Alert, Button, Card, Empty, Input, Modal, Segmented, Space, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';

import { type OnayKalemi, useOnayEylemi, useOnayKutusu } from './hooks';

// Etiket metni koyu zeminde AA kontrastlı açık tonlar (antd'nin hazır mor/mavi etiketleri 3.4:1).
const TUR_RENK: Record<string, string> = {
  satinalma_talebi: '#7fa2fb',
  izin_talebi: '#b49cf7',
  fazla_mesai: '#f6b84b',
  sayim: '#67cdf9',
  fatura: '#bef264',
};

export function Onaylarim() {
  const { t } = useTranslation();
  const { data, isPending, isError } = useOnayKutusu();
  const eylem = useOnayEylemi();
  const [tur, setTur] = useState<string>('hepsi');
  const [red, setRed] = useState<OnayKalemi | null>(null);
  const [neden, setNeden] = useState('');

  const kalemler = useMemo(() => data?.kalemler ?? [], [data]);
  const sayac = useMemo(() => {
    const m: Record<string, number> = {};
    for (const k of kalemler) m[k.tur] = (m[k.tur] ?? 0) + 1;
    return m;
  }, [kalemler]);
  const gorunen = tur === 'hepsi' ? kalemler : kalemler.filter((k) => k.tur === tur);
  const bekliyor = (k: OnayKalemi) =>
    eylem.isPending && eylem.variables?.kalem.tur === k.tur && eylem.variables.kalem.id === k.id;

  const kolonlar: ColumnsType<OnayKalemi> = [
    {
      title: t('onay.is'),
      key: 'is',
      render: (_v, k) => (
        <span>
          <Tag
            variant="filled"
            style={{
              color: TUR_RENK[k.tur],
              background: `color-mix(in srgb, ${TUR_RENK[k.tur]} 14%, transparent)`,
            }}
          >
            {t(`onay.tur_${k.tur}`)}
          </Tag>
          <Link to={k.detay_yolu} className="varlik-ad">
            {k.baslik}
          </Link>
          <span className="varlik-alt sayisal" style={{ display: 'block' }}>
            {k.kod}
            {k.ozet ? ` · ${k.ozet}` : ''}
          </span>
        </span>
      ),
    },
    {
      title: t('onay.talep_eden'),
      dataIndex: 'talep_eden',
      responsive: ['md'],
      render: (v: string | null) => v ?? '—',
    },
    {
      title: t('onay.bekliyor'),
      dataIndex: 'tarih',
      responsive: ['sm'],
      render: (v: string) => (
        <span className="sayisal" title={dayjs(v).format('DD.MM.YYYY HH:mm')}>
          {t('onay.gun', { gun: Math.max(dayjs().diff(dayjs(v), 'day'), 0) })}
        </span>
      ),
    },
    {
      title: '',
      key: 'eylem',
      align: 'right',
      render: (_v, k) => (
        <Space size={6} wrap>
          <Button
            type="primary"
            size="small"
            icon={<CheckOutlined />}
            loading={bekliyor(k) && eylem.variables?.eylem === 'onay'}
            disabled={eylem.isPending}
            onClick={() => eylem.mutate({ kalem: k, eylem: 'onay' })}
            aria-label={`${t('onay.onayla')}: ${k.kod}`}
          >
            {t('onay.onayla')}
          </Button>
          {k.red_yolu && (
            <Button
              size="small"
              danger
              icon={<CloseOutlined />}
              disabled={eylem.isPending}
              onClick={() => {
                setNeden('');
                setRed(k);
              }}
              aria-label={`${t('onay.reddet')}: ${k.kod}`}
            >
              {t('onay.reddet')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  const nedenEksik = !!red?.red_gerekce_zorunlu && neden.trim().length === 0;

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('onay.baslik')} alt={t('onay.alt')} />
      <OzetSerit
        yukleniyor={isPending}
        metrikler={[
          {
            anahtar: 'toplam',
            baslik: t('onay.toplam'),
            deger: String(kalemler.length),
            ikon: <InboxOutlined />,
          },
          ...['satinalma_talebi', 'izin_talebi', 'fazla_mesai', 'sayim', 'fatura'].map((x) => ({
            anahtar: x,
            baslik: t(`onay.tur_${x}`),
            deger: String(sayac[x] ?? 0),
          })),
        ]}
      />
      {(data?.kendi_kayitlarim ?? 0) > 0 && (
        <Alert
          type="info"
          showIcon
          style={{ marginTop: 16 }}
          title={t('onay.kendi_kayit', { adet: data?.kendi_kayitlarim })}
        />
      )}
      <Card style={{ marginTop: 16 }}>
        <Segmented
          value={tur}
          onChange={(v) => setTur(String(v))}
          style={{ marginBottom: 12, maxWidth: '100%', overflowX: 'auto' }}
          options={[
            { value: 'hepsi', label: `${t('onay.hepsi')} (${kalemler.length})` },
            ...Object.keys(sayac).map((x) => ({
              value: x,
              label: `${t(`onay.tur_${x}`)} (${sayac[x]})`,
            })),
          ]}
        />
        <Table<OnayKalemi>
          rowKey={(k) => `${k.tur}-${k.id}`}
          columns={kolonlar}
          dataSource={gorunen}
          loading={isPending}
          pagination={{ pageSize: 25, hideOnSinglePage: true }}
          scroll={{ x: 'max-content' }}
          locale={{
            emptyText: (
              <Empty
                description={isError ? t('ortak.hata_baslik') : t('onay.bos')}
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            ),
          }}
        />
      </Card>
      <Modal
        open={red !== null}
        title={red ? `${t('onay.reddet')}: ${red.kod}` : ''}
        okText={t('onay.reddet')}
        okButtonProps={{ danger: true, disabled: nedenEksik, loading: eylem.isPending }}
        cancelText={t('ortak.vazgec')}
        onCancel={() => setRed(null)}
        onOk={() =>
          red &&
          eylem.mutate(
            { kalem: red, eylem: 'red', neden: neden.trim() },
            { onSuccess: () => setRed(null) },
          )
        }
        destroyOnHidden
      >
        <label htmlFor="red-nedeni" className="varlik-alt" style={{ display: 'block' }}>
          {red?.red_gerekce_zorunlu ? t('onay.neden_zorunlu') : t('onay.neden_istege')}
        </label>
        <Input.TextArea
          id="red-nedeni"
          rows={3}
          maxLength={500}
          value={neden}
          onChange={(e) => setNeden(e.target.value)}
          style={{ marginTop: 6 }}
        />
      </Modal>
    </SayfaKapsayici>
  );
}
