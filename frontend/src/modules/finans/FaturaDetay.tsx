/**
 * Fatura detayı (Drawer): künye, durum çizelgesi, kalemler, toplamlar, ödemeler ve aksiyonlar.
 * Aksiyonlar ``gecerliHedefler`` ∩ yetki ile gösterilir; kesme düğmesi faturayı hazırlayan
 * kişide pasiftir ve nedenini söyler (görev ayrımı; sunucu da 403 döner).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckOutlined,
  EditOutlined,
  FilePdfOutlined,
  RollbackOutlined,
  SendOutlined,
  StopOutlined,
  WalletOutlined,
} from '@ant-design/icons';
import { Alert, App, Button, Drawer, Input, Modal, Space, Table, Tooltip } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import { DetayIstatSira, DurumZamanCizelgesi } from '@/components/DetayOgeleri';
import { useAuthStore } from '@/store/authStore';

import { gecerliHedefler } from './durum';
import { FaturaFormu } from './FaturaFormu';
import { FaturaPim } from './FaturaPim';
import {
  type Fatura,
  type FaturaAksiyon,
  faturaPdfAc,
  paraBicim,
  useFatura,
  useFaturaAksiyon,
} from './hooks';
import { OdemeFormu } from './OdemeFormu';

type Kalem = Fatura['kalemler'][number];

export function FaturaDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { data: f } = useFatura(id ?? 0);
  const aksiyon = useFaturaAksiyon();
  const izinVar = useAuthStore((s) => s.izinVar);
  const benimId = useAuthStore((s) => s.kullanici?.id);
  const [nedenAksiyon, setNedenAksiyon] = useState<'iade' | 'iptal' | null>(null);
  const [neden, setNeden] = useState('');
  const [duzenle, setDuzenle] = useState(false);
  const [odemeAcik, setOdemeAcik] = useState(false);
  const [pdfYukleniyor, setPdfYukleniyor] = useState(false);

  const yaz = izinVar('finans:yaz');
  const onay = izinVar('finans:onay');
  const hedefler = f ? gecerliHedefler(f.durum) : [];
  const kendiFaturasi = f?.olusturan_kullanici_id != null && f.olusturan_kullanici_id === benimId;

  const calistir = (a: FaturaAksiyon) => {
    if (!f) return;
    if (a === 'iade' || (a === 'iptal' && f.durum === 'kesildi')) {
      setNeden('');
      setNedenAksiyon(a);
      return;
    }
    aksiyon.mutate({ id: f.id, aksiyon: a });
  };

  const kolonlar: ColumnsType<Kalem> = [
    { title: '#', dataIndex: 'sira', key: 'sira', width: 44 },
    { title: t('finans.aciklama'), dataIndex: 'aciklama', key: 'aciklama' },
    {
      title: t('finans.miktar'),
      key: 'miktar',
      align: 'right',
      render: (_v, k) => (
        <span className="sayisal">
          {k.miktar.toLocaleString('tr-TR')} {k.birim}
        </span>
      ),
    },
    {
      title: t('finans.birim_fiyat'),
      dataIndex: 'birim_fiyat',
      key: 'birim_fiyat',
      align: 'right',
      render: (v: number) => <span className="sayisal">{paraBicim(v, f?.para_birimi)}</span>,
    },
    {
      title: t('finans.kdv'),
      dataIndex: 'kdv_orani',
      key: 'kdv_orani',
      align: 'right',
      render: (v: number) => <span className="sayisal">%{v}</span>,
    },
    {
      title: t('finans.tutar'),
      dataIndex: 'satir_tutari',
      key: 'satir_tutari',
      align: 'right',
      render: (v: number) => <span className="sayisal">{paraBicim(v, f?.para_birimi)}</span>,
    },
  ];

  const mutluYol = ['taslak', 'onay_bekliyor', 'kesildi', 'kapandi'].map((d) => ({
    anahtar: d,
    baslik: t(`finans.durum_${d}`),
  }));

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      size={760}
      title={
        f && (
          <Space>
            <span className="sayisal">{f.kod}</span>
            <FaturaPim durum={f.durum} />
          </Space>
        )
      }
      extra={
        f && (
          <Button
            icon={<FilePdfOutlined />}
            loading={pdfYukleniyor}
            onClick={() => {
              setPdfYukleniyor(true);
              faturaPdfAc(f.id, f.kod)
                .catch(() => message.error(t('finans.pdf_hata')))
                .finally(() => setPdfYukleniyor(false));
            }}
          >
            {t('finans.pdf')}
          </Button>
        )
      }
    >
      {f && (
        <>
          <p className="varlik-alt" style={{ marginTop: 0 }}>
            {f.firma_ad} · {t(`finans.tur_${f.tur}`)} · {t('finans.fatura_tarihi')}{' '}
            {dayjs(f.fatura_tarihi).format('DD.MM.YYYY')} · {t('finans.vade')}{' '}
            <span style={{ color: f.vadesi_gecti ? 'var(--hata-metin)' : undefined }}>
              {dayjs(f.vade_tarihi).format('DD.MM.YYYY')}
            </span>
          </p>

          <DetayIstatSira
            ogeler={[
              {
                anahtar: 'genel',
                etiket: t('finans.genel_toplam'),
                deger: paraBicim(f.genel_toplam, f.para_birimi),
              },
              {
                anahtar: 'odenen',
                etiket: t('finans.odenen'),
                deger: paraBicim(f.odenen_tutar, f.para_birimi),
              },
              {
                anahtar: 'acik',
                etiket: t('finans.acik'),
                deger: paraBicim(f.acik_tutar, f.para_birimi),
                ton: f.vadesi_gecti ? 'var(--hata-metin)' : undefined,
              },
            ]}
          />

          {f.iade_nedeni && f.durum === 'taslak' && (
            <Alert
              type="warning"
              showIcon
              style={{ marginTop: 16 }}
              title={t('finans.iade_edildi')}
              description={f.iade_nedeni}
            />
          )}
          {f.durum === 'iptal' && f.iptal_nedeni && (
            <Alert
              type="error"
              showIcon
              style={{ marginTop: 16 }}
              title={t('finans.iptal_nedeni')}
              description={f.iptal_nedeni}
            />
          )}

          <Space wrap style={{ margin: '18px 0' }}>
            {f.durum === 'taslak' && yaz && (
              <Button icon={<EditOutlined />} onClick={() => setDuzenle(true)}>
                {t('finans.duzenle')}
              </Button>
            )}
            {hedefler.includes('onay_bekliyor') && yaz && (
              <Button type="primary" icon={<SendOutlined />} onClick={() => calistir('gonder')}>
                {t('finans.onaya_gonder')}
              </Button>
            )}
            {hedefler.includes('kesildi') && onay && (
              <Tooltip title={kendiFaturasi ? t('finans.kendi_faturan') : undefined}>
                <Button
                  type="primary"
                  icon={<CheckOutlined />}
                  disabled={kendiFaturasi}
                  loading={aksiyon.isPending}
                  onClick={() => calistir('kes')}
                >
                  {t('finans.kes')}
                </Button>
              </Tooltip>
            )}
            {hedefler.includes('taslak') && onay && (
              <Button icon={<RollbackOutlined />} onClick={() => calistir('iade')}>
                {t('finans.iade_et')}
              </Button>
            )}
            {f.durum === 'kesildi' && f.acik_tutar > 0 && (yaz || onay) && (
              <Button icon={<WalletOutlined />} onClick={() => setOdemeAcik(true)}>
                {f.tur === 'satis' ? t('finans.tahsilat_gir') : t('finans.odeme_gir')}
              </Button>
            )}
            {hedefler.includes('iptal') &&
              ((f.durum === 'kesildi' && onay) || (f.durum !== 'kesildi' && yaz)) && (
                <Button danger icon={<StopOutlined />} onClick={() => calistir('iptal')}>
                  {t('finans.iptal_et')}
                </Button>
              )}
          </Space>

          <Table<Kalem>
            rowKey="id"
            size="small"
            columns={kolonlar}
            dataSource={f.kalemler}
            pagination={false}
            scroll={{ x: 560 }}
          />
          <dl className="fatura-toplam">
            <dt>{t('finans.ara_toplam')}</dt>
            <dd className="sayisal">{paraBicim(f.ara_toplam, f.para_birimi)}</dd>
            <dt>{t('finans.kdv')}</dt>
            <dd className="sayisal">{paraBicim(f.kdv_toplam, f.para_birimi)}</dd>
            <dt className="genel">{t('finans.genel_toplam')}</dt>
            <dd className="sayisal genel">{paraBicim(f.genel_toplam, f.para_birimi)}</dd>
          </dl>

          {f.aciklama && (
            <p className="varlik-alt" style={{ whiteSpace: 'pre-wrap' }}>
              {f.aciklama}
            </p>
          )}

          <h3 className="bolum-baslik" style={{ marginTop: 24 }}>
            {t('finans.surec')}
          </h3>
          <DurumZamanCizelgesi
            adimlar={mutluYol}
            mevcut={f.durum}
            olumsuz={
              f.durum === 'iptal'
                ? { anahtar: 'iptal', baslik: t('finans.durum_iptal') }
                : undefined
            }
          />
          <p className="varlik-alt">
            {t('finans.efatura')}: <strong>{t(`finans.gib_${f.gib_durumu}`)}</strong> · ETTN{' '}
            <span className="sayisal">{f.ettn}</span>
          </p>
        </>
      )}

      <Modal
        open={nedenAksiyon != null}
        title={nedenAksiyon === 'iade' ? t('finans.iade_baslik') : t('finans.iptal_baslik')}
        okText={nedenAksiyon === 'iade' ? t('finans.iade_et') : t('finans.iptal_et')}
        okButtonProps={{ danger: nedenAksiyon === 'iptal', disabled: !neden.trim() }}
        cancelText={t('ortak.vazgec')}
        confirmLoading={aksiyon.isPending}
        onCancel={() => setNedenAksiyon(null)}
        onOk={async () => {
          if (!f || !nedenAksiyon) return;
          await aksiyon.mutateAsync({ id: f.id, aksiyon: nedenAksiyon, neden: neden.trim() });
          setNedenAksiyon(null);
        }}
      >
        <label htmlFor="fatura-neden" className="varlik-alt" style={{ display: 'block' }}>
          {t('finans.neden_zorunlu')}
        </label>
        <Input.TextArea
          id="fatura-neden"
          rows={3}
          maxLength={500}
          value={neden}
          onChange={(e) => setNeden(e.target.value)}
        />
      </Modal>
      <FaturaFormu acik={duzenle} kapat={() => setDuzenle(false)} duzenlenen={f} />
      <OdemeFormu acik={odemeAcik} kapat={() => setOdemeAcik(false)} fatura={f} />
    </Drawer>
  );
}
