/**
 * Acil durum tatbikatları (S26-B, ADR-0044): tür, tarih, katılım, tahliye süresi, bulgular ve
 * planlanan sonraki tatbikat. Özet şeridi son tatbikattan bu yana geçen günü ve en yakın planı öne
 * çıkarır; sonraki tarih bu tatbikattan sonra olmalı (sunucu 422).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertOutlined, PlusOutlined } from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  DatePicker,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Table,
  Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import { type Tatbikat, useTatbikatlar, useTatbikatOlustur } from './olgunlukHooks';

const TURLER = ['yangin', 'deprem', 'tahliye', 'kimyasal', 'ilk_yardim', 'diger'];
const tarih = (v: string | null | undefined) => (v ? dayjs(v).format('DD.MM.YYYY') : '—');
const sure = (sn: number | null | undefined) =>
  sn === null || sn === undefined
    ? '—'
    : `${Math.floor(sn / 60)}:${String(sn % 60).padStart(2, '0')}`;

function TatbikatFormu({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const olustur = useTatbikatOlustur();
  const [form] = Form.useForm();
  const tarihDegeri = Form.useWatch('tarih', form) as Dayjs | undefined;

  const gonder = async () => {
    const v = await form.validateFields();
    const dk = (v.tahliye_dk as number | undefined) ?? null;
    const sn = (v.tahliye_sn as number | undefined) ?? 0;
    const s = await olustur.mutateAsync({
      tur: v.tur,
      tarih: (v.tarih as Dayjs).format('YYYY-MM-DD'),
      yer: v.yer ?? '',
      katilimci_sayisi: v.katilimci_sayisi ?? 0,
      tahliye_suresi_sn: dk === null && !v.tahliye_sn ? null : (dk ?? 0) * 60 + sn,
      bulgular: v.bulgular ?? '',
      sonraki_tarih: v.sonraki_tarih ? (v.sonraki_tarih as Dayjs).format('YYYY-MM-DD') : null,
    });
    message.success(t('isg26.tatbikat_kaydedildi', { kod: s.kod }));
    form.resetFields();
    kapat();
  };

  return (
    <Modal
      open={acik}
      width={640}
      title={t('isg26.tatbikat_yeni')}
      okText={t('ortak.kaydet')}
      cancelText={t('ortak.iptal')}
      onCancel={kapat}
      onOk={() => void gonder()}
      confirmLoading={olustur.isPending}
      destroyOnHidden
      mask={{ closable: false }}
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        initialValues={{ tur: 'yangin', tarih: dayjs() }}
      >
        <div className="form-iki-sutun">
          <Form.Item name="tur" label={t('isg26.tatbikat_tur')} rules={[{ required: true }]}>
            <Select options={TURLER.map((x) => ({ value: x, label: t(`isg26.tatbikat_${x}`) }))} />
          </Form.Item>
          <Form.Item name="tarih" label={t('isg26.tarih')} rules={[{ required: true }]}>
            <DatePicker format="DD.MM.YYYY" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="yer" label={t('isg26.yer')}>
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item name="katilimci_sayisi" label={t('isg26.katilimci')}>
            <InputNumber min={0} max={100000} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label={t('isg26.tahliye_suresi')} tooltip={t('isg26.tahliye_ipucu')}>
            <div className="isg26-sure">
              <Form.Item name="tahliye_dk" noStyle>
                <InputNumber min={0} max={1440} suffix={t('isg26.dk')} aria-label={t('isg26.dk')} />
              </Form.Item>
              <Form.Item name="tahliye_sn" noStyle>
                <InputNumber min={0} max={59} suffix={t('isg26.sn')} aria-label={t('isg26.sn')} />
              </Form.Item>
            </div>
          </Form.Item>
          <Form.Item name="sonraki_tarih" label={t('isg26.sonraki_tarih')}>
            <DatePicker
              format="DD.MM.YYYY"
              style={{ width: '100%' }}
              disabledDate={(d) => !!tarihDegeri && !d.isAfter(tarihDegeri, 'day')}
            />
          </Form.Item>
        </div>
        <Form.Item name="bulgular" label={t('isg26.bulgular')}>
          <Input.TextArea rows={3} maxLength={4000} placeholder={t('isg26.bulgular_ornek')} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

export function Tatbikatlar() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isg:yaz'));
  const { data, isPending } = useTatbikatlar();
  const [formAcik, setFormAcik] = useState(false);
  const liste = data ?? [];
  const bugun = dayjs().startOf('day');
  const son = liste[0];
  const planlar = liste
    .map((x) => x.sonraki_tarih)
    .filter((x): x is string => !!x)
    .sort();
  const yakinPlan = planlar.find((x) => !dayjs(x).isBefore(bugun));
  const gecikmis = planlar.filter((x) => dayjs(x).isBefore(bugun)).length;

  const kolonlar: ColumnsType<Tatbikat> = [
    {
      title: t('isg26.tatbikat'),
      dataIndex: 'tur',
      render: (_v, x) => (
        <span>
          <span className="varlik-ad">{t(`isg26.tatbikat_${x.tur}`)}</span>
          <span className="varlik-alt sayisal" style={{ display: 'block' }}>
            {x.kod}
          </span>
        </span>
      ),
    },
    {
      title: t('isg26.tarih'),
      dataIndex: 'tarih',
      render: (v: string) => <span className="sayisal">{tarih(v)}</span>,
    },
    {
      title: t('isg26.yer'),
      dataIndex: 'yer',
      responsive: ['md'],
      render: (v: string) => v || '—',
    },
    {
      title: t('isg26.katilimci'),
      dataIndex: 'katilimci_sayisi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('isg26.tahliye_suresi'),
      dataIndex: 'tahliye_suresi_sn',
      align: 'right',
      render: (v: number | null) => <span className="sayisal">{sure(v)}</span>,
    },
    {
      title: t('isg26.sonraki_tarih'),
      dataIndex: 'sonraki_tarih',
      render: (v: string | null) =>
        v ? (
          <Tag color={dayjs(v).isBefore(bugun) ? 'red' : 'blue'} variant="filled">
            {tarih(v)}
          </Tag>
        ) : (
          '—'
        ),
    },
    {
      title: t('isg26.bulgular'),
      dataIndex: 'bulgular',
      responsive: ['lg'],
      ellipsis: true,
      render: (v: string) => v || '—',
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('isg26.tatbikat_baslik')}
        alt={t('isg26.tatbikat_alt')}
        sag={
          yazabilir ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('isg26.tatbikat_yeni')}
            </Button>
          ) : null
        }
      />
      <OzetSerit
        yukleniyor={isPending}
        metrikler={[
          {
            anahtar: 'son',
            baslik: t('isg26.son_tatbikat'),
            deger: son ? String(bugun.diff(dayjs(son.tarih), 'day')) : '—',
            birim: son ? t('isg26.gun_once') : undefined,
            ikon: <AlertOutlined />,
          },
          {
            anahtar: 'plan',
            baslik: t('isg26.yakin_plan'),
            deger: yakinPlan ? tarih(yakinPlan) : '—',
          },
          {
            anahtar: 'gecikmis',
            baslik: t('isg26.gecikmis_plan'),
            deger: String(gecikmis),
            olumlu: gecikmis === 0,
          },
          { anahtar: 'toplam', baslik: t('isg26.toplam_tatbikat'), deger: String(liste.length) },
        ]}
      />
      <Card style={{ marginTop: 16 }}>
        <Table<Tatbikat>
          rowKey="id"
          loading={isPending}
          columns={kolonlar}
          dataSource={liste}
          scroll={{ x: 'max-content' }}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          locale={{ emptyText: <Empty description={t('isg26.tatbikat_bos')} /> }}
        />
      </Card>
      <TatbikatFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
