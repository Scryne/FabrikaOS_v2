/**
 * Depolar & bakiyeler (S25-A, ADR-0024): solda depo → lokasyon ağacı (dolu kalem sayısıyla),
 * sağda seçili lokasyonun lot kırılımlı bakiye tablosu. Satırdan "Transfer" iki bacaklı transfer
 * penceresini açar; toplam bakiye değişmez, lokasyonlar arası taşınır.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ApartmentOutlined, PlusOutlined, SwapOutlined } from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  Col,
  Form,
  Input,
  InputNumber,
  Modal,
  Row,
  Select,
  Table,
  Tree,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { DataNode } from 'antd/es/tree';

import { BosDurum } from '@/components/BosDurum';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import {
  type Bakiye,
  useBakiyeler,
  useDepolar,
  useLokasyonOlustur,
  useSayimlar,
  useTransfer,
} from './depoHooks';

export function DepoBakiye() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const yazabilir = useAuthStore((s) => s.izinVar('stok:yaz'));
  const depolar = useDepolar();
  const sayimlar = useSayimlar();
  const [seciliLok, setSeciliLok] = useState<number | undefined>(undefined);
  const bakiyeler = useBakiyeler(seciliLok);
  const transfer = useTransfer();
  const lokasyonOlustur = useLokasyonOlustur();
  const [transferSatir, setTransferSatir] = useState<Bakiye | null>(null);
  const [lokasyonDepo, setLokasyonDepo] = useState<number | null>(null);
  const [transferForm] = Form.useForm();
  const [lokasyonForm] = Form.useForm();

  const tumLokasyonlar = useMemo(
    () => (depolar.data ?? []).flatMap((d) => d.lokasyonlar.map((l) => ({ ...l, depoKod: d.kod }))),
    [depolar.data],
  );

  const agac: DataNode[] = (depolar.data ?? []).map((d) => ({
    key: `depo-${d.id}`,
    selectable: false,
    title: (
      <span className="varlik-hucre">
        <ApartmentOutlined aria-hidden="true" />
        <span>
          <strong>{d.kod}</strong> · {d.ad}
        </span>
      </span>
    ),
    children: d.lokasyonlar.map((l) => ({
      key: `lok-${l.id}`,
      title: (
        <span>
          <span className="sayisal">{l.kod}</span> · {l.ad}{' '}
          <span className="varlik-alt">
            ({t('depo.dolu_kalem', { sayi: l.dolu_kalem_sayisi ?? 0 })})
          </span>
        </span>
      ),
    })),
  }));

  const kolonlar: ColumnsType<Bakiye> = [
    {
      title: t('depo.malzeme'),
      key: 'malzeme',
      render: (_v, b) => (
        <Link to={`/malzemeler/${b.malzeme_id}`} className="varlik-ad">
          {b.malzeme_ad}
          <span className="varlik-alt sayisal" style={{ display: 'block' }}>
            {b.malzeme_kod}
          </span>
          <span className="varlik-alt depo-lok-alt">
            {b.depo_kod} / {b.lokasyon_kod}
            {b.lot_no ? ` · ${b.lot_no}` : ''}
          </span>
        </Link>
      ),
    },
    {
      title: t('depo.lokasyon'),
      key: 'lok',
      responsive: ['md'],
      render: (_v, b) => `${b.depo_kod} / ${b.lokasyon_kod}`,
    },
    {
      title: t('depo.lot'),
      dataIndex: 'lot_no',
      responsive: ['lg'],
      render: (v: string) => v || '—',
    },
    {
      title: t('depo.miktar'),
      dataIndex: 'miktar',
      align: 'right',
      render: (v: number, b) => (
        <span className="sayisal">
          {v} {b.birim}
        </span>
      ),
    },
    ...(yazabilir
      ? [
          {
            title: '',
            key: 'aksiyon',
            align: 'right' as const,
            render: (_v: unknown, b: Bakiye) => (
              <Button
                size="small"
                icon={<SwapOutlined />}
                onClick={() => {
                  transferForm.resetFields();
                  setTransferSatir(b);
                }}
              >
                {t('depo.transfer')}
              </Button>
            ),
          },
        ]
      : []),
  ];

  const lokasyonSayisi = tumLokasyonlar.length;
  const doluKalem = (bakiyeler.data ?? []).length;
  const acikSayim = (sayimlar.data ?? []).filter(
    (s) => s.durum !== 'onaylandi' && s.durum !== 'iptal',
  ).length;

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('depo.baslik')}
        alt={t('depo.alt')}
        sag={
          <Link to="/sayimlar">
            <Button>{t('depo.sayimlara_git')}</Button>
          </Link>
        }
      />
      <OzetSerit
        yukleniyor={depolar.isPending}
        metrikler={[
          {
            anahtar: 'depo',
            baslik: t('depo.ozet_depo'),
            deger: String((depolar.data ?? []).length),
          },
          { anahtar: 'lok', baslik: t('depo.ozet_lokasyon'), deger: String(lokasyonSayisi) },
          { anahtar: 'kalem', baslik: t('depo.ozet_kalem'), deger: String(doluKalem) },
          { anahtar: 'sayim', baslik: t('depo.ozet_acik_sayim'), deger: String(acikSayim) },
        ]}
      />
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card
            title={t('depo.agac_baslik')}
            extra={
              yazabilir && (depolar.data ?? []).length > 0 ? (
                <Button
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    lokasyonForm.resetFields();
                    setLokasyonDepo((depolar.data ?? [])[0]?.id ?? null);
                  }}
                >
                  {t('depo.lokasyon_ekle')}
                </Button>
              ) : null
            }
          >
            <Tree
              treeData={agac}
              defaultExpandAll
              selectedKeys={seciliLok != null ? [`lok-${seciliLok}`] : []}
              onSelect={(keys) => {
                const k = String(keys[0] ?? '');
                setSeciliLok(k.startsWith('lok-') ? Number(k.slice(4)) : undefined);
              }}
            />
            {seciliLok != null && (
              <Button
                type="link"
                onClick={() => setSeciliLok(undefined)}
                style={{ paddingLeft: 0 }}
              >
                {t('depo.tum_lokasyonlar')}
              </Button>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={16}>
          <Card title={seciliLok != null ? t('depo.secili_bakiye') : t('depo.tum_bakiye')}>
            <Table<Bakiye>
              rowKey={(b) => `${b.malzeme_id}-${b.lokasyon_id}-${b.lot_no}`}
              columns={kolonlar}
              dataSource={bakiyeler.data ?? []}
              loading={bakiyeler.isPending}
              pagination={{ pageSize: 20, hideOnSinglePage: true }}
              locale={{
                emptyText: (
                  <BosDurum baslik={t('depo.bos_baslik')} aciklama={t('depo.bos_aciklama')} />
                ),
              }}
            />
          </Card>
        </Col>
      </Row>

      <Modal
        open={transferSatir !== null}
        title={t('depo.transfer_baslik')}
        okText={t('depo.transfer')}
        confirmLoading={transfer.isPending}
        onCancel={() => setTransferSatir(null)}
        onOk={() => transferForm.submit()}
        destroyOnHidden
      >
        {transferSatir && (
          <Form
            form={transferForm}
            layout="vertical"
            onFinish={(v: { hedef: number; miktar: number; aciklama?: string }) =>
              transfer.mutate(
                {
                  malzeme_id: transferSatir.malzeme_id,
                  kaynak_lokasyon_id: transferSatir.lokasyon_id,
                  hedef_lokasyon_id: v.hedef,
                  miktar: v.miktar,
                  lot_no: transferSatir.lot_no,
                  aciklama: v.aciklama ?? '',
                },
                {
                  onSuccess: () => {
                    message.success(t('depo.transfer_tamam'));
                    setTransferSatir(null);
                  },
                },
              )
            }
          >
            <p>
              <strong>{transferSatir.malzeme_ad}</strong> · {transferSatir.depo_kod} /{' '}
              {transferSatir.lokasyon_kod} ·{' '}
              <span className="sayisal">
                {transferSatir.miktar} {transferSatir.birim}
              </span>
            </p>
            <Form.Item
              name="hedef"
              label={t('depo.hedef_lokasyon')}
              rules={[{ required: true, message: t('depo.hedef_gerekli') }]}
            >
              <Select
                showSearch
                optionFilterProp="label"
                options={tumLokasyonlar
                  .filter((l) => l.id !== transferSatir.lokasyon_id)
                  .map((l) => ({ value: l.id, label: `${l.depoKod} / ${l.kod} · ${l.ad}` }))}
              />
            </Form.Item>
            <Form.Item
              name="miktar"
              label={t('depo.miktar')}
              rules={[
                { required: true, message: t('depo.miktar_gerekli') },
                {
                  validator: (_r, v: number | undefined) =>
                    v != null && v > transferSatir.miktar
                      ? Promise.reject(
                          new Error(t('depo.miktar_fazla', { en_fazla: transferSatir.miktar })),
                        )
                      : Promise.resolve(),
                },
              ]}
            >
              <InputNumber
                min={0.001}
                step={1}
                style={{ width: '100%' }}
                addonAfter={transferSatir.birim}
              />
            </Form.Item>
            <Form.Item name="aciklama" label={t('depo.aciklama')}>
              <Input maxLength={500} />
            </Form.Item>
          </Form>
        )}
      </Modal>

      <Modal
        open={lokasyonDepo !== null}
        title={t('depo.lokasyon_ekle')}
        okText={t('depo.kaydet')}
        confirmLoading={lokasyonOlustur.isPending}
        onCancel={() => setLokasyonDepo(null)}
        onOk={() => lokasyonForm.submit()}
        destroyOnHidden
      >
        <Form
          form={lokasyonForm}
          layout="vertical"
          initialValues={{ depo_id: lokasyonDepo }}
          onFinish={(v: { depo_id: number; kod: string; ad: string }) =>
            lokasyonOlustur.mutate(v, {
              onSuccess: () => {
                message.success(t('depo.lokasyon_tamam'));
                setLokasyonDepo(null);
              },
            })
          }
        >
          <Form.Item name="depo_id" label={t('depo.depo')} rules={[{ required: true }]}>
            <Select
              options={(depolar.data ?? []).map((d) => ({
                value: d.id,
                label: `${d.kod} · ${d.ad}`,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="kod"
            label={t('depo.kod')}
            rules={[{ required: true, message: t('depo.kod_gerekli') }]}
          >
            <Input maxLength={40} placeholder="RAF-A-01" />
          </Form.Item>
          <Form.Item
            name="ad"
            label={t('depo.ad')}
            rules={[{ required: true, message: t('depo.ad_gerekli') }]}
          >
            <Input maxLength={120} />
          </Form.Item>
        </Form>
      </Modal>
    </SayfaKapsayici>
  );
}
