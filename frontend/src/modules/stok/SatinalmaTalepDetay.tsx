/**
 * Satınalma talebi detayı (Drawer) — künye + durum rozeti + kalem tablosu + tahmini toplam.
 * Aksiyon butonları ``gecerliHedefler(durum)`` ∩ kullanıcı izni ile filtrelenir (görev ayrımı):
 * ``onayla``/``reddet`` yalnız ``satinalma:onay`` varsa görünür. Reddet ``red_nedeni`` sorar.
 * Onaylı talepten ``satinalma:yaz`` ile sipariş açılır (S25-B); açık siparişi varsa bağlantı gösterilir.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import { ShoppingCartOutlined } from '@ant-design/icons';
import {
  App,
  Button,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';

import { useAuthStore } from '@/store/authStore';

import { useTalep, useTalepDurumAksiyon } from './hooks';
import { TalepDurumEtiketi } from './rozetler';
import { SiparisPim, useSiparisler, useSiparisOlustur, useTedarikciler } from './siparisHooks';
import { gecerliHedefler } from './talepDurum';

type KalemSatiri = {
  id: number;
  malzeme_id: number;
  malzeme_kod?: string | null;
  malzeme_ad?: string | null;
  miktar: number;
  birim: string;
  tahmini_birim_fiyat?: number | null;
  aciklama: string;
};

type Aksiyon = { aksiyon: string; izin: string; etiket: string };

const HEDEF_AKSIYON: Record<string, Aksiyon> = {
  onay_bekliyor: { aksiyon: 'gonder', izin: 'satinalma:yaz', etiket: 'satinalma.gonder' },
  onaylandi: { aksiyon: 'onayla', izin: 'satinalma:onay', etiket: 'satinalma.onayla' },
  reddedildi: { aksiyon: 'reddet', izin: 'satinalma:onay', etiket: 'satinalma.reddet' },
  iptal: { aksiyon: 'iptal', izin: 'satinalma:yaz', etiket: 'satinalma.iptal' },
};

export function SatinalmaTalepDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: talep } = useTalep(id ?? 0);
  const aksiyonMut = useTalepDurumAksiyon();
  const izinVar = useAuthStore((s) => s.izinVar);
  const [redAcik, setRedAcik] = useState(false);
  const [redNeden, setRedNeden] = useState('');
  const { message } = App.useApp();
  const navigate = useNavigate();
  const [siparisAcik, setSiparisAcik] = useState(false);
  const siparisOkur = izinVar('satinalma:oku');
  const siparisYazar = izinVar('satinalma:yaz');
  const onayli = talep?.durum === 'onaylandi';
  const siparisler = useSiparisler({ talep_id: talep?.id }, onayli && siparisOkur);
  const aktifSiparis = (siparisler.data ?? []).find((s) => s.durum !== 'iptal');
  const tedarikciler = useTedarikciler(siparisAcik);
  const siparisOlustur = useSiparisOlustur();

  const hedefler = talep ? gecerliHedefler(talep.durum) : [];
  const butonlar = hedefler
    .map((h) => HEDEF_AKSIYON[h])
    .filter((a): a is Aksiyon => a != null && izinVar(a.izin));

  const calistir = async (aksiyon: string) => {
    if (!talep) return;
    if (aksiyon === 'reddet') {
      setRedAcik(true);
      return;
    }
    await aksiyonMut.mutateAsync({ id: talep.id, aksiyon });
  };

  const redGonder = async () => {
    if (!talep) return;
    await aksiyonMut.mutateAsync({ id: talep.id, aksiyon: 'reddet', red_nedeni: redNeden });
    setRedAcik(false);
    setRedNeden('');
  };

  const kolonlar: ColumnsType<KalemSatiri> = [
    {
      title: t('satinalma.malzeme'),
      dataIndex: 'malzeme_id',
      key: 'malzeme_id',
      render: (_v: number, k) => (
        <span>
          <span className="varlik-ad">{k.malzeme_ad ?? `#${k.malzeme_id}`}</span>
          {k.malzeme_kod && (
            <span className="varlik-alt sayisal" style={{ display: 'block' }}>
              {k.malzeme_kod}
            </span>
          )}
        </span>
      ),
    },
    {
      title: t('satinalma.miktar'),
      dataIndex: 'miktar',
      key: 'miktar',
      align: 'right',
      render: (v: number, k) => (
        <span className="sayisal">
          {v} {k.birim}
        </span>
      ),
    },
    {
      title: t('satinalma.birim_fiyat'),
      dataIndex: 'tahmini_birim_fiyat',
      key: 'tahmini_birim_fiyat',
      align: 'right',
      render: (v: number | null) => <span className="sayisal">{v ?? '—'}</span>,
    },
  ];

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={620}
      title={talep?.kod}
      extra={talep && <TalepDurumEtiketi durum={talep.durum} />}
    >
      {talep && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('satinalma.baslik')}>{talep.baslik}</Descriptions.Item>
            <Descriptions.Item label={t('satinalma.tahmini_toplam')}>
              {talep.tahmini_toplam != null ? `${talep.tahmini_toplam} ${talep.para_birimi}` : '—'}
            </Descriptions.Item>
            {talep.red_nedeni && (
              <Descriptions.Item label={t('satinalma.red_nedeni')}>
                {talep.red_nedeni}
              </Descriptions.Item>
            )}
            {aktifSiparis && (
              <Descriptions.Item label={t('siparis.talep_siparisi')}>
                <Space size={8} wrap>
                  <Link to={`/satinalma-siparisleri/${aktifSiparis.id}`} className="sayisal">
                    {aktifSiparis.kod}
                  </Link>
                  <SiparisPim durum={aktifSiparis.durum} />
                </Space>
              </Descriptions.Item>
            )}
          </Descriptions>
          <Table<KalemSatiri>
            style={{ marginTop: 16 }}
            rowKey="id"
            pagination={false}
            dataSource={talep.kalemler}
            columns={kolonlar}
          />
          <Space style={{ marginTop: 16 }} wrap>
            {onayli && siparisYazar && !siparisler.isPending && !aktifSiparis && (
              <Button
                type="primary"
                icon={<ShoppingCartOutlined />}
                onClick={() => setSiparisAcik(true)}
              >
                {t('siparis.ac')}
              </Button>
            )}
            {butonlar.map((a) => (
              <Button
                key={a.aksiyon}
                type={a.aksiyon === 'onayla' ? 'primary' : 'default'}
                danger={a.aksiyon === 'reddet'}
                loading={aksiyonMut.isPending}
                onClick={() => void calistir(a.aksiyon)}
              >
                {t(a.etiket)}
              </Button>
            ))}
          </Space>
          <Modal
            open={siparisAcik}
            title={t('siparis.ac_baslik', { kod: talep.kod })}
            okText={t('siparis.ac')}
            cancelText={t('ortak.vazgec')}
            confirmLoading={siparisOlustur.isPending}
            onCancel={() => setSiparisAcik(false)}
            okButtonProps={{ htmlType: 'submit', form: 'talep-siparis-formu' }}
            destroyOnHidden
          >
            <Form
              id="talep-siparis-formu"
              layout="vertical"
              initialValues={{ tolerans: 0 }}
              onFinish={(v: {
                tedarikci_firma_id: number;
                beklenen?: Dayjs;
                tolerans: number;
                aciklama?: string;
              }) =>
                siparisOlustur.mutate(
                  {
                    talep_id: talep.id,
                    tedarikci_firma_id: v.tedarikci_firma_id,
                    beklenen_teslim_tarihi: v.beklenen ? v.beklenen.format('YYYY-MM-DD') : null,
                    aciklama: v.aciklama ?? '',
                    kalemler: (talep.kalemler ?? []).map((k) => ({
                      talep_kalemi_id: k.id,
                      fazla_teslim_toleransi_yuzde: v.tolerans ?? 0,
                    })),
                  },
                  {
                    onSuccess: (sip) => {
                      message.success(t('siparis.acildi', { kod: sip.kod }));
                      setSiparisAcik(false);
                      kapat();
                      navigate(`/satinalma-siparisleri/${sip.id}`);
                    },
                  },
                )
              }
            >
              <Form.Item
                name="tedarikci_firma_id"
                label={t('siparis.tedarikci')}
                rules={[{ required: true, message: t('siparis.tedarikci_gerekli') }]}
                extra={
                  tedarikciler.data && tedarikciler.data.length === 0
                    ? t('siparis.tedarikci_yok')
                    : undefined
                }
              >
                <Select
                  showSearch
                  optionFilterProp="label"
                  loading={tedarikciler.isPending}
                  options={(tedarikciler.data ?? []).map((f) => ({ value: f.id, label: f.ad }))}
                />
              </Form.Item>
              <Form.Item name="beklenen" label={t('siparis.beklenen')}>
                <DatePicker
                  format="DD.MM.YYYY"
                  style={{ width: '100%' }}
                  disabledDate={(d) => d.isBefore(dayjs(), 'day')}
                />
              </Form.Item>
              <Form.Item
                name="tolerans"
                label={t('siparis.tolerans')}
                tooltip={t('siparis.tolerans_ipucu')}
              >
                <InputNumber min={0} max={100} style={{ width: '100%' }} suffix="%" />
              </Form.Item>
              <Form.Item name="aciklama" label={t('depo.aciklama')}>
                <Input maxLength={1000} />
              </Form.Item>
            </Form>
          </Modal>
          <Modal
            open={redAcik}
            onCancel={() => setRedAcik(false)}
            onOk={() => void redGonder()}
            title={t('satinalma.red_baslik')}
            okText={t('ortak.kaydet')}
            cancelText={t('ortak.iptal')}
            confirmLoading={aksiyonMut.isPending}
          >
            <Input.TextArea
              rows={3}
              value={redNeden}
              onChange={(e) => setRedNeden(e.target.value)}
              placeholder={t('satinalma.red_nedeni')}
            />
          </Modal>
        </>
      )}
    </Drawer>
  );
}
