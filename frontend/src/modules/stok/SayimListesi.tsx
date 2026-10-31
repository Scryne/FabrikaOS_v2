/**
 * Sayım oturumları (S25-A): lokasyon başına sayım aç → satırları say → onaya gönder → onay
 * (ayrı izin, sayanla onaylayan farklı). Onayda farklar DELTA olarak uygulanır (ADR-0024 §1).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Form, Input, Modal, Select, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import {
  SAYIM_RENK,
  type Sayim,
  type SayimDurum,
  useDepolar,
  useSayimAc,
  useSayimlar,
} from './depoHooks';

export function SayimListesi() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('stok:yaz'));
  const sayimlar = useSayimlar();
  const depolar = useDepolar();
  const sayimAc = useSayimAc();
  const [acik, setAcik] = useState(false);
  const [form] = Form.useForm();

  const kolonlar: ColumnsType<Sayim> = [
    {
      title: t('sayim.kod'),
      dataIndex: 'kod',
      render: (v: string, s) => (
        <Link to={`/sayimlar/${s.id}`} className="varlik-ad sayisal">
          {v}
        </Link>
      ),
    },
    { title: t('depo.lokasyon'), dataIndex: 'lokasyon_kod' },
    {
      title: t('sayim.durum'),
      dataIndex: 'durum',
      render: (d: SayimDurum) => <Tag color={SAYIM_RENK[d]}>{t(`sayim.durum_${d}`)}</Tag>,
    },
    { title: t('sayim.satir'), key: 'satir', align: 'right', render: (_v, s) => s.satirlar.length },
    {
      title: t('sayim.fark'),
      dataIndex: 'fark_sayisi',
      align: 'right',
      render: (v: number) => <span style={{ color: v > 0 ? 'var(--uyari)' : undefined }}>{v}</span>,
    },
    {
      title: t('sayim.tarih'),
      dataIndex: 'olusturma_tarihi',
      render: (v: string | null) => (v ? new Date(v).toLocaleString('tr-TR') : '—'),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('sayim.baslik')}
        alt={t('sayim.alt')}
        sag={
          yazabilir ? (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                form.resetFields();
                setAcik(true);
              }}
            >
              {t('sayim.yeni')}
            </Button>
          ) : null
        }
      />
      <Card>
        <Table<Sayim>
          rowKey="id"
          columns={kolonlar}
          dataSource={sayimlar.data ?? []}
          loading={sayimlar.isPending}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          scroll={{ x: 640 }}
          onRow={(s) => ({
            onClick: () => navigate(`/sayimlar/${s.id}`),
            style: { cursor: 'pointer' },
          })}
          locale={{
            emptyText: (
              <BosDurum baslik={t('sayim.bos_baslik')} aciklama={t('sayim.bos_aciklama')} />
            ),
          }}
        />
      </Card>
      <Modal
        open={acik}
        title={t('sayim.yeni')}
        okText={t('sayim.ac')}
        confirmLoading={sayimAc.isPending}
        onCancel={() => setAcik(false)}
        onOk={() => form.submit()}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(v: { lokasyon_id: number; aciklama?: string }) =>
            sayimAc.mutate(v, {
              onSuccess: (s) => {
                message.success(t('sayim.acildi', { kod: s.kod }));
                setAcik(false);
                navigate(`/sayimlar/${s.id}`);
              },
            })
          }
        >
          <Form.Item
            name="lokasyon_id"
            label={t('depo.lokasyon')}
            rules={[{ required: true, message: t('sayim.lokasyon_gerekli') }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              options={(depolar.data ?? []).flatMap((d) =>
                d.lokasyonlar.map((l) => ({ value: l.id, label: `${d.kod} / ${l.kod} · ${l.ad}` })),
              )}
            />
          </Form.Item>
          <Form.Item name="aciklama" label={t('depo.aciklama')}>
            <Input maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </SayfaKapsayici>
  );
}
