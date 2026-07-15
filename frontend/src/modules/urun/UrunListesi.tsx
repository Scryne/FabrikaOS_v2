/**
 * Ürün kartları listesi (S24) — sunucu-taraflı tablo + yeni ürün formu + reçete (BOM)
 * düzenleme çekmecesi. Reçetesi olan ürün iş emrine bağlanınca kapanışta BOM patlatma
 * stok tüketir (arka plan bilgisi ``urun.alt`` metninde).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PartitionOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Card, Form, Input, Modal, Select, Switch, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { ReceteCekmecesi } from './ReceteCekmecesi';
import { type Urun, useUrunGuncelle, useUrunler, useUrunOlustur } from './hooks';

function UrunFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm<{ kod: string; ad: string; birim: string; aciklama?: string }>();
  const olustur = useUrunOlustur();

  const gonder = async () => {
    const v = await form.validateFields();
    await olustur.mutateAsync({
      kod: v.kod.trim(),
      ad: v.ad.trim(),
      birim: v.birim,
      aciklama: v.aciklama?.trim() ?? '',
    });
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      title={t('urun.yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      confirmLoading={olustur.isPending}
      onOk={() => void gonder()}
      onCancel={() => {
        form.resetFields();
        kapat();
      }}
      destroyOnHidden
      maskClosable={false}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        preserve={false}
        initialValues={{ birim: 'adet' }}
      >
        <Form.Item name="kod" label={t('urun.kod')} rules={[{ required: true }, { max: 50 }]}>
          <Input placeholder={t('urun.kod_ipucu')} autoFocus />
        </Form.Item>
        <Form.Item name="ad" label={t('urun.ad')} rules={[{ required: true }, { max: 200 }]}>
          <Input />
        </Form.Item>
        <Form.Item name="birim" label={t('urun.birim')} rules={[{ required: true }]}>
          <Select options={['adet', 'kg', 'lt', 'm', 'm2'].map((b) => ({ value: b, label: b }))} />
        </Form.Item>
        <Form.Item name="aciklama" label={t('urun.aciklama')}>
          <Input.TextArea rows={2} maxLength={1000} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function UrunListesi() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('uretim:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useUrunler(param);
  const guncelle = useUrunGuncelle();
  const [formAcik, setFormAcik] = useState(false);
  const [receteUrunu, setReceteUrunu] = useState<Urun | null>(null);

  const kolonlar: ColumnsType<Urun> = [
    {
      title: t('urun.kod'),
      dataIndex: 'kod',
      key: 'kod',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('urun.ad'), dataIndex: 'ad', key: 'ad', sorter: true },
    {
      title: t('urun.birim'),
      dataIndex: 'birim',
      key: 'birim',
      width: 90,
      render: (v: string) => <Tag>{v}</Tag>,
    },
    { title: t('urun.aciklama'), dataIndex: 'aciklama', key: 'aciklama', ellipsis: true },
    {
      title: t('urun.aktif'),
      dataIndex: 'aktif',
      key: 'aktif',
      width: 90,
      render: (aktif: boolean, kayit) =>
        yazabilir ? (
          <Switch
            size="small"
            checked={aktif}
            loading={guncelle.isPending && guncelle.variables?.id === kayit.id}
            onChange={(deger) => guncelle.mutate({ id: kayit.id, govde: { aktif: deger } })}
            aria-label={t('urun.aktif')}
          />
        ) : (
          <Tag color={aktif ? 'green' : 'default'}>{aktif ? t('urun.aktif') : t('urun.pasif')}</Tag>
        ),
    },
    {
      key: 'recete',
      width: 130,
      render: (_, kayit) => (
        <Button size="small" icon={<PartitionOutlined />} onClick={() => setReceteUrunu(kayit)}>
          {t('urun.recete')}
        </Button>
      ),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.urunler')}
        alt={t('urun.alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('urun.yeni')}
            </Button>
          )
        }
      />
      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Urun>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('urun.ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('urun.bos')}
          araclar={
            <Select
              allowClear
              placeholder={t('urun.aktif')}
              style={{ width: 140 }}
              value={param.filtreler?.aktif as boolean | undefined}
              onChange={(v) => paramDegistir({ filtreler: { aktif: v } })}
              options={[
                { value: true, label: t('urun.aktif') },
                { value: false, label: t('urun.pasif') },
              ]}
            />
          }
        />
      </Card>
      <UrunFormu acik={formAcik} kapat={() => setFormAcik(false)} />
      <ReceteCekmecesi urun={receteUrunu} kapat={() => setReceteUrunu(null)} />
    </SayfaKapsayici>
  );
}
