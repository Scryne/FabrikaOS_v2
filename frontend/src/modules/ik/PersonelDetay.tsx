/**
 * Personel detay sayfası — özlük künyesi (KVKK: TC maskeli) + sekmeler: fazla mesai / zimmet /
 * sertifika (her biri alt-liste + "ekle"). Başlıkta "izin talebi oluştur" (personel önseçili).
 * Yazma aksiyonları ``ik:yaz``; fazla mesai onayı ``ik:onay``.
 */

import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeftOutlined, PlusOutlined } from '@ant-design/icons';
import { Button, Card, Descriptions, Space, Table, Tabs, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { useAuthStore } from '@/store/authStore';

import { MesaiFormu, SertifikaFormu, ZimmetFormu } from './AltKayitFormlari';
import {
  type FazlaMesai,
  type Sertifika,
  type Zimmet,
  useMesaiOnayla,
  useMesailer,
  usePersonel,
  useSertifikalar,
  useZimmetIade,
  useZimmetler,
} from './hooks';
import { IzinFormu } from './IzinFormu';
import { ZimmetDurumEtiketi } from './rozetler';

function MesaiSekmesi({ personelId }: { personelId: number }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const onaylayabilir = useAuthStore((s) => s.izinVar('ik:onay'));
  const { data } = useMesailer(personelId);
  const onayla = useMesaiOnayla();
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<FazlaMesai> = [
    { title: t('ik.tarih'), dataIndex: 'tarih', key: 'tarih' },
    {
      title: t('ik.saat'),
      dataIndex: 'saat',
      key: 'saat',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    { title: t('ik.aciklama'), dataIndex: 'aciklama', key: 'aciklama' },
    {
      title: t('ik.onayli'),
      dataIndex: 'onayli',
      key: 'onayli',
      render: (v: boolean, k) =>
        v ? (
          <Tag color="success" bordered={false}>
            {t('ik.onayli_evet')}
          </Tag>
        ) : onaylayabilir ? (
          <Button
            size="small"
            loading={onayla.isPending}
            onClick={() => void onayla.mutateAsync({ id: k.id, personelId })}
          >
            {t('ik.onayla')}
          </Button>
        ) : (
          <Tag bordered={false}>{t('ik.onayli_hayir')}</Tag>
        ),
    },
  ];

  return (
    <>
      {yazabilir && (
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          style={{ marginBottom: 12 }}
          onClick={() => setFormAcik(true)}
        >
          {t('ik.mesai_yeni')}
        </Button>
      )}
      <Table<FazlaMesai>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={data ?? []}
        columns={kolonlar}
      />
      <MesaiFormu acik={formAcik} kapat={() => setFormAcik(false)} personelId={personelId} />
    </>
  );
}

function ZimmetSekmesi({ personelId }: { personelId: number }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const { data } = useZimmetler(personelId);
  const iade = useZimmetIade();
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Zimmet> = [
    { title: t('ik.demirbas'), dataIndex: 'demirbas', key: 'demirbas' },
    { title: t('ik.seri_no'), dataIndex: 'seri_no', key: 'seri_no' },
    { title: t('ik.zimmet_tarihi'), dataIndex: 'zimmet_tarihi', key: 'zimmet_tarihi' },
    {
      title: t('ik.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (v: string, k) => (
        <Space>
          <ZimmetDurumEtiketi durum={v} />
          {yazabilir && v === 'zimmetli' && (
            <Button
              size="small"
              loading={iade.isPending}
              onClick={() => void iade.mutateAsync({ id: k.id, personelId })}
            >
              {t('ik.iade')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      {yazabilir && (
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          style={{ marginBottom: 12 }}
          onClick={() => setFormAcik(true)}
        >
          {t('ik.zimmet_yeni')}
        </Button>
      )}
      <Table<Zimmet>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={data ?? []}
        columns={kolonlar}
      />
      <ZimmetFormu acik={formAcik} kapat={() => setFormAcik(false)} personelId={personelId} />
    </>
  );
}

function SertifikaSekmesi({ personelId }: { personelId: number }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const { data } = useSertifikalar(personelId);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Sertifika> = [
    { title: t('ik.sertifika_ad'), dataIndex: 'ad', key: 'ad' },
    { title: t('ik.kurum'), dataIndex: 'kurum', key: 'kurum' },
    { title: t('ik.alinma_tarihi'), dataIndex: 'alinma_tarihi', key: 'alinma_tarihi' },
    {
      title: t('ik.gecerlilik_tarihi'),
      dataIndex: 'gecerlilik_tarihi',
      key: 'gecerlilik_tarihi',
      render: (v: string | null) => v ?? '—',
    },
  ];

  return (
    <>
      {yazabilir && (
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          style={{ marginBottom: 12 }}
          onClick={() => setFormAcik(true)}
        >
          {t('ik.sertifika_yeni')}
        </Button>
      )}
      <Table<Sertifika>
        rowKey="id"
        size="small"
        pagination={false}
        dataSource={data ?? []}
        columns={kolonlar}
      />
      <SertifikaFormu acik={formAcik} kapat={() => setFormAcik(false)} personelId={personelId} />
    </>
  );
}

export function PersonelDetay() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const params = useParams();
  const id = Number(params.id);
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const { data: personel, isPending } = usePersonel(id);
  const [izinAcik, setIzinAcik] = useState(false);

  return (
    <div style={{ maxWidth: 1100 }}>
      <SayfaBaslik
        baslik={personel ? `${personel.ad} ${personel.soyad}` : t('menu.personeller')}
        alt={personel?.sicil_no}
        sag={
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/personeller')}>
              {t('ortak.geri')}
            </Button>
            {yazabilir && personel && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setIzinAcik(true)}>
                {t('ik.izin_yeni')}
              </Button>
            )}
          </Space>
        }
      />
      <Card loading={isPending} styles={{ body: { padding: 18 } }}>
        {personel && (
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label={t('ik.sicil_no')}>
              <span className="sayisal">{personel.sicil_no}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.tc_kimlik_no')}>
              <span className="sayisal">{personel.tc_kimlik_no || '—'}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.departman')}>
              {personel.departman || '—'}
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.unvan')}>{personel.unvan || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('ik.telefon')}>{personel.telefon || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('ik.eposta')}>{personel.eposta || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('ik.ise_giris_tarihi')}>
              {personel.ise_giris_tarihi ?? '—'}
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.yillik_izin_hakki')}>
              <span className="sayisal">{personel.yillik_izin_hakki}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.aktif')}>
              <Tag color={personel.aktif ? 'success' : 'default'} bordered={false}>
                {personel.aktif ? t('ik.aktif_evet') : t('ik.aktif_hayir')}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>
      {personel && (
        <Card style={{ marginTop: 16 }} styles={{ body: { padding: 18 } }}>
          <Tabs
            items={[
              {
                key: 'mesai',
                label: t('ik.sekme_mesai'),
                children: <MesaiSekmesi personelId={id} />,
              },
              {
                key: 'zimmet',
                label: t('ik.sekme_zimmet'),
                children: <ZimmetSekmesi personelId={id} />,
              },
              {
                key: 'sertifika',
                label: t('ik.sekme_sertifika'),
                children: <SertifikaSekmesi personelId={id} />,
              },
            ]}
          />
        </Card>
      )}
      <IzinFormu acik={izinAcik} kapat={() => setIzinAcik(false)} personelId={id} />
    </div>
  );
}
