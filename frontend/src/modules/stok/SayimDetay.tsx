/**
 * Sayım detayı (S25-A): telefonda sayım için büyük dokunma hedefli satır girişi; fark sütunu
 * semantik renkli (eksik kırmızı, fazla yeşil). Sistem miktarı satır ilk yazıldığı anın
 * görüntüsüdür; onayda fark o andan bu yana yapılan hareketlerin ÜSTÜNE eklenir (ADR-0024 §1).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { CheckOutlined, SendOutlined, StopOutlined } from '@ant-design/icons';
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  InputNumber,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import {
  SAYIM_RENK,
  type SayimSatiri,
  useMalzemeSecenekleri,
  useSayim,
  useSayimAksiyon,
  useSayimSatirYaz,
} from './depoHooks';

export function SayimDetay() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const id = Number(useParams().id);
  const yazabilir = useAuthStore((s) => s.izinVar('stok:yaz'));
  const onaylayabilir = useAuthStore((s) => s.izinVar('stok:duzeltme'));
  const sayim = useSayim(id);
  const malzemeler = useMalzemeSecenekleri();
  const satirYaz = useSayimSatirYaz(id);
  const aksiyon = useSayimAksiyon(id);
  const [form] = Form.useForm();
  const [secili, setSecili] = useState<number | undefined>();

  const s = sayim.data;
  const acik = s?.durum === 'acik';

  const kolonlar: ColumnsType<SayimSatiri> = [
    {
      title: t('depo.malzeme'),
      key: 'm',
      render: (_v, r) => (
        <span>
          <span className="varlik-ad">{r.malzeme_ad}</span>
          <span className="varlik-alt sayisal" style={{ display: 'block' }}>
            {r.malzeme_kod}
            {r.lot_no ? ` · ${r.lot_no}` : ''}
          </span>
        </span>
      ),
    },
    {
      title: t('sayim.sistem'),
      dataIndex: 'sistem_miktari',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('sayim.sayilan'),
      dataIndex: 'sayilan_miktar',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('sayim.fark'),
      dataIndex: 'fark',
      align: 'right',
      render: (v: number) => (
        <span
          className="sayisal"
          style={{
            fontWeight: 600,
            color: v < 0 ? 'var(--hata)' : v > 0 ? 'var(--basari)' : undefined,
          }}
        >
          {v > 0 ? `+${v}` : v}
        </span>
      ),
    },
  ];

  if (!sayim.isPending && !s) {
    return (
      <SayfaKapsayici>
        <BosDurum
          baslik={t('sayim.bulunamadi')}
          aksiyon={<Link to="/sayimlar">{t('sayim.listeye_don')}</Link>}
        />
      </SayfaKapsayici>
    );
  }

  return (
    <SayfaKapsayici enGenis={960}>
      <SayfaBaslik
        baslik={
          <Space wrap>
            <span className="sayisal">{s?.kod ?? '…'}</span>
            {s && <Tag color={SAYIM_RENK[s.durum]}>{t(`sayim.durum_${s.durum}`)}</Tag>}
          </Space>
        }
        alt={s ? `${t('depo.lokasyon')}: ${s.lokasyon_kod ?? '—'}` : undefined}
        sag={<Link to="/sayimlar">{t('sayim.listeye_don')}</Link>}
      />

      {s?.durum === 'onay_bekliyor' && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }} title={t('sayim.delta_bilgi')} />
      )}

      {acik && yazabilir && (
        <Card title={t('sayim.satir_ekle')} style={{ marginBottom: 16 }}>
          <Form
            form={form}
            layout="vertical"
            onFinish={(v: { malzeme_id: number; sayilan_miktar: number }) =>
              satirYaz.mutate(v, {
                onSuccess: () => {
                  message.success(t('sayim.satir_kaydedildi'));
                  form.resetFields();
                  setSecili(undefined);
                },
              })
            }
          >
            <Form.Item
              name="malzeme_id"
              label={t('depo.malzeme')}
              rules={[{ required: true, message: t('sayim.malzeme_gerekli') }]}
            >
              <Select
                size="large"
                showSearch
                optionFilterProp="label"
                loading={malzemeler.isPending}
                onChange={(v: number) => setSecili(v)}
                options={(malzemeler.data ?? []).map((m) => ({
                  value: m.id,
                  label: `${m.kod} · ${m.ad}`,
                }))}
              />
            </Form.Item>
            <Form.Item
              name="sayilan_miktar"
              label={t('sayim.sayilan')}
              rules={[{ required: true, message: t('sayim.miktar_gerekli') }]}
            >
              <InputNumber
                size="large"
                min={0}
                inputMode="decimal"
                style={{ width: '100%' }}
                suffix={(malzemeler.data ?? []).find((m) => m.id === secili)?.birim}
              />
            </Form.Item>
            <Button
              type="primary"
              size="large"
              htmlType="submit"
              block
              loading={satirYaz.isPending}
            >
              {t('sayim.satiri_kaydet')}
            </Button>
          </Form>
        </Card>
      )}

      <Card title={t('sayim.satirlar')}>
        <Table<SayimSatiri>
          rowKey="id"
          columns={kolonlar}
          dataSource={s?.satirlar ?? []}
          loading={sayim.isPending}
          pagination={false}
          size="small"
          tableLayout="fixed"
          locale={{ emptyText: <BosDurum baslik={t('sayim.satir_yok')} /> }}
        />
        <Space wrap style={{ marginTop: 16 }}>
          {acik && yazabilir && (
            <Button
              type="primary"
              icon={<SendOutlined />}
              disabled={(s?.satirlar.length ?? 0) === 0}
              loading={aksiyon.isPending}
              onClick={() =>
                aksiyon.mutate('gonder', {
                  onSuccess: () => message.success(t('sayim.gonderildi')),
                })
              }
            >
              {t('sayim.onaya_gonder')}
            </Button>
          )}
          {s?.durum === 'onay_bekliyor' && onaylayabilir && (
            <Popconfirm
              title={t('sayim.onay_soru', { sayi: s.fark_sayisi })}
              okText={t('sayim.onayla')}
              cancelText={t('sayim.vazgec')}
              onConfirm={() =>
                aksiyon.mutate('onayla', { onSuccess: () => message.success(t('sayim.onaylandi')) })
              }
            >
              <Button type="primary" icon={<CheckOutlined />} loading={aksiyon.isPending}>
                {t('sayim.onayla')}
              </Button>
            </Popconfirm>
          )}
          {(s?.durum === 'acik' || s?.durum === 'onay_bekliyor') && yazabilir && (
            <Popconfirm
              title={t('sayim.iptal_soru')}
              okText={t('sayim.iptal')}
              cancelText={t('sayim.vazgec')}
              onConfirm={() => aksiyon.mutate('iptal')}
            >
              <Button danger icon={<StopOutlined />}>
                {t('sayim.iptal')}
              </Button>
            </Popconfirm>
          )}
        </Space>
      </Card>
    </SayfaKapsayici>
  );
}
