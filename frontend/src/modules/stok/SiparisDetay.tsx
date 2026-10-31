/**
 * Satınalma siparişi detayı (S25-B): kalem bazında sipariş / teslim / kalan, irsaliye geçmişi,
 * teslim alma ve iade pencereleri. Teslim kısmi olabilir; aynı irsaliye ikinci kez stok yazmaz.
 * Fazla teslim tolerans içindeyse işaretlenir, aşarsa sunucu 422 döner (ADR-0024 §3).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeftOutlined,
  InboxOutlined,
  RollbackOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Table,
  Tag,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';

import { BosDurum } from '@/components/BosDurum';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { useDepolar } from './depoHooks';
import {
  gecikmis,
  type SiparisKalem,
  SiparisPim,
  type Teslim,
  type TeslimKalem,
  useIade,
  useSiparis,
  useSiparisAksiyon,
  useTeslimAl,
} from './siparisHooks';

function tarih(v: string | null, saat = false): string {
  if (!v) return '—';
  const d = new Date(v);
  return saat ? d.toLocaleString('tr-TR') : d.toLocaleDateString('tr-TR');
}

export function SiparisDetay() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const navigate = useNavigate();
  const id = Number(useParams().id);
  const depocu = useAuthStore((s) => s.izinVar('stok:yaz'));
  const satinalmaci = useAuthStore((s) => s.izinVar('satinalma:yaz'));
  const siparis = useSiparis(id);
  const depolar = useDepolar();
  const teslimAl = useTeslimAl(id);
  const iade = useIade(id);
  const aksiyon = useSiparisAksiyon(id);
  const [teslimAcik, setTeslimAcik] = useState(false);
  const [iadeTeslim, setIadeTeslim] = useState<Teslim | null>(null);
  const [kapatAcik, setKapatAcik] = useState(false);

  const s = siparis.data;

  if (!siparis.isPending && !s) {
    return (
      <SayfaKapsayici>
        <BosDurum
          baslik={t('siparis.bulunamadi')}
          aksiyon={<Link to="/satinalma-siparisleri">{t('siparis.listeye_don')}</Link>}
        />
      </SayfaKapsayici>
    );
  }

  const teslimAlinabilir = s != null && (s.durum === 'acik' || s.durum === 'kismi_teslim');
  const lokasyonSecenek = (depolar.data ?? []).flatMap((d) =>
    d.lokasyonlar.map((l) => ({ value: l.id, label: `${d.kod} / ${l.kod} · ${l.ad}` })),
  );

  const kalemKolon: ColumnsType<SiparisKalem> = [
    {
      title: t('depo.malzeme'),
      key: 'malzeme',
      render: (_v, k) => (
        <span>
          <Link to={`/malzemeler/${k.malzeme_id}`} className="varlik-ad">
            {k.malzeme_ad}
          </Link>
          <span className="varlik-alt sayisal" style={{ display: 'block' }}>
            {k.malzeme_kod}
            {k.fazla_teslim_toleransi_yuzde > 0
              ? ` · ${t('siparis.tolerans_kisa', { n: k.fazla_teslim_toleransi_yuzde })}`
              : ''}
          </span>
        </span>
      ),
    },
    {
      title: t('siparis.siparis_miktari'),
      dataIndex: 'miktar',
      align: 'right',
      responsive: ['md'],
      render: (v: number, k) => (
        <span className="sayisal">
          {v} {k.birim}
        </span>
      ),
    },
    {
      title: t('siparis.teslim_alinan'),
      key: 'teslim',
      width: 170,
      render: (_v, k) => (
        <div>
          <span className="sayisal">
            {k.teslim_alinan_miktar} / {k.miktar} {k.birim}
          </span>
          <Progress
            percent={Math.min(100, Math.round((k.teslim_alinan_miktar / k.miktar) * 100))}
            size="small"
            showInfo={false}
            strokeColor={k.kalan_miktar === 0 ? RENKLER.basari : RENKLER.mavi}
          />
        </div>
      ),
    },
    {
      title: t('siparis.birim_fiyat'),
      dataIndex: 'birim_fiyat',
      align: 'right',
      responsive: ['md'],
      render: (v: number | null) => (
        <span className="sayisal">{v != null ? v.toLocaleString('tr-TR') : '—'}</span>
      ),
    },
  ];

  const teslimKalemKolon = (teslim: Teslim): ColumnsType<TeslimKalem> => [
    {
      title: t('depo.malzeme'),
      key: 'm',
      render: (_v, k) => (
        <span>
          <span className="varlik-ad">{k.malzeme_ad}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {k.lokasyon}
            {k.lot_no ? ` · ${t('depo.lot')} ${k.lot_no}` : ''}
          </span>
        </span>
      ),
    },
    {
      title: t('siparis.miktar'),
      dataIndex: 'miktar',
      align: 'right',
      render: (v: number, k) => (
        <span
          className="sayisal"
          style={{ color: teslim.tur === 'iade' ? 'var(--hata)' : undefined }}
        >
          {teslim.tur === 'iade' ? `−${v}` : v} {k.birim}
        </span>
      ),
    },
    {
      title: '',
      key: 'isaret',
      align: 'right',
      render: (_v, k) => (
        <Space size={4} wrap style={{ justifyContent: 'flex-end' }}>
          {k.fazla_teslim && (
            <Tag color="warning" bordered={false}>
              {t('siparis.fazla_teslim')}
            </Tag>
          )}
          {k.hizli_kabulden && (
            <Tag color="blue" bordered={false}>
              {t('siparis.hizli_kabulden')}
            </Tag>
          )}
          {k.iade_edilen_miktar > 0 && (
            <Tag bordered={false}>{t('siparis.iade_edildi_n', { n: k.iade_edilen_miktar })}</Tag>
          )}
        </Space>
      ),
    },
  ];

  const teslimAc = () => setTeslimAcik(true);
  const iadeAc = (teslim: Teslim) => setIadeTeslim(teslim);

  return (
    <SayfaKapsayici enGenis={1080}>
      <SayfaBaslik
        baslik={
          <Space size={12} align="center" wrap>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/satinalma-siparisleri')}
              aria-label={t('ortak.geri')}
            />
            <span className="sayisal">{s?.kod ?? '…'}</span>
            {s && (
              <span className="baslik-pim">
                <SiparisPim durum={s.durum} />
              </span>
            )}
          </Space>
        }
        alt={s?.tedarikci_ad ?? undefined}
        sag={
          s && (
            <Space wrap>
              {s.durum === 'acik' && satinalmaci && s.teslimler.length === 0 && (
                <Popconfirm
                  title={t('siparis.iptal_soru')}
                  okText={t('siparis.iptal_et')}
                  cancelText={t('ortak.vazgec')}
                  onConfirm={() =>
                    aksiyon.mutate(
                      { aksiyon: 'iptal' },
                      { onSuccess: () => message.success(t('siparis.iptal_edildi')) },
                    )
                  }
                >
                  <Button danger icon={<StopOutlined />}>
                    {t('siparis.iptal_et')}
                  </Button>
                </Popconfirm>
              )}
              {s.durum === 'kismi_teslim' && satinalmaci && (
                <Button onClick={() => setKapatAcik(true)}>{t('siparis.kapat')}</Button>
              )}
              {teslimAlinabilir && depocu && (
                <Button type="primary" icon={<InboxOutlined />} onClick={teslimAc}>
                  {t('siparis.teslim_al')}
                </Button>
              )}
            </Space>
          )
        }
      />

      {s && (
        <>
          <Card style={{ marginBottom: 16 }} styles={{ body: { padding: 18 } }}>
            <Descriptions size="small" column={{ xs: 1, sm: 2, lg: 4 }}>
              <Descriptions.Item label={t('siparis.tedarikci')}>{s.tedarikci_ad}</Descriptions.Item>
              <Descriptions.Item label={t('siparis.beklenen')}>
                {gecikmis(s) ? (
                  <span style={{ color: 'var(--hata)', fontWeight: 600 }}>
                    {tarih(s.beklenen_teslim_tarihi)} · {t('siparis.gecikti')}
                  </span>
                ) : (
                  tarih(s.beklenen_teslim_tarihi)
                )}
              </Descriptions.Item>
              <Descriptions.Item label={t('siparis.tutar')}>
                <span className="sayisal">
                  {s.toplam_tutar.toLocaleString('tr-TR', { maximumFractionDigits: 2 })}{' '}
                  {s.para_birimi}
                </span>
              </Descriptions.Item>
              <Descriptions.Item label={t('siparis.teslim')}>
                <span className="sayisal">%{Math.round(s.teslim_orani * 100)}</span>
              </Descriptions.Item>
              {s.aciklama && (
                <Descriptions.Item label={t('depo.aciklama')} span="filled">
                  {s.aciklama}
                </Descriptions.Item>
              )}
              {s.kapanis_nedeni && (
                <Descriptions.Item label={t('siparis.kapanis_nedeni')} span="filled">
                  {s.kapanis_nedeni}
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>

          <Card title={t('siparis.kalemler')} style={{ marginBottom: 16 }}>
            <Table<SiparisKalem>
              rowKey="id"
              size="small"
              columns={kalemKolon}
              dataSource={s.kalemler}
              pagination={false}
            />
          </Card>

          <Card title={t('siparis.teslim_gecmisi')}>
            {s.teslimler.length === 0 ? (
              <BosDurum
                baslik={t('siparis.teslim_yok')}
                aciklama={t('siparis.teslim_yok_aciklama')}
              />
            ) : (
              <Space direction="vertical" size={16} style={{ width: '100%' }}>
                {[...s.teslimler].reverse().map((tk) => {
                  const iadeEdilebilir =
                    tk.tur === 'teslim' &&
                    depocu &&
                    s.durum !== 'iptal' &&
                    tk.kalemler.some((k) => k.miktar > k.iade_edilen_miktar);
                  return (
                    <div key={tk.id} className="teslim-kayit">
                      <div className="teslim-kayit-ust">
                        <Space size={8} wrap>
                          <span className="sayisal" style={{ fontWeight: 600 }}>
                            {tk.irsaliye_no}
                          </span>
                          {tk.tur === 'iade' ? (
                            <Tag color="error" bordered={false}>
                              {t('siparis.iade')}
                            </Tag>
                          ) : tk.zamaninda === false ? (
                            <Tag color="warning" bordered={false}>
                              {t('siparis.gec_teslim')}
                            </Tag>
                          ) : tk.zamaninda === true ? (
                            <Tag color="success" bordered={false}>
                              {t('siparis.zamaninda')}
                            </Tag>
                          ) : null}
                          <span className="varlik-alt">{tarih(tk.fiili_tarih, true)}</span>
                        </Space>
                        {iadeEdilebilir && (
                          <Button
                            size="small"
                            icon={<RollbackOutlined />}
                            onClick={() => iadeAc(tk)}
                          >
                            {t('siparis.iade_et')}
                          </Button>
                        )}
                      </div>
                      <Table<TeslimKalem>
                        rowKey="id"
                        size="small"
                        showHeader={false}
                        columns={teslimKalemKolon(tk)}
                        dataSource={tk.kalemler}
                        pagination={false}
                      />
                    </div>
                  );
                })}
              </Space>
            )}
          </Card>

          <Modal
            open={teslimAcik}
            title={t('siparis.teslim_baslik', { kod: s.kod })}
            okText={t('siparis.teslim_al')}
            cancelText={t('ortak.vazgec')}
            confirmLoading={teslimAl.isPending}
            onCancel={() => setTeslimAcik(false)}
            okButtonProps={{ htmlType: 'submit', form: 'siparis-teslim-formu' }}
            destroyOnHidden
            width={640}
          >
            <Form
              id="siparis-teslim-formu"
              layout="vertical"
              initialValues={{
                fiili_tarih: dayjs(),
                kalemler: s.kalemler.map((k) => ({ id: k.id, miktar: k.kalan_miktar, lot_no: '' })),
              }}
              onFinish={(v: {
                irsaliye_no: string;
                fiili_tarih: Dayjs;
                lokasyon_id?: number;
                aciklama?: string;
                kalemler: { id: number; miktar: number | null; lot_no?: string }[];
              }) => {
                const kalemler = v.kalemler
                  .filter((k) => (k.miktar ?? 0) > 0)
                  .map((k) => ({
                    siparis_kalemi_id: k.id,
                    miktar: k.miktar as number,
                    lot_no: k.lot_no ?? '',
                  }));
                if (kalemler.length === 0) {
                  message.warning(t('siparis.en_az_bir_kalem'));
                  return;
                }
                teslimAl.mutate(
                  {
                    irsaliye_no: v.irsaliye_no,
                    fiili_tarih: v.fiili_tarih.toISOString(),
                    lokasyon_id: v.lokasyon_id,
                    aciklama: v.aciklama ?? '',
                    kalemler,
                  },
                  {
                    onSuccess: () => {
                      message.success(t('siparis.teslim_tamam', { irsaliye: v.irsaliye_no }));
                      setTeslimAcik(false);
                    },
                  },
                );
              }}
            >
              <div className="form-iki-sutun">
                <Form.Item
                  name="irsaliye_no"
                  label={t('siparis.irsaliye')}
                  rules={[
                    { required: true, whitespace: true, message: t('siparis.irsaliye_gerekli') },
                  ]}
                >
                  <Input maxLength={40} autoFocus />
                </Form.Item>
                <Form.Item
                  name="fiili_tarih"
                  label={t('siparis.fiili_tarih')}
                  tooltip={t('siparis.fiili_tarih_ipucu')}
                  rules={[{ required: true }]}
                >
                  <DatePicker
                    showTime={{ format: 'HH:mm' }}
                    format="DD.MM.YYYY HH:mm"
                    style={{ width: '100%' }}
                    disabledDate={(d) => d.isAfter(dayjs(), 'day')}
                  />
                </Form.Item>
              </div>
              <Form.Item
                name="lokasyon_id"
                label={t('siparis.hedef_lokasyon')}
                tooltip={t('siparis.hedef_lokasyon_ipucu')}
              >
                <Select
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  placeholder={t('stok.lokasyon_bos')}
                  options={lokasyonSecenek}
                />
              </Form.Item>
              <Form.List name="kalemler">
                {(alanlar) => (
                  <div className="teslim-kalemler">
                    {alanlar.map((alan) => {
                      const k = s.kalemler[alan.name];
                      if (!k) return null;
                      return (
                        <div key={alan.key} className="teslim-kalem-satir">
                          <div className="teslim-kalem-ad">
                            <span className="varlik-ad">{k.malzeme_ad}</span>
                            <span className="varlik-alt" style={{ display: 'block' }}>
                              {t('siparis.kalan_n', { n: k.kalan_miktar, birim: k.birim ?? '' })}
                            </span>
                          </div>
                          <Form.Item name={[alan.name, 'id']} hidden>
                            <Input />
                          </Form.Item>
                          <Form.Item
                            name={[alan.name, 'miktar']}
                            style={{ marginBottom: 0 }}
                            aria-label={t('siparis.miktar')}
                          >
                            <InputNumber
                              min={0}
                              inputMode="decimal"
                              style={{ width: '100%' }}
                              suffix={k.birim}
                            />
                          </Form.Item>
                          {k.lot_takipli && (
                            <Form.Item
                              name={[alan.name, 'lot_no']}
                              className="teslim-lot"
                              style={{ marginBottom: 0 }}
                              dependencies={[['kalemler', alan.name, 'miktar']]}
                              rules={[
                                ({ getFieldValue }) => ({
                                  validator: (_r, deger: string | undefined) =>
                                    (getFieldValue(['kalemler', alan.name, 'miktar']) ?? 0) > 0 &&
                                    !deger?.trim()
                                      ? Promise.reject(new Error(t('siparis.lot_gerekli')))
                                      : Promise.resolve(),
                                }),
                              ]}
                            >
                              <Input placeholder={t('depo.lot')} maxLength={60} />
                            </Form.Item>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </Form.List>
              <Form.Item name="aciklama" label={t('depo.aciklama')} style={{ marginTop: 16 }}>
                <Input maxLength={500} />
              </Form.Item>
            </Form>
          </Modal>

          <Modal
            open={iadeTeslim !== null}
            title={t('siparis.iade_baslik', { irsaliye: iadeTeslim?.irsaliye_no ?? '' })}
            okText={t('siparis.iade_et')}
            okButtonProps={{ danger: true, htmlType: 'submit', form: 'siparis-iade-formu' }}
            cancelText={t('ortak.vazgec')}
            confirmLoading={iade.isPending}
            onCancel={() => setIadeTeslim(null)}
            destroyOnHidden
          >
            {iadeTeslim && (
              <Form
                id="siparis-iade-formu"
                layout="vertical"
                initialValues={{
                  kalemler: iadeTeslim.kalemler.map((k) => ({ id: k.id, miktar: 0 })),
                }}
                onFinish={(v: {
                  irsaliye_no: string;
                  aciklama?: string;
                  kalemler: { id: number; miktar: number | null }[];
                }) => {
                  const kalemler = v.kalemler
                    .filter((k) => (k.miktar ?? 0) > 0)
                    .map((k) => ({ teslim_alma_kalemi_id: k.id, miktar: k.miktar as number }));
                  if (kalemler.length === 0) {
                    message.warning(t('siparis.en_az_bir_kalem'));
                    return;
                  }
                  iade.mutate(
                    {
                      teslimId: iadeTeslim.id,
                      irsaliye_no: v.irsaliye_no,
                      aciklama: v.aciklama ?? '',
                      kalemler,
                    },
                    {
                      onSuccess: () => {
                        message.success(t('siparis.iade_tamam'));
                        setIadeTeslim(null);
                      },
                    },
                  );
                }}
              >
                <Form.Item
                  name="irsaliye_no"
                  label={t('siparis.iade_irsaliye')}
                  rules={[
                    { required: true, whitespace: true, message: t('siparis.irsaliye_gerekli') },
                  ]}
                >
                  <Input maxLength={40} autoFocus />
                </Form.Item>
                <Form.List name="kalemler">
                  {(alanlar) => (
                    <div className="teslim-kalemler">
                      {alanlar.map((alan) => {
                        const k = iadeTeslim.kalemler[alan.name];
                        if (!k) return null;
                        const enFazla = k.miktar - k.iade_edilen_miktar;
                        return (
                          <div key={alan.key} className="teslim-kalem-satir">
                            <div className="teslim-kalem-ad">
                              <span className="varlik-ad">{k.malzeme_ad}</span>
                              <span className="varlik-alt" style={{ display: 'block' }}>
                                {t('siparis.iade_edilebilir_n', {
                                  n: enFazla,
                                  birim: k.birim ?? '',
                                })}
                              </span>
                            </div>
                            <Form.Item name={[alan.name, 'id']} hidden>
                              <Input />
                            </Form.Item>
                            <Form.Item name={[alan.name, 'miktar']} style={{ marginBottom: 0 }}>
                              <InputNumber
                                min={0}
                                max={enFazla}
                                disabled={enFazla <= 0}
                                inputMode="decimal"
                                style={{ width: '100%' }}
                                suffix={k.birim}
                              />
                            </Form.Item>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Form.List>
                <Form.Item
                  name="aciklama"
                  label={t('siparis.iade_nedeni')}
                  style={{ marginTop: 16 }}
                >
                  <Input maxLength={500} />
                </Form.Item>
              </Form>
            )}
          </Modal>

          <Modal
            open={kapatAcik}
            title={t('siparis.kapat_baslik')}
            okText={t('siparis.kapat')}
            cancelText={t('ortak.vazgec')}
            confirmLoading={aksiyon.isPending}
            onCancel={() => setKapatAcik(false)}
            okButtonProps={{ htmlType: 'submit', form: 'siparis-kapat-formu' }}
            destroyOnHidden
          >
            <p className="varlik-alt" style={{ marginTop: 0 }}>
              {t('siparis.kapat_aciklama')}
            </p>
            <Form
              id="siparis-kapat-formu"
              layout="vertical"
              onFinish={(v: { neden: string }) =>
                aksiyon.mutate(
                  { aksiyon: 'kapat', neden: v.neden },
                  {
                    onSuccess: () => {
                      message.success(t('siparis.kapatildi'));
                      setKapatAcik(false);
                    },
                  },
                )
              }
            >
              <Form.Item
                name="neden"
                label={t('siparis.kapanis_nedeni')}
                rules={[{ required: true, min: 3, message: t('siparis.neden_gerekli') }]}
              >
                <Input.TextArea rows={3} maxLength={500} />
              </Form.Item>
            </Form>
          </Modal>
        </>
      )}
    </SayfaKapsayici>
  );
}
