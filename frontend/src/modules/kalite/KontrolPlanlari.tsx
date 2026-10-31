/**
 * Kontrol planları (S26-A): ürün/operasyon başına ölçülen karakteristikler. Plan açılırken
 * karakteristikler (tolerans, alt grup boyutu, cihaz) birlikte tanımlanır.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { MinusCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Form, Input, InputNumber, Modal, Select, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import { type Plan, useCihazlar, usePlanlar, usePlanOlustur } from './spcHooks';

export function KontrolPlanlari() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const planlar = usePlanlar();
  const cihazlar = useCihazlar();
  const olustur = usePlanOlustur();
  const [acik, setAcik] = useState(false);

  const kolonlar: ColumnsType<Plan> = [
    {
      title: t('spc.plan'),
      dataIndex: 'kod',
      render: (_v, p) => (
        <span>
          <span className="varlik-ad">{p.ad}</span>
          <span className="varlik-alt sayisal" style={{ display: 'block' }}>
            {p.kod}
          </span>
        </span>
      ),
    },
    { title: t('spc.operasyon'), dataIndex: 'operasyon', render: (v: string) => v || '—' },
    { title: t('spc.karakteristik_sayisi'), dataIndex: 'karakteristik_sayisi', align: 'right' },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('spc.planlar_baslik')}
        alt={t('spc.planlar_alt')}
        sag={
          yazabilir ? (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setAcik(true)}>
              {t('spc.plan_ekle')}
            </Button>
          ) : null
        }
      />
      <Card>
        <Table<Plan>
          rowKey="id"
          columns={kolonlar}
          dataSource={planlar.data ?? []}
          loading={planlar.isPending}
          pagination={{ pageSize: 25, hideOnSinglePage: true }}
          scroll={{ x: 'max-content' }}
          onRow={(p) => ({
            onClick: () => navigate(`/kontrol-planlari/${p.id}`),
            style: { cursor: 'pointer' },
          })}
          locale={{
            emptyText: (
              <BosDurum baslik={t('spc.plan_bos')} aciklama={t('spc.plan_bos_aciklama')} />
            ),
          }}
        />
      </Card>
      <Modal
        open={acik}
        width={760}
        title={t('spc.plan_ekle')}
        okText={t('ortak.kaydet')}
        confirmLoading={olustur.isPending}
        onCancel={() => setAcik(false)}
        okButtonProps={{ htmlType: 'submit', form: 'plan-formu' }}
        destroyOnHidden
      >
        <Form
          id="plan-formu"
          layout="vertical"
          initialValues={{ karakteristikler: [{ birim: 'mm', alt_grup_boyutu: 5 }] }}
          onFinish={(v) =>
            olustur.mutate(v, {
              onSuccess: (p) => {
                message.success(t('spc.plan_eklendi', { kod: p.kod }));
                setAcik(false);
                navigate(`/kontrol-planlari/${p.id}`);
              },
            })
          }
        >
          <div className="form-iki-sutun">
            <Form.Item
              name="ad"
              label={t('spc.ad')}
              rules={[{ required: true, message: t('spc.ad_gerekli') }]}
            >
              <Input maxLength={200} placeholder={t('spc.plan_ornek')} />
            </Form.Item>
            <Form.Item name="operasyon" label={t('spc.operasyon')}>
              <Input maxLength={200} />
            </Form.Item>
          </div>
          <Form.List name="karakteristikler">
            {(alanlar, { add, remove }) => (
              <div className="spc-karakteristik-listesi">
                {alanlar.map((alan) => (
                  <div key={alan.key} className="spc-karakteristik-satir">
                    <Form.Item
                      name={[alan.name, 'ad']}
                      label={t('spc.karakteristik')}
                      rules={[{ required: true, message: t('spc.ad_gerekli') }]}
                    >
                      <Input maxLength={200} placeholder={t('spc.karakteristik_ornek')} />
                    </Form.Item>
                    <Form.Item name={[alan.name, 'birim']} label={t('spc.birim')}>
                      <Input maxLength={20} />
                    </Form.Item>
                    <Form.Item name={[alan.name, 'nominal']} label={t('spc.nominal')}>
                      <InputNumber style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name={[alan.name, 'alt_tolerans']} label={t('spc.alt_tolerans')}>
                      <InputNumber style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name={[alan.name, 'ust_tolerans']} label={t('spc.ust_tolerans')}>
                      <InputNumber style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item
                      name={[alan.name, 'alt_grup_boyutu']}
                      label={t('spc.n')}
                      tooltip={t('spc.n_ipucu')}
                    >
                      <InputNumber min={2} max={10} style={{ width: '100%' }} />
                    </Form.Item>
                    <Form.Item name={[alan.name, 'cihaz_id']} label={t('spc.cihaz')}>
                      <Select
                        allowClear
                        options={(cihazlar.data ?? []).map((c) => ({
                          value: c.id,
                          label: `${c.kod} · ${c.ad}`,
                        }))}
                      />
                    </Form.Item>
                    {alanlar.length > 1 && (
                      <Button
                        type="text"
                        danger
                        icon={<MinusCircleOutlined />}
                        aria-label={t('spc.karakteristik_kaldir')}
                        onClick={() => remove(alan.name)}
                      />
                    )}
                  </div>
                ))}
                <Button
                  icon={<PlusOutlined />}
                  onClick={() => add({ birim: 'mm', alt_grup_boyutu: 5 })}
                >
                  {t('spc.karakteristik_ekle')}
                </Button>
              </div>
            )}
          </Form.List>
        </Form>
      </Modal>
    </SayfaKapsayici>
  );
}
