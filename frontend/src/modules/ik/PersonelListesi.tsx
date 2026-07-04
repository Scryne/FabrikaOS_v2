/**
 * Personel listesi — sunucu-taraflı tablo (sicil/ad soyad/departman/ünvan/TC maskeli/aktif) +
 * "yeni" (``ik:yaz``). Satır → personel detayına gider. TC yalnız maskeli görüntülenir (KVKK).
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Card, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';

import { type Personel, usePersoneller } from './hooks';
import { PersonelFormu } from './PersonelFormu';

export function PersonelListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = usePersoneller(param);
  const [formAcik, setFormAcik] = useState(false);

  const kolonlar: ColumnsType<Personel> = [
    {
      title: t('ik.sicil_no'),
      dataIndex: 'sicil_no',
      key: 'sicil_no',
      sorter: true,
      render: (v: string) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('ik.ad_soyad'),
      key: 'ad_soyad',
      sorter: true,
      render: (_v, k) => `${k.ad} ${k.soyad}`,
    },
    { title: t('ik.departman'), dataIndex: 'departman', key: 'departman', sorter: true },
    { title: t('ik.unvan'), dataIndex: 'unvan', key: 'unvan' },
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
        <Tag color={v ? 'success' : 'default'} bordered={false}>
          {v ? t('ik.aktif_evet') : t('ik.aktif_hayir')}
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.personeller')}
        alt={t('ik.personel_alt')}
        sag={
          yazabilir && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
              {t('ik.personel_yeni')}
            </Button>
          )
        }
      />
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
    </div>
  );
}
