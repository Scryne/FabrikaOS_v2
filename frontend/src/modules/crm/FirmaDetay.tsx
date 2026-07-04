/**
 * Firma detayı (Drawer) — künye + ortak (kontak) listesi. ``crm:yaz`` varsa düzenle/ortak ekle.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Button, Descriptions, Drawer, List, Space, Tag } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { FirmaFormu } from './FirmaFormu';
import { useFirma, useOrtaklar } from './hooks';
import { OrtakFormu } from './OrtakFormu';
import { FirmaTipEtiketi } from './rozetler';

export function FirmaDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: firma } = useFirma(id ?? 0);
  const { data: ortaklar } = useOrtaklar(id ?? 0);
  const yazabilir = useAuthStore((s) => s.izinVar('crm:yaz'));
  const [duzenle, setDuzenle] = useState(false);
  const [ortakEkle, setOrtakEkle] = useState(false);

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={620}
      title={firma?.ad}
      extra={firma && <FirmaTipEtiketi tip={firma.tip} />}
    >
      {firma && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('crm.sektor')}>{firma.sektor || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('crm.il')}>{firma.il || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('crm.vergi_no')}>{firma.vergi_no || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('crm.telefon')}>{firma.telefon || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('crm.eposta')}>{firma.eposta || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('crm.aktif')}>
              <Tag color={firma.aktif ? 'success' : 'default'} bordered={false}>
                {firma.aktif ? t('crm.aktif_evet') : t('crm.aktif_hayir')}
              </Tag>
            </Descriptions.Item>
          </Descriptions>

          {yazabilir && (
            <Space style={{ marginTop: 16 }}>
              <Button onClick={() => setDuzenle(true)}>{t('crm.firma_duzenle')}</Button>
            </Space>
          )}

          <div
            style={{
              marginTop: 24,
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <h4 style={{ margin: 0 }}>{t('crm.ortaklar')}</h4>
            {yazabilir && (
              <Button size="small" icon={<PlusOutlined />} onClick={() => setOrtakEkle(true)}>
                {t('crm.yeni_ortak')}
              </Button>
            )}
          </div>
          <List
            style={{ marginTop: 8 }}
            size="small"
            bordered
            dataSource={ortaklar ?? []}
            locale={{ emptyText: t('crm.ortak_bos') }}
            renderItem={(o) => (
              <List.Item>
                <List.Item.Meta
                  title={
                    <span>
                      {o.ad_soyad}{' '}
                      {o.birincil && (
                        <Tag color="blue" bordered={false}>
                          {t('crm.birincil')}
                        </Tag>
                      )}
                    </span>
                  }
                  description={[o.unvan, o.telefon, o.eposta].filter(Boolean).join(' · ') || '—'}
                />
              </List.Item>
            )}
          />

          <FirmaFormu acik={duzenle} kapat={() => setDuzenle(false)} mevcut={firma} />
          <OrtakFormu acik={ortakEkle} kapat={() => setOrtakEkle(false)} firmaId={firma.id} />
        </>
      )}
    </Drawer>
  );
}
