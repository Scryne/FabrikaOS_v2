/**
 * Güvenlik ekranı (S23 / ADR-0022) — kişisel yüzey: izin gerekmez, oturum yeterli.
 *
 * İki panel:
 * 1. **İki aşamalı doğrulama** — kurulum sihirbazı (QR + kurtarma kodları) / kapatma
 *    (parola + kod ister; geri alınamaz olduğu için onay modalı).
 * 2. **Oturumlar & cihazlar** — aktif refresh oturumları; uzaktan sonlandırma. Mevcut
 *    oturumun hangisi olduğu istemcide bilinmez (jti sızdırılmaz) → "hepsini kapat"
 *    yerine satır bazlı sonlandırma sunulur, kullanıcı kendi cihazını IP/tarayıcıdan tanır.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LockOutlined, SafetyCertificateOutlined, StopOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App, Button, Form, Input, Modal, Space, Table, Tag, Typography } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { ApiHata } from '@/api/client';
import { ikiAsamaKapat, oturumlariGetir, oturumSonlandir, type OturumSatiri } from '@/api/kimlik';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import { IkiAsamaKurulum } from './IkiAsamaKurulum';

const OTURUM_ANAHTAR = ['kimlik-oturumlar'] as const;

function tarihYaz(deger: string | null | undefined): string {
  if (!deger) return '—';
  return new Date(deger).toLocaleString('tr-TR');
}

export function GuvenlikSayfasi() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const qc = useQueryClient();
  const kullanici = useAuthStore((s) => s.kullanici);
  const [kurulumAcik, setKurulumAcik] = useState(false);
  const [kapatmaAcik, setKapatmaAcik] = useState(false);
  const [form] = Form.useForm<{ parola: string; kod: string }>();

  const ikiAsamaAktif = kullanici?.iki_asama_aktif ?? false;

  const oturumlar = useQuery({
    queryKey: OTURUM_ANAHTAR,
    queryFn: oturumlariGetir,
  });

  const sonlandir = useMutation({
    mutationFn: oturumSonlandir,
    onSuccess: () => {
      message.success(t('guvenlik.oturum_sonlandirildi'));
      void qc.invalidateQueries({ queryKey: OTURUM_ANAHTAR });
    },
    onError: (hata: unknown) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });

  const kapat = useMutation({
    mutationFn: (d: { parola: string; kod: string }) => ikiAsamaKapat(d.parola, d.kod),
    onSuccess: () => {
      message.success(t('guvenlik.iki_asama_kapatildi'));
      setKapatmaAcik(false);
      form.resetFields();
      // ``ben`` yanıtındaki iki_asama_aktif değişti → oturum bilgisi tazelenmeli.
      window.location.reload();
    },
    onError: (hata: unknown) =>
      message.error(hata instanceof ApiHata ? hata.message : t('guvenlik.kod_hatali')),
  });

  const kolonlar: ColumnsType<OturumSatiri> = [
    {
      title: t('guvenlik.cihaz'),
      dataIndex: 'istemci',
      render: (istemci: string) => (
        <span style={{ fontSize: 12.5 }}>{istemci || t('guvenlik.bilinmeyen_cihaz')}</span>
      ),
    },
    {
      title: t('guvenlik.ip'),
      dataIndex: 'ip_adresi',
      width: 150,
      render: (ip: string | null) => <span className="sayisal">{ip ?? '—'}</span>,
    },
    {
      title: t('guvenlik.son_kullanim'),
      dataIndex: 'son_kullanim',
      width: 190,
      render: (deger: string | null) => <span className="sayisal">{tarihYaz(deger)}</span>,
    },
    {
      title: t('guvenlik.bitis'),
      dataIndex: 'bitis',
      width: 190,
      render: (deger: string) => <span className="sayisal">{tarihYaz(deger)}</span>,
    },
    {
      title: '',
      key: 'islem',
      width: 130,
      align: 'right',
      render: (_, kayit) => (
        <Button
          size="small"
          danger
          icon={<StopOutlined />}
          loading={sonlandir.isPending && sonlandir.variables === kayit.id}
          onClick={() => sonlandir.mutate(kayit.id)}
        >
          {t('guvenlik.sonlandir')}
        </Button>
      ),
    },
  ];

  return (
    <SayfaKapsayici enGenis={1000}>
      <SayfaBaslik baslik={t('guvenlik.baslik')} alt={t('guvenlik.aciklama')} />

      <Space direction="vertical" size={18} style={{ width: '100%' }}>
        <PanelKart
          baslik={t('guvenlik.iki_asama_baslik')}
          sag={
            ikiAsamaAktif ? (
              <Tag color="green">{t('guvenlik.etkin')}</Tag>
            ) : (
              <Tag>{t('guvenlik.etkin_degil')}</Tag>
            )
          }
        >
          {kurulumAcik ? (
            <IkiAsamaKurulum
              onTamamlandi={() => {
                setKurulumAcik(false);
                window.location.reload();
              }}
              onIptal={() => setKurulumAcik(false)}
            />
          ) : (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              <Typography.Paragraph style={{ marginBottom: 0, color: 'var(--metin-soluk)' }}>
                {ikiAsamaAktif ? t('guvenlik.aktif_aciklama') : t('guvenlik.pasif_aciklama')}
              </Typography.Paragraph>
              {ikiAsamaAktif ? (
                <Button danger icon={<LockOutlined />} onClick={() => setKapatmaAcik(true)}>
                  {t('guvenlik.iki_asama_kapat')}
                </Button>
              ) : (
                <Button
                  type="primary"
                  icon={<SafetyCertificateOutlined />}
                  onClick={() => setKurulumAcik(true)}
                >
                  {t('guvenlik.iki_asama_kur')}
                </Button>
              )}
            </Space>
          )}
        </PanelKart>

        <PanelKart baslik={t('guvenlik.oturumlar_baslik')} govdeDolgu={0}>
          <Table<OturumSatiri>
            rowKey="id"
            size="small"
            loading={oturumlar.isLoading}
            dataSource={oturumlar.data ?? []}
            columns={kolonlar}
            pagination={false}
          />
        </PanelKart>
      </Space>

      <Modal
        open={kapatmaAcik}
        title={t('guvenlik.iki_asama_kapat')}
        okText={t('guvenlik.kapat_onayla')}
        okButtonProps={{ danger: true, loading: kapat.isPending }}
        cancelText={t('ortak.iptal')}
        onCancel={() => setKapatmaAcik(false)}
        onOk={() => {
          void form.validateFields().then((d) => kapat.mutate(d));
        }}
        destroyOnHidden
      >
        <Typography.Paragraph type="secondary">{t('guvenlik.kapat_aciklama')}</Typography.Paragraph>
        <Form form={form} layout="vertical" requiredMark={false}>
          <Form.Item
            name="parola"
            label={t('kimlik.parola')}
            rules={[{ required: true, message: t('kimlik.parola_gerekli') }]}
          >
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Form.Item
            name="kod"
            label={t('guvenlik.dogrulama_kodu')}
            rules={[{ required: true, message: t('guvenlik.kod_gerekli') }]}
          >
            <Input className="sayisal" placeholder="123456" maxLength={12} />
          </Form.Item>
        </Form>
      </Modal>
    </SayfaKapsayici>
  );
}
