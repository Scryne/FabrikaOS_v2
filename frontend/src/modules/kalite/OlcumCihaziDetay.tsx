/** Ölçüm cihazı detayı (S26-A): künye, geçerlilik, kalibrasyon geçmişi, yeni kalibrasyon kaydı. */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { PlusOutlined } from '@ant-design/icons';
import {
  Alert,
  App,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  Modal,
  Select,
  Table,
  Tag,
} from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import {
  type Gecerlilik,
  GECERLILIK_RENK,
  type Kalibrasyon,
  useCihaz,
  useKalibrasyonEkle,
} from './spcHooks';

const SONUC_RENK: Record<string, string> = { uygun: 'green', ayarlandi: 'blue', uygunsuz: 'red' };

export function OlcumCihaziDetay() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const id = Number(useParams().id);
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const cihaz = useCihaz(id);
  const ekle = useKalibrasyonEkle(id);
  const [acik, setAcik] = useState(false);
  const c = cihaz.data;

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={c ? `${c.kod} · ${c.ad}` : t('spc.cihaz')}
        alt={<Link to="/olcum-cihazlari">{t('spc.cihazlar_baslik')}</Link>}
        sag={
          yazabilir && c ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAcik(true)}>
              {t('spc.kalibrasyon_ekle')}
            </Button>
          ) : null
        }
      />
      {c &&
        (c.gecerlilik === 'gecmis' ||
          c.gecerlilik === 'kullanim_disi' ||
          c.gecerlilik === 'kalibrasyonsuz') && (
          <Alert
            type="error"
            showIcon
            className="aktarim-uyari"
            title={t('spc.kullanilamaz_uyari')}
          />
        )}
      <Card loading={cihaz.isPending} style={{ marginTop: 16 }}>
        {c && (
          <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 3 }}>
            <Descriptions.Item label={t('spc.gecerlilik')}>
              <Tag color={GECERLILIK_RENK[c.gecerlilik as Gecerlilik]}>
                {t(`spc.gecerlilik_${c.gecerlilik}`)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('spc.son_kalibrasyon')}>
              {c.son_kalibrasyon_tarihi
                ? dayjs(c.son_kalibrasyon_tarihi).format('DD.MM.YYYY')
                : '—'}
            </Descriptions.Item>
            <Descriptions.Item label={t('spc.sonraki_kalibrasyon')}>
              {c.sonraki_kalibrasyon_tarihi
                ? dayjs(c.sonraki_kalibrasyon_tarihi).format('DD.MM.YYYY')
                : '—'}
            </Descriptions.Item>
            <Descriptions.Item label={t('spc.periyot')}>
              {t('spc.gun', { gun: c.kalibrasyon_periyodu_gun })}
            </Descriptions.Item>
            <Descriptions.Item label={t('spc.tur')}>{c.tur || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('spc.seri_no')}>{c.seri_no || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('spc.konum')}>{c.konum || '—'}</Descriptions.Item>
          </Descriptions>
        )}
      </Card>
      <Card title={t('spc.kalibrasyon_gecmisi')} style={{ marginTop: 16 }}>
        <Table<Kalibrasyon>
          rowKey="id"
          size="small"
          dataSource={c?.kalibrasyonlar ?? []}
          pagination={false}
          scroll={{ x: 'max-content' }}
          columns={[
            {
              title: t('spc.tarih'),
              dataIndex: 'tarih',
              render: (v: string) => dayjs(v).format('DD.MM.YYYY'),
            },
            {
              title: t('spc.sonuc'),
              dataIndex: 'sonuc',
              render: (v: string) => <Tag color={SONUC_RENK[v]}>{t(`spc.sonuc_${v}`)}</Tag>,
            },
            {
              title: t('spc.sertifika_no'),
              dataIndex: 'sertifika_no',
              render: (v: string) => v || '—',
            },
            {
              title: t('spc.kurum'),
              dataIndex: 'kurum',
              responsive: ['md'],
              render: (v: string) => v || '—',
            },
            {
              title: t('spc.aciklama'),
              dataIndex: 'aciklama',
              responsive: ['lg'],
              render: (v: string) => v || '—',
            },
          ]}
          locale={{ emptyText: t('spc.kalibrasyon_yok') }}
        />
      </Card>
      <Modal
        open={acik}
        title={t('spc.kalibrasyon_ekle')}
        okText={t('ortak.kaydet')}
        confirmLoading={ekle.isPending}
        onCancel={() => setAcik(false)}
        okButtonProps={{ htmlType: 'submit', form: 'kalibrasyon-formu' }}
        destroyOnHidden
      >
        <Form
          id="kalibrasyon-formu"
          layout="vertical"
          initialValues={{ tarih: dayjs(), sonuc: 'uygun' }}
          onFinish={(v: {
            tarih: Dayjs;
            sonuc: string;
            sertifika_no?: string;
            kurum?: string;
            aciklama?: string;
          }) =>
            ekle.mutate(
              {
                sonuc: v.sonuc,
                tarih: v.tarih.format('YYYY-MM-DD'),
                sertifika_no: v.sertifika_no ?? '',
                kurum: v.kurum ?? '',
                aciklama: v.aciklama ?? '',
              },
              {
                onSuccess: () => {
                  message.success(t('spc.kalibrasyon_kaydedildi'));
                  setAcik(false);
                },
              },
            )
          }
        >
          <div className="form-iki-sutun">
            <Form.Item name="tarih" label={t('spc.tarih')} rules={[{ required: true }]}>
              <DatePicker
                format="DD.MM.YYYY"
                style={{ width: '100%' }}
                disabledDate={(d) => d.isAfter(dayjs(), 'day')}
              />
            </Form.Item>
            <Form.Item name="sonuc" label={t('spc.sonuc')} rules={[{ required: true }]}>
              <Select
                options={['uygun', 'ayarlandi', 'uygunsuz'].map((s) => ({
                  value: s,
                  label: t(`spc.sonuc_${s}`),
                }))}
              />
            </Form.Item>
            <Form.Item name="sertifika_no" label={t('spc.sertifika_no')}>
              <Input maxLength={100} />
            </Form.Item>
            <Form.Item name="kurum" label={t('spc.kurum')}>
              <Input maxLength={200} />
            </Form.Item>
          </div>
          <Form.Item name="aciklama" label={t('spc.aciklama')}>
            <Input.TextArea maxLength={1000} rows={2} />
          </Form.Item>
          <p className="varlik-alt">{t('spc.uygunsuz_notu')}</p>
        </Form>
      </Modal>
    </SayfaKapsayici>
  );
}
