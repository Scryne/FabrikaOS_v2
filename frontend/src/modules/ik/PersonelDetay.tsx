/**
 * Personel detay sayfası — özlük künyesi (KVKK: TC maskeli) + sekmeler: fazla mesai / zimmet /
 * sertifika (her biri alt-liste + "ekle"). Başlıkta "izin talebi oluştur" (personel önseçili).
 * Yazma aksiyonları ``ik:yaz``; fazla mesai onayı ``ik:onay``.
 */

import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeftOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  InboxOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import { Button, Descriptions, Skeleton, Space, Table, Tabs, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
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

const HAT = '#f59e0b';

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
  // Alt-listeler KPI şeridi için üstte de çekilir (sekmelerle aynı anahtar → React Query dedup).
  const mesailer = useMesailer(id);
  const zimmetler = useZimmetler(id);
  const sertifikalar = useSertifikalar(id);
  const [izinAcik, setIzinAcik] = useState(false);

  const onayliMesai = (mesailer.data ?? []).filter((m) => m.onayli).reduce((a, m) => a + m.saat, 0);
  const acikZimmet = (zimmetler.data ?? []).filter((z) => z.durum === 'zimmetli').length;
  const sertifikaSayisi = (sertifikalar.data ?? []).length;

  const ozetMetrikler: OzetMetrik[] = [
    {
      anahtar: 'izin',
      baslik: t('ik.kpi_izin'),
      deger: String(personel?.yillik_izin_hakki ?? 0),
      birim: t('ik.birim_gun'),
      ikon: <CalendarOutlined />,
    },
    {
      anahtar: 'mesai',
      baslik: t('ik.kpi_mesai'),
      deger: String(onayliMesai),
      birim: t('ik.birim_saat'),
      ikon: <ClockCircleOutlined />,
    },
    {
      anahtar: 'zimmet',
      baslik: t('ik.kpi_zimmet'),
      deger: String(acikZimmet),
      ikon: <InboxOutlined />,
    },
    {
      anahtar: 'sertifika',
      baslik: t('ik.sekme_sertifika'),
      deger: String(sertifikaSayisi),
      ikon: <SafetyCertificateOutlined />,
    },
  ];

  return (
    <SayfaKapsayici enGenis={1160}>
      <SayfaBaslik
        baslik={
          <Space size={12} align="center" wrap>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/personeller')}
              aria-label={t('ortak.geri')}
            />
            <span>{personel ? `${personel.ad} ${personel.soyad}` : t('menu.personeller')}</span>
            {personel?.unvan && (
              <Tag bordered={false} style={{ fontWeight: 400 }}>
                {personel.unvan}
              </Tag>
            )}
            {personel && !personel.aktif && <Tag bordered={false}>{t('ik.aktif_hayir')}</Tag>}
          </Space>
        }
        alt={personel?.sicil_no}
        sag={
          yazabilir &&
          personel && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setIzinAcik(true)}>
              {t('ik.izin_yeni')}
            </Button>
          )
        }
      />

      <div style={{ marginBottom: 16 }}>
        <OzetSerit metrikler={ozetMetrikler} renk={HAT} yukleniyor={isPending} />
      </div>

      <PanelKart baslik={t('ik.kunye')} renk={HAT}>
        {isPending || !personel ? (
          <Skeleton active paragraph={{ rows: 4 }} />
        ) : (
          <Descriptions column={{ xs: 1, sm: 2, md: 3 }} size="small">
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
            <Descriptions.Item label={t('ik.aktif')}>
              <Tag color={personel.aktif ? 'success' : 'default'} bordered={false}>
                {personel.aktif ? t('ik.aktif_evet') : t('ik.aktif_hayir')}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
        )}
      </PanelKart>

      {personel && (
        <div style={{ marginTop: 16 }}>
          <PanelKart renk={HAT} govdeDolgu={16}>
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
          </PanelKart>
        </div>
      )}
      <IzinFormu acik={izinAcik} kapat={() => setIzinAcik(false)} personelId={id} />
    </SayfaKapsayici>
  );
}
