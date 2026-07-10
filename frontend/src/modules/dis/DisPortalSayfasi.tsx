/**
 * Dış self-servis portal `/dis` — kabuksuz hafif kabuk (uiplani §11.1):
 * sidebar YOK; üst bar = marka + firma adı (tenant markalama alanı) + çıkış;
 * sekmeler: Taleplerim · Yeni Talep. Durum adları müşteri dilindedir
 * (`dis.durum_*`); talep detayında durum zaman çizelgesi (Steps) gösterilir.
 *
 * Aynı antrasit ailenin sadeleştirilmiş tek-modül kabuğu — iç kabuk (menü, komut
 * paleti, bildirim) bilinçli olarak yoktur; dış kullanıcının tek yüzeyi budur.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LogoutOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Card, Drawer, Form, Input, Select, Steps, Tag, Tabs } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useNavigate } from 'react-router-dom';

import { cikisYap } from '@/api/kimlik';
import { LogoIsareti } from '@/components/Marka';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { type DisTalep, useDisDurum, useDisTalepler, useDisTalepOlustur } from './hooks';

const DURUM_RENGI: Record<string, string> = {
  acik: RENKLER.uyari,
  inceleniyor: RENKLER.mavi,
  cozuldu: RENKLER.basari,
  kapandi: RENKLER.metinSoluk,
  iptal: RENKLER.hata,
};

// Durum zaman çizelgesi sırası (iptal ayrı ele alınır — akış dışı terminal).
const DURUM_SIRASI = ['acik', 'inceleniyor', 'cozuldu', 'kapandi'] as const;

const TURLER = ['teklif', 'destek', 'sikayet', 'bilgi', 'diger'] as const;
const ONCELIKLER = ['dusuk', 'orta', 'yuksek'] as const;

function DurumEtiketi({ durum }: { durum: string }) {
  const { t } = useTranslation();
  return (
    <Tag bordered={false} style={{ color: DURUM_RENGI[durum], fontWeight: 600 }}>
      {t(`dis.durum_${durum}`, durum)}
    </Tag>
  );
}

/** Talep detayı: açıklama + müşteri-dili durum zaman çizelgesi. */
function TalepDetayCekmece({ talep, kapat }: { talep: DisTalep | null; kapat: () => void }) {
  const { t } = useTranslation();
  const indeks = talep ? DURUM_SIRASI.indexOf(talep.durum as (typeof DURUM_SIRASI)[number]) : -1;

  return (
    <Drawer
      open={talep !== null}
      onClose={kapat}
      title={talep ? `${talep.kod} · ${talep.baslik}` : ''}
      width={440}
    >
      {talep && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div>
            <DurumEtiketi durum={talep.durum} />
            <span style={{ color: 'var(--metin-soluk)', fontSize: 12, marginLeft: 8 }}>
              {new Date(talep.olusturma_tarihi).toLocaleString('tr-TR')}
            </span>
          </div>
          {talep.aciklama && <p style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{talep.aciklama}</p>}
          {talep.durum === 'iptal' ? (
            <Tag bordered={false} style={{ color: RENKLER.hata, alignSelf: 'flex-start' }}>
              {t('dis.durum_iptal')}
            </Tag>
          ) : (
            <Steps
              direction="vertical"
              size="small"
              current={indeks}
              items={DURUM_SIRASI.map((d) => ({ title: t(`dis.durum_${d}`) }))}
            />
          )}
        </div>
      )}
    </Drawer>
  );
}

