/**
 * Firma detayı (Drawer) — KPI şeridi (kontak sayısı / birincil kontak / durum) + künye
 * (Descriptions) + ilgili kişiler (baş harf avatarlı liste, birincil işaretli). ``crm:yaz``
 * varsa firmayı düzenle / kontak ekle.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Avatar, Button, Descriptions, Drawer, List, Tag } from 'antd';

import { DetayIstatSira } from '@/components/DetayOgeleri';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { FirmaFormu } from './FirmaFormu';
import { useFirma, useOrtaklar } from './hooks';
import { OrtakFormu } from './OrtakFormu';
import { FirmaTipEtiketi } from './rozetler';

function basHarf(ad: string): string {
  return (
    ad
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0])
      .join('')
      .toUpperCase() || '?'
  );
}

export function FirmaDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: firma } = useFirma(id ?? 0);
  const { data: ortaklar } = useOrtaklar(id ?? 0);
  const yazabilir = useAuthStore((s) => s.izinVar('crm:yaz'));
  const [duzenle, setDuzenle] = useState(false);
  const [ortakEkle, setOrtakEkle] = useState(false);

  const liste = ortaklar ?? [];
  const birincil = liste.find((o) => o.birincil);

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={620}
      destroyOnHidden
      title={firma?.ad}
      extra={firma && <FirmaTipEtiketi tip={firma.tip} />}
    >
      {firma && (
        <>
          <DetayIstatSira
            ogeler={[
              { anahtar: 'kontak', deger: liste.length, etiket: t('crm.ortaklar') },
              {
                anahtar: 'birincil',
                deger: birincil ? birincil.ad_soyad : '—',
                etiket: t('crm.ist_birincil'),
              },
              {
                anahtar: 'durum',
                deger: firma.aktif ? t('crm.aktif_evet') : t('crm.aktif_hayir'),
                etiket: t('crm.aktif'),
                ton: firma.aktif ? RENKLER.basari : RENKLER.metinSoluk,
              },
            ]}
          />

          <div className="detay-bolum-baslik">{t('ortak.kunye')}</div>
          <Descriptions column={1} size="small" styles={{ label: { width: 130 } }}>
            <Descriptions.Item label={t('crm.sektor')}>{firma.sektor || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('crm.il')}>{firma.il || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('crm.vergi_no')}>
              <span className="sayisal">{firma.vergi_no || '—'}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('crm.telefon')}>
              <span className="sayisal">{firma.telefon || '—'}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('crm.eposta')}>{firma.eposta || '—'}</Descriptions.Item>
          </Descriptions>

          {yazabilir && (
            <Button style={{ marginTop: 14 }} onClick={() => setDuzenle(true)}>
              {t('crm.firma_duzenle')}
            </Button>
          )}

          <div
            className="detay-bolum-baslik"
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>{t('crm.ortaklar')}</span>
            {yazabilir && (
              <Button size="small" icon={<PlusOutlined />} onClick={() => setOrtakEkle(true)}>
                {t('crm.yeni_ortak')}
              </Button>
            )}
          </div>
          <List
            size="small"
            dataSource={liste}
            locale={{ emptyText: t('crm.ortak_bos') }}
            renderItem={(o) => (
              <List.Item>
                <List.Item.Meta
                  avatar={
                    <Avatar style={{ background: 'var(--yuzey-ust)', color: 'var(--metin)' }}>
                      {basHarf(o.ad_soyad)}
                    </Avatar>
                  }
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
