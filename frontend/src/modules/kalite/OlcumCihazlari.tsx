/**
 * Ölçüm cihazları (S26-A): kalibrasyon geçerliliği tek bakışta. Süresi geçmiş ya da kullanım
 * dışı cihazla SPC ölçümü girilemez (ISO 9001 7.1.5) — liste bu yüzden önce bunu gösterir.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Form, Input, InputNumber, Modal, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import {
  type Cihaz,
  type Gecerlilik,
  GECERLILIK_RENK,
  useCihazlar,
  useCihazOlustur,
} from './spcHooks';

export function OlcumCihazlari() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const cihazlar = useCihazlar();
  const olustur = useCihazOlustur();
  const [acik, setAcik] = useState(false);

  const liste = cihazlar.data ?? [];
  const say = (g: Gecerlilik) => liste.filter((c) => c.gecerlilik === g).length;

  const kolonlar: ColumnsType<Cihaz> = [
    {
      title: t('spc.cihaz'),
      dataIndex: 'kod',
      render: (_v, c) => (
        <span>
          <span className="varlik-ad sayisal">{c.kod}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {c.ad}
          </span>
        </span>
      ),
    },
    {
      title: t('spc.konum'),
      dataIndex: 'konum',
      responsive: ['md'],
      render: (v: string) => v || '—',
    },
    {
      title: t('spc.gecerlilik'),
      dataIndex: 'gecerlilik',
      render: (g: Gecerlilik) => <Tag color={GECERLILIK_RENK[g]}>{t(`spc.gecerlilik_${g}`)}</Tag>,
    },
    {
      title: t('spc.sonraki_kalibrasyon'),
      dataIndex: 'sonraki_kalibrasyon_tarihi',
      render: (v: string | null, c) =>
        v ? (
          <span className="sayisal">
            {new Date(v).toLocaleDateString('tr-TR')}
            {c.kalan_gun !== null && (
              <span className="varlik-alt" style={{ display: 'block' }}>
                {c.kalan_gun < 0
                  ? t('spc.gun_gecti', { gun: -c.kalan_gun })
                  : t('spc.gun_kaldi', { gun: c.kalan_gun })}
              </span>
            )}
          </span>
        ) : (
          '—'
        ),
    },
    {
      title: t('spc.periyot'),
      dataIndex: 'kalibrasyon_periyodu_gun',
      align: 'right',
      responsive: ['lg'],
      render: (v: number) => <span className="sayisal">{t('spc.gun', { gun: v })}</span>,
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('spc.cihazlar_baslik')}
        alt={t('spc.cihazlar_alt')}
        sag={
          yazabilir ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAcik(true)}>
              {t('spc.cihaz_ekle')}
            </Button>
          ) : null
        }
      />
      <OzetSerit
        yukleniyor={cihazlar.isPending}
        metrikler={[
          { anahtar: 'toplam', baslik: t('spc.toplam_cihaz'), deger: String(liste.length) },
          {
            anahtar: 'gecerli',
            baslik: t('spc.gecerlilik_gecerli'),
            deger: String(say('gecerli')),
            olumlu: true,
          },
          {
            anahtar: 'yaklasiyor',
            baslik: t('spc.gecerlilik_yaklasiyor'),
            deger: String(say('yaklasiyor')),
          },
          {
            anahtar: 'gecmis',
            baslik: t('spc.kullanilamaz'),
            deger: String(say('gecmis') + say('kullanim_disi') + say('kalibrasyonsuz')),
            olumlu: say('gecmis') + say('kullanim_disi') + say('kalibrasyonsuz') === 0,
          },
        ]}
      />
      <Card>
        <Table<Cihaz>
          rowKey="id"
          columns={kolonlar}
          dataSource={liste}
          loading={cihazlar.isPending}
          pagination={{ pageSize: 25, hideOnSinglePage: true }}
          scroll={{ x: 'max-content' }}
          onRow={(c) => ({
            onClick: () => navigate(`/olcum-cihazlari/${c.id}`),
            style: { cursor: 'pointer' },
          })}
          locale={{
            emptyText: (
              <BosDurum baslik={t('spc.cihaz_bos')} aciklama={t('spc.cihaz_bos_aciklama')} />
            ),
          }}
        />
      </Card>
      <Modal
        open={acik}
        title={t('spc.cihaz_ekle')}
        okText={t('ortak.kaydet')}
        confirmLoading={olustur.isPending}
        onCancel={() => setAcik(false)}
        okButtonProps={{ htmlType: 'submit', form: 'cihaz-formu' }}
        destroyOnHidden
      >
        <Form
          id="cihaz-formu"
          layout="vertical"
          initialValues={{ kalibrasyon_periyodu_gun: 365 }}
          onFinish={(v) =>
            olustur.mutate(v, {
              onSuccess: (c) => {
                message.success(t('spc.cihaz_eklendi', { kod: c.kod }));
                setAcik(false);
                navigate(`/olcum-cihazlari/${c.id}`);
              },
            })
          }
        >
          <div className="form-iki-sutun">
            <Form.Item
              name="kod"
              label={t('spc.kod')}
              rules={[{ required: true, message: t('spc.kod_gerekli') }]}
            >
              <Input maxLength={50} placeholder="OC-001" />
            </Form.Item>
            <Form.Item
              name="ad"
              label={t('spc.ad')}
              rules={[{ required: true, message: t('spc.ad_gerekli') }]}
            >
              <Input maxLength={200} placeholder={t('spc.ad_ornek')} />
            </Form.Item>
            <Form.Item name="tur" label={t('spc.tur')}>
              <Input maxLength={100} />
            </Form.Item>
            <Form.Item name="seri_no" label={t('spc.seri_no')}>
              <Input maxLength={100} />
            </Form.Item>
            <Form.Item name="konum" label={t('spc.konum')}>
              <Input maxLength={200} />
            </Form.Item>
            <Form.Item name="kalibrasyon_periyodu_gun" label={t('spc.periyot')}>
              <InputNumber
                min={1}
                max={3650}
                style={{ width: '100%' }}
                suffix={t('spc.gun_birim')}
              />
            </Form.Item>
          </div>
          <p className="varlik-alt">{t('spc.ilk_kalibrasyon_notu')}</p>
        </Form>
      </Modal>
    </SayfaKapsayici>
  );
}
