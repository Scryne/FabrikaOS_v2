/**
 * Personeller çalışma alanı — KPI şeridi (İK özeti) + zengin tablo: avatar varlık hücresi
 * (ad soyad + unvan) · departman · **maskeli TC** (mono; maskeleme sunucuda — KVKK) · durum pimi.
 * Satır → personel detayı. "Yeni personel" yalnız ``ik:yaz``.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  CalendarOutlined,
  IdcardOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { Avatar, Button, Card, Space } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { DurumPim } from '@/components/DurumPim';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { type Personel, useIkOzet, usePersoneller } from './hooks';
import { PersonelFormu } from './PersonelFormu';

const HAT = BOLUM_RENGI['menu.bolum_isg_ik'];

function basHarf(ad: string, soyad: string): string {
  return `${ad[0] ?? ''}${soyad[0] ?? ''}`.toUpperCase() || '?';
}

export function PersonelListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = usePersoneller(param);
  const { data: ozet, isPending: ozetYukleniyor } = useIkOzet();
  const [formAcik, setFormAcik] = useState(false);

  const metrikler: OzetMetrik[] = ozet
    ? [
        {
          anahtar: 'aktif',
          baslik: t('ik.kpi_aktif'),
          deger: String(ozet.aktif_personel),
          ikon: <TeamOutlined />,
        },
        {
          anahtar: 'izinli',
          baslik: t('ik.kpi_izinli'),
          deger: String(ozet.bugun_izinli),
          ikon: <CalendarOutlined />,
        },
        {
          anahtar: 'sertifika',
          baslik: t('ik.kpi_sertifika'),
          deger: String(ozet.yaklasan_sertifika),
          ikon: <SafetyCertificateOutlined />,
        },
        {
          anahtar: 'zimmet',
          baslik: t('ik.kpi_zimmet'),
          deger: String(ozet.acik_zimmet),
          ikon: <IdcardOutlined />,
        },
      ]
    : [];

  const kolonlar: ColumnsType<Personel> = [
    {
      title: t('ik.ad_soyad'),
      key: 'ad_soyad',
      sorter: true,
      render: (_v, k) => (
        <span className="varlik-hucre">
          <Avatar
            size={34}
            style={{
              backgroundColor: 'rgba(245,158,11,0.16)',
              color: HAT,
              fontWeight: 600,
              flexShrink: 0,
            }}
          >
            {basHarf(k.ad, k.soyad)}
          </Avatar>
          <span>
            <span className="varlik-ad" style={{ display: 'block' }}>
              {k.ad} {k.soyad}
            </span>
            <span className="varlik-alt">{k.unvan || '—'}</span>
          </span>
        </span>
      ),
    },
    { title: t('ik.departman'), dataIndex: 'departman', key: 'departman', sorter: true },
    {
      title: t('ik.sicil_no'),
      dataIndex: 'sicil_no',
      key: 'sicil_no',
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.tc_kimlik_no'),
      dataIndex: 'tc_kimlik_no',
      key: 'tc_kimlik_no',
      render: (v: string) => <span className="sayisal">{v || '—'}</span>,
    },
    {
      title: t('ik.aktif'),
      dataIndex: 'aktif',
      key: 'aktif',
      render: (v: boolean) => (
        <DurumPim
          renk={v ? RENKLER.basari : RENKLER.metinSoluk}
          etiket={v ? t('ik.aktif_evet') : t('ik.aktif_hayir')}
          solgun={!v}
        />
      ),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.personeller')}
        alt={t('ik.personel_alt')}
        sag={
          <Space wrap>
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('ik.personel_yeni')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={ozetYukleniyor} />

      <div style={{ height: 20 }} />

      <Card styles={{ body: { padding: 18 } }}>
        <SunucuTablo<Personel>
          kolonlar={kolonlar}
          veri={data?.veri ?? []}
          meta={data?.meta}
          yukleniyor={isPending}
          param={param}
          paramDegistir={paramDegistir}
          rowKey="id"
          aramaYer={t('ik.personel_ara')}
          bosMetin={isError ? t('ortak.hata_baslik') : t('ik.personel_bos')}
          onRow={(kayit) => ({
            onClick: () => navigate(`/personeller/${kayit.id}`),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
      <PersonelFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