function Taleplerim() {
  const { t } = useTranslation();
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useDisTalepler(param);
  const [secili, setSecili] = useState<DisTalep | null>(null);

  const kolonlar: ColumnsType<DisTalep> = [
    {
      title: t('dis.kod'),
      dataIndex: 'kod',
      key: 'kod',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    { title: t('dis.baslik'), dataIndex: 'baslik', key: 'baslik' },
    {
      title: t('dis.tur'),
      dataIndex: 'tur',
      key: 'tur',
      render: (v: string) => <Tag bordered={false}>{t(`dis.tur_${v}`, v)}</Tag>,
    },
    {
      title: t('dis.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (durum: string) => <DurumEtiketi durum={durum} />,
    },
    {
      title: t('dis.tarih'),
      dataIndex: 'olusturma_tarihi',
      key: 'olusturma_tarihi',
      render: (v: string) => (
        <span className="sayisal">{new Date(v).toLocaleDateString('tr-TR')}</span>
      ),
    },
  ];

  return (
    <>
      <SunucuTablo<DisTalep>
        kolonlar={kolonlar}
        veri={data?.veri ?? []}
        meta={data?.meta}
        yukleniyor={isPending}
        param={param}
        paramDegistir={paramDegistir}
        rowKey="id"
        onRow={(kayit) => ({ onClick: () => setSecili(kayit), style: { cursor: 'pointer' } })}
        bosMetin={isError ? t('ortak.hata_baslik') : t('dis.talep_bos')}
      />
      <TalepDetayCekmece talep={secili} kapat={() => setSecili(null)} />
    </>
  );
}

function YeniTalep({ tamamlandi }: { tamamlandi: () => void }) {
  const { t } = useTranslation();
  const [form] = Form.useForm();
  const olustur = useDisTalepOlustur();

  const gonder = async () => {
    const v = (await form.validateFields()) as {
      baslik: string;
      aciklama?: string;
      tur: string;
      oncelik: string;
    };
    await olustur.mutateAsync({ ...v, aciklama: v.aciklama ?? '' });
    form.resetFields();
    tamamlandi();
  };

  return (
    <Form
      form={form}
      layout="vertical"
      requiredMark="optional"
      style={{ maxWidth: 560 }}
      initialValues={{ tur: 'destek', oncelik: 'orta' }}
    >
      <Form.Item name="baslik" label={t('dis.baslik')} rules={[{ required: true }]}>
        <Input maxLength={200} placeholder={t('dis.baslik_ornek')} />
      </Form.Item>
      <Form.Item name="aciklama" label={t('dis.aciklama')}>
        <Input.TextArea rows={5} maxLength={2000} showCount />
      </Form.Item>
      <Form.Item name="tur" label={t('dis.tur')}>
        <Select options={TURLER.map((v) => ({ value: v, label: t(`dis.tur_${v}`) }))} />
      </Form.Item>
      <Form.Item name="oncelik" label={t('dis.oncelik')}>
        <Select options={ONCELIKLER.map((v) => ({ value: v, label: t(`dis.oncelik_${v}`) }))} />
      </Form.Item>
      <Button
        type="primary"
        icon={<PlusOutlined />}
        loading={olustur.isPending}
        onClick={() => void gonder()}
      >
        {t('dis.gonder')}
      </Button>
    </Form>
  );
}

export function DisPortalSayfasi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const kullanici = useAuthStore((s) => s.kullanici);
  const { data: durum } = useDisDurum();
  const [aktifSekme, setAktifSekme] = useState('taleplerim');

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Üst bar: marka + firma (tenant markalama alanı) + kullanıcı/çıkış */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          padding: '14px 28px',
          borderBottom: '1px solid var(--cizgi, rgba(148,163,184,0.15))',
        }}
      >
        <LogoIsareti boyut={28} />
        <div>
          <div style={{ fontWeight: 700, lineHeight: 1.2 }}>{t('dis.portal_baslik')}</div>
          <div style={{ fontSize: 12, color: 'var(--metin-soluk)' }}>{durum?.firma_ad ?? '…'}</div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          {durum && (
            <span style={{ fontSize: 13, color: 'var(--metin-soluk)' }}>
              {t('dis.acik_talep', { adet: durum.acik })}
            </span>
          )}
          <span style={{ fontSize: 13 }}>{kullanici?.ad_soyad || kullanici?.eposta}</span>
          <Button
            size="small"
            icon={<LogoutOutlined />}
            onClick={() => {
              void cikisYap().then(() => navigate('/giris', { replace: true }));
            }}
          >
            {t('ortak.cikis')}
          </Button>
        </div>
      </header>

      <main style={{ width: '100%', maxWidth: 960, margin: '0 auto', padding: '24px 20px' }}>
        <Card styles={{ body: { padding: 18 } }}>
          <Tabs
            activeKey={aktifSekme}
            onChange={setAktifSekme}
            items={[
              { key: 'taleplerim', label: t('dis.taleplerim'), children: <Taleplerim /> },
              {
                key: 'yeni',
                label: t('dis.yeni_talep'),
                children: <YeniTalep tamamlandi={() => setAktifSekme('taleplerim')} />,
              },
            ]}
          />
        </Card>
      </main>
    </div>
  );
}
