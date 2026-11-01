/**
 * Sipariş detayı (Drawer, S31): künye, durum çizelgesi, kalemler, MRP tablosu (brüt → net) ve
 * onayın tetiklediği iş emri / satınalma talebi bağlantıları. Onay düğmesi siparişi açan kişide
 * pasiftir ve nedenini söyler (görev ayrımı; sunucu da 403 döner). Onay üretim hattı ister.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  CarOutlined,
  CheckOutlined,
  EditOutlined,
  FlagOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Drawer,
  Empty,
  Modal,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { DetayIstatSira, DurumZamanCizelgesi } from '@/components/DetayOgeleri';
import { paraBicim } from '@/modules/finans/hooks';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';

import {
  type Mrp,
  type Siparis,
  useMrp,
  useSiparis,
  useSiparisDurum,
  useSiparisOnayla,
} from './hooks';
import { SiparisFormu } from './SiparisFormu';
import { SiparisPim } from './SiparisPim';

type Kalem = Siparis['kalemler'][number];
type Ihtiyac = Mrp['ihtiyaclar'][number];

const sayi = (v: number) => v.toLocaleString('tr-TR', { maximumFractionDigits: 3 });

export function SiparisDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: s } = useSiparis(id);
  const mrp = useMrp(id);
  const onayla = useSiparisOnayla();
  const durum = useSiparisDurum();
  const makineler = useMakineSecenekleri();
  const izinVar = useAuthStore((st) => st.izinVar);
  const benimId = useAuthStore((st) => st.kullanici?.id);
  const [duzenle, setDuzenle] = useState(false);
  const [onayAcik, setOnayAcik] = useState(false);
  const [hat, setHat] = useState<number | undefined>();

  const yaz = izinVar('satis:yaz');
  const onay = izinVar('satis:onay');
  const hedefler = s?.gecerli_hedefler ?? [];
  const kendiSiparisi = s?.olusturan_kullanici_id === benimId;
  const m = mrp.data;

  const kalemKolon: ColumnsType<Kalem> = [
    {
      title: t('satis.urun'),
      key: 'urun',
      render: (_v, k) => (
        <span>
          {k.urun_ad} <span className="varlik-alt sayisal">{k.urun_kod}</span>
        </span>
      ),
    },
    {
      title: t('satis.miktar'),
      dataIndex: 'miktar',
      key: 'miktar',
      align: 'right',
      render: (v: number) => <span className="sayisal">{sayi(v)}</span>,
    },
    {
      title: t('satis.birim_fiyat'),
      dataIndex: 'birim_fiyat',
      key: 'birim_fiyat',
      align: 'right',
      render: (v: number | null) => (
        <span className="sayisal">{v == null ? '—' : paraBicim(v, s?.para_birimi)}</span>
      ),
    },
  ];

  const mrpKolon: ColumnsType<Ihtiyac> = [
    {
      title: t('satis.malzeme'),
      key: 'malzeme',
      render: (_v, i) => (
        <span>
          {i.malzeme_ad} <span className="varlik-alt sayisal">{i.malzeme_kod}</span>
        </span>
      ),
    },
    {
      title: t('satis.brut'),
      dataIndex: 'brut',
      key: 'brut',
      align: 'right',
      render: (v: number, i) => (
        <span className="sayisal">
          {sayi(v)} <span className="varlik-alt">{i.birim}</span>
        </span>
      ),
    },
    {
      title: (
        <Tooltip title={t('satis.kullanilabilir_ipucu')}>
          <span>{t('satis.kullanilabilir')}</span>
        </Tooltip>
      ),
      dataIndex: 'kullanilabilir',
      key: 'kullanilabilir',
      align: 'right',
      render: (v: number, i) => (
        <Tooltip
          title={t('satis.kullanilabilir_dokum', {
            eldeki: sayi(i.eldeki),
            tedarik: sayi(i.acik_tedarik),
            ayrilmis: sayi(i.ayrilmis),
          })}
        >
          <span className="sayisal">{sayi(v)}</span>
        </Tooltip>
      ),
    },
    {
      title: t('satis.net'),
      dataIndex: 'net',
      key: 'net',
      align: 'right',
      render: (v: number) =>
        v > 0 ? (
          <Tag color="error" bordered={false} style={{ marginRight: 0 }}>
            <span className="sayisal">{sayi(v)}</span>
          </Tag>
        ) : (
          <span className="sayisal" style={{ opacity: 0.5 }}>
            0
          </span>
        ),
    },
  ];

  const onayVer = () => {
    if (!s) return;
    onayla.mutate(
      { id: s.id, makineId: hat ?? s.makine_id ?? undefined },
      { onSuccess: () => setOnayAcik(false) },
    );
  };

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={780}
      title={
        s && (
          <Space>
            <span className="sayisal">{s.kod}</span>
            <SiparisPim durum={s.durum} />
          </Space>
        )
      }
    >
      {!s ? (
        <Skeleton active />
      ) : (
        <>
          <p className="varlik-alt" style={{ marginTop: 0 }}>
            {s.firma_ad} · {t('satis.teslim')}{' '}
            <span style={{ color: s.gecikti ? 'var(--hata-metin)' : undefined }}>
              {dayjs(s.teslim_tarihi).format('DD.MM.YYYY')}
            </span>
            {s.makine_kod && (
              <>
                {' '}
                · {t('satis.uretim_hatti')} <span className="sayisal">{s.makine_kod}</span>
              </>
            )}
            {s.talep_id && (
              <>
                {' '}
                · <Link to="/talepler">{t('satis.portal_talebi')}</Link>
              </>
            )}
          </p>

          <DurumZamanCizelgesi
            adimlar={['taslak', 'onaylandi', 'sevk_edildi', 'kapandi'].map((a) => ({
              anahtar: a,
              baslik: t(`satis.durum_${a}`),
            }))}
            mevcut={s.durum}
            olumsuz={{ anahtar: 'iptal', baslik: t('satis.durum_iptal') }}
          />

          <DetayIstatSira
            ogeler={[
              {
                anahtar: 'tutar',
                etiket: t('satis.tutar'),
                deger: s.tutar == null ? '—' : paraBicim(s.tutar, s.para_birimi),
              },
              { anahtar: 'kalem', etiket: t('satis.kalem'), deger: String(s.kalemler.length) },
              {
                anahtar: 'eksik',
                etiket: t('satis.eksik_malzeme'),
                deger: m ? String(m.eksik_sayisi) : '…',
                ton: m && m.eksik_sayisi > 0 ? 'var(--hata-metin)' : undefined,
              },
            ]}
          />

          <Space wrap style={{ margin: '18px 0' }}>
            {s.durum === 'taslak' && yaz && (
              <Button icon={<EditOutlined />} onClick={() => setDuzenle(true)}>
                {t('satis.duzenle')}
              </Button>
            )}
            {hedefler.includes('onaylandi') && onay && (
              <Tooltip title={kendiSiparisi ? t('satis.kendi_siparisin') : undefined}>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  disabled={kendiSiparisi}
                  onClick={() => {
                    setHat(s.makine_id ?? undefined);
                    setOnayAcik(true);
                  }}
                >
                  {t('satis.onayla')}
                </Button>
              </Tooltip>
            )}
            {hedefler.includes('sevk_edildi') && yaz && (
              <Button
                icon={<CarOutlined />}
                loading={durum.isPending}
                onClick={() => durum.mutate({ id: s.id, durum: 'sevk_edildi' })}
              >
                {t('satis.sevk_et')}
              </Button>
            )}
            {hedefler.includes('kapandi') && yaz && (
              <Button
                icon={<FlagOutlined />}
                loading={durum.isPending}
                onClick={() => durum.mutate({ id: s.id, durum: 'kapandi' })}
              >
                {t('satis.kapat')}
              </Button>
            )}
            {hedefler.includes('iptal') && (s.durum === 'onaylandi' ? onay : yaz) && (
              <Button
                danger
                icon={<StopOutlined />}
                loading={durum.isPending}
                onClick={() =>
                  Modal.confirm({
                    title: t('satis.iptal_baslik', { kod: s.kod }),
                    content:
                      s.durum === 'onaylandi'
                        ? t('satis.iptal_onayli_uyari')
                        : t('satis.iptal_uyari'),
                    okText: t('satis.iptal_et'),
                    okButtonProps: { danger: true },
                    cancelText: t('ortak.vazgec'),
                    onOk: () => durum.mutateAsync({ id: s.id, durum: 'iptal' }),
                  })
                }
              >
                {t('satis.iptal_et')}
              </Button>
            )}
          </Space>

          <h3 className="bolum-baslik">{t('satis.kalemler')}</h3>
          <Table<Kalem>
            rowKey="id"
            size="small"
            columns={kalemKolon}
            dataSource={s.kalemler}
            pagination={false}
            scroll={{ x: 480 }}
          />

          <h3 className="bolum-baslik" style={{ marginTop: 24 }}>
            {t('satis.mrp')}
          </h3>
          {m && m.recetesiz_urunler.length > 0 && (
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 12 }}
              message={t('satis.recetesiz', { n: m.recetesiz_urunler.length })}
              description={t('satis.recetesiz_aciklama')}
            />
          )}
          {mrp.isPending ? (
            <Skeleton active paragraph={{ rows: 3 }} />
          ) : !m || m.ihtiyaclar.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('satis.mrp_bos')} />
          ) : (
            <Table<Ihtiyac>
              rowKey="malzeme_id"
              size="small"
              columns={mrpKolon}
              dataSource={m.ihtiyaclar}
              pagination={false}
              scroll={{ x: 520 }}
            />
          )}
          <p className="varlik-alt" style={{ marginTop: 8 }}>
            {t('satis.mrp_aciklama')}
          </p>

          <h3 className="bolum-baslik" style={{ marginTop: 24 }}>
            {t('satis.tetikler')}
          </h3>
          {s.tetikler.length === 0 ? (
            <p className="varlik-alt">
              {s.durum === 'taslak' ? t('satis.tetik_yok_taslak') : t('satis.tetik_yok')}
            </p>
          ) : (
            <ul className="tetik-listesi">
              {s.tetikler.map((x) => (
                <li key={`${x.tur}-${x.id}`}>
                  <span className="varlik-alt">{t(`satis.tetik_${x.tur}`)}</span>
                  <Link
                    className="sayisal"
                    to={
                      x.tur === 'is_emri'
                        ? `/is-emirleri?kayit=${x.id}`
                        : `/satinalma-talepleri?kayit=${x.id}`
                    }
                  >
                    {x.kod}
                  </Link>
                  {x.durum && (
                    <Tag bordered={false}>
                      {t(
                        x.tur === 'is_emri'
                          ? `isemri.durum_${x.durum}`
                          : `satinalma.durum_${x.durum}`,
                      )}
                    </Tag>
                  )}
                </li>
              ))}
            </ul>
          )}

          <Modal
            open={onayAcik}
            onCancel={() => setOnayAcik(false)}
            onOk={onayVer}
            okText={t('satis.onayla_tetikle')}
            cancelText={t('ortak.vazgec')}
            confirmLoading={onayla.isPending}
            okButtonProps={{ disabled: !(hat ?? s.makine_id) }}
            title={t('satis.onay_baslik', { kod: s.kod })}
          >
            <p>{t('satis.onay_aciklama')}</p>
            {m && m.eksik_sayisi > 0 && (
              <Alert
                type="info"
                showIcon
                style={{ marginBottom: 12 }}
                message={t('satis.onay_talep_acilacak', { n: m.eksik_sayisi })}
              />
            )}
            <label className="form-etiket" htmlFor="onay-hat">
              {t('satis.uretim_hatti')}
            </label>
            <Select
              id="onay-hat"
              style={{ width: '100%' }}
              value={hat}
              onChange={setHat}
              showSearch
              optionFilterProp="label"
              placeholder={t('satis.hat_sec')}
              options={(makineler.data ?? []).map((mk) => ({
                value: mk.id,
                label: `${mk.kod} · ${mk.ad}`,
              }))}
            />
          </Modal>
          <SiparisFormu acik={duzenle} kapat={() => setDuzenle(false)} duzenlenen={s} />
        </>
      )}
    </Drawer>
  );
}
