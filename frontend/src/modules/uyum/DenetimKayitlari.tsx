/**
 * Denetim kayıtları görüntüleyicisi (S23 / ADR-0022) — kim, ne, ne zaman, nereden.
 *
 * Append-only bir defterdir: ekranda hiçbir düzenleme/silme aksiyonu YOKTUR (bilinçli).
 * Filtreler sunucu tarafında uygulanır (kullanıcı e-postası / kaynak / eylem / tarih
 * aralığı); satır detayı çekmecede ham ``detay`` JSON'ı ile gösterilir.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FileSearchOutlined } from '@ant-design/icons';
import { Descriptions, Drawer, Select, Space, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DatePicker } from 'antd';
import dayjs, { type Dayjs } from 'dayjs';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';

import { type DenetimKaydi, useDenetimKayitlari, useDenetimKaynaklari } from './hooks';

/** Yazma eylemleri vurgulanır; okuma/oturum eylemleri sakin kalır. */
const EYLEM_RENK: Record<string, string> = {
  olustur: 'green',
  guncelle: 'blue',
  sil: 'red',
  giris: 'default',
  sso_giris: 'default',
  cikis: 'default',
  onayla: 'green',
  reddet: 'red',
  anonimlestir: 'red',
  kvkk_ihrac: 'purple',
  parola_degistir: 'orange',
  '2fa_etkinlestir': 'green',
  '2fa_kapat': 'orange',
};

export function DenetimKayitlari() {
  const { t } = useTranslation();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending } = useDenetimKayitlari(param);
  const { data: kaynaklar } = useDenetimKaynaklari();
  const [secili, setSecili] = useState<DenetimKaydi | null>(null);

  const kolonlar: ColumnsType<DenetimKaydi> = [
    {
      title: t('uyum.zaman'),
      dataIndex: 'olusturma_tarihi',
      width: 180,
      render: (deger: string) => (
        <span className="sayisal">{dayjs(deger).format('DD.MM.YYYY HH:mm:ss')}</span>
      ),
    },
    {
      title: t('uyum.kullanici'),
      dataIndex: 'kullanici_eposta',
      render: (eposta: string | null) =>
        eposta ?? <Typography.Text type="secondary">—</Typography.Text>,
    },
    {
      title: t('uyum.eylem'),
      dataIndex: 'eylem',
      width: 160,
      render: (eylem: string) => <Tag color={EYLEM_RENK[eylem] ?? 'default'}>{eylem}</Tag>,
    },
    {
      title: t('uyum.kaynak'),
      dataIndex: 'kaynak',
      width: 150,
    },
    {
      title: t('uyum.kaynak_id'),
      dataIndex: 'kaynak_id',
      width: 120,
      render: (deger: string | null) => <span className="sayisal">{deger ?? '—'}</span>,
    },
    {
      title: t('uyum.ip'),
      dataIndex: 'ip_adresi',
      width: 140,
      render: (deger: string | null) => <span className="sayisal">{deger ?? '—'}</span>,
    },
  ];

  function tarihAraligi(aralik: [Dayjs | null, Dayjs | null] | null) {
    paramDegistir({
      filtreler: {
        baslangic: aralik?.[0] ? aralik[0].startOf('day').toISOString() : undefined,
        bitis: aralik?.[1] ? aralik[1].endOf('day').toISOString() : undefined,
      },
    });
  }

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('uyum.denetim_baslik')} alt={t('uyum.denetim_aciklama')} />

      <SunucuTablo<DenetimKaydi>
        kolonlar={kolonlar}
        veri={data?.veri ?? []}
        meta={data?.meta}
        yukleniyor={isPending}
        param={param}
        paramDegistir={paramDegistir}
        rowKey="id"
        aramaYer={t('uyum.kullanici_ara')}
        bosMetin={t('uyum.denetim_bos')}
        onRow={(kayit) => ({ onClick: () => setSecili(kayit) })}
        araclar={
          <Space wrap>
            <Select
              allowClear
              placeholder={t('uyum.kaynak')}
              style={{ minWidth: 170 }}
              options={(kaynaklar ?? []).map((k) => ({ value: k, label: k }))}
              onChange={(deger?: string) => paramDegistir({ filtreler: { kaynak: deger } })}
            />
            <DatePicker.RangePicker
              onChange={(aralik) => tarihAraligi(aralik as [Dayjs | null, Dayjs | null] | null)}
              placeholder={[t('uyum.baslangic'), t('uyum.bitis')]}
            />
          </Space>
        }
      />

      <Drawer
        open={secili !== null}
        onClose={() => setSecili(null)}
        width={520}
        title={
          <Space>
            <FileSearchOutlined />
            {t('uyum.kayit_detay')}
          </Space>
        }
        destroyOnHidden
      >
        {secili && (
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label={t('uyum.zaman')}>
                <span className="sayisal">
                  {dayjs(secili.olusturma_tarihi).format('DD.MM.YYYY HH:mm:ss')}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label={t('uyum.kullanici')}>
                {secili.kullanici_eposta ?? '—'}
              </Descriptions.Item>
              <Descriptions.Item label={t('uyum.eylem')}>
                <Tag color={EYLEM_RENK[secili.eylem] ?? 'default'}>{secili.eylem}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label={t('uyum.kaynak')}>
                {secili.kaynak}
                {secili.kaynak_id ? ` #${secili.kaynak_id}` : ''}
              </Descriptions.Item>
              <Descriptions.Item label={t('uyum.ip')}>
                <span className="sayisal">{secili.ip_adresi ?? '—'}</span>
              </Descriptions.Item>
              <Descriptions.Item label={t('uyum.istek_id')}>
                <span className="sayisal">{secili.request_id ?? '—'}</span>
              </Descriptions.Item>
            </Descriptions>

            <div>
              <Typography.Text strong>{t('uyum.detay')}</Typography.Text>
              <pre
                className="sayisal"
                style={{
                  marginTop: 8,
                  padding: 12,
                  borderRadius: 8,
                  border: '1px solid var(--kenarlik)',
                  background: 'var(--yuzey-ust)',
                  fontSize: 12,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}
              >
                {secili.detay ? JSON.stringify(secili.detay, null, 2) : '—'}
              </pre>
            </div>
          </Space>
        )}
      </Drawer>
    </SayfaKapsayici>
  );
}
