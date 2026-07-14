/**
 * Firma detayı (Drawer) — KPI şeridi (kontak sayısı / birincil kontak / durum) + künye
 * (Descriptions) + tedarikçi performans skoru (S-VB; yalnız tedarikçi tipinde) + ilgili
 * kişiler (baş harf avatarlı liste, birincil işaretli). ``crm:yaz`` varsa düzenleme.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { PlusOutlined } from '@ant-design/icons';
import { Avatar, Button, Descriptions, Drawer, List, Tag, Tooltip } from 'antd';

import { DetayIstatSira } from '@/components/DetayOgeleri';
import { OranSatiri } from '@/components/OranSatiri';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { FirmaFormu } from './FirmaFormu';
import { useFirma, useOrtaklar, useTedarikciSkoru } from './hooks';
import { OrtakFormu } from './OrtakFormu';
import { FirmaTipEtiketi } from './rozetler';

/** Skor bandı → semantik renk (85+ sağlıklı / 60+ izlenmeli / altı riskli). */
function skorRengi(skor: number): string {
  if (skor >= 85) return 'var(--basari)';
  if (skor >= 60) return 'var(--uyari)';
  return 'var(--hata)';
}

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
  const { data: skor } = useTedarikciSkoru(id ?? 0, firma?.tip === 'tedarikci');
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

          {firma.tip === 'tedarikci' && skor && (
            <>
              <div className="detay-bolum-baslik">
                {t('crm.skor_baslik')}
                {skor.yetersiz_veri.length > 0 && (
                  <Tooltip
                    title={`${t('crm.skor_yetersiz')}: ${skor.yetersiz_veri
                      .map((s) => t(`crm.skor_${s}`))
                      .join(', ')}`}
                  >
                    <Tag bordered={false} style={{ marginLeft: 8 }}>
                      {t('crm.skor_yetersiz')}
                    </Tag>
                  </Tooltip>
                )}
              </div>
              <div
                style={{
                  display: 'flex',
                  gap: 20,
                  alignItems: 'center',
                  padding: '14px 16px',
                  background: 'var(--yuzey-ust)',
                  border: '1px solid var(--kenarlik)',
                  borderRadius: 12,
                }}
              >
                <span
                  className="sayisal"
                  style={{
                    fontSize: 34,
                    fontWeight: 700,
                    color: skorRengi(skor.skor),
                    lineHeight: 1,
                    minWidth: 76,
                  }}
                >
                  {skor.skor.toFixed(0)}
                  <span style={{ fontSize: 13, color: 'var(--metin-soluk)', fontWeight: 400 }}>
                    /100
                  </span>
                </span>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <OranSatiri
                    etiket={t('crm.skor_kalite')}
                    yuzde={skor.kalite_gecme_orani * 100}
                    renk={skorRengi(skor.kalite_gecme_orani * 100)}
                  />
                  <OranSatiri
                    etiket={t('crm.skor_sozlesme')}
                    yuzde={skor.sozlesme_uyumu * 100}
                    renk={skorRengi(skor.sozlesme_uyumu * 100)}
                  />
                  <OranSatiri
                    etiket={t('crm.skor_talep')}
                    yuzde={skor.talep_cozum_orani * 100}
                    renk={skorRengi(skor.talep_cozum_orani * 100)}
                  />
                </div>
              </div>
            </>
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
