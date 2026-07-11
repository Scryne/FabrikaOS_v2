/**
 * Sözleşme detayı (Drawer) — KPI şeridi (tutar / kalan gün / süre ilerlemesi) + künye
 * (Descriptions) + **durum zaman çizelgesi** (taslak→aktif→sonlandı; fesih/iptal olumsuz
 * terminal) + durum geçiş butonları (``gecerliHedefler`` ∩ ``sozlesme:yaz``) + düzenle.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { CSSProperties } from 'react';
import { Button, Descriptions, Drawer, Space } from 'antd';
import dayjs from 'dayjs';

import { DetayIstatSira, DurumZamanCizelgesi } from '@/components/DetayOgeleri';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { gecerliHedefler } from './durum';
import { useSozlesme, useSozlesmeDurum } from './hooks';
import { SozlesmeDurumEtiketi } from './rozetler';
import { SozlesmeFormu } from './SozlesmeFormu';

const HAT = BOLUM_RENGI['menu.bolum_ticari'];
const CIZELGE = ['taslak', 'aktif', 'sonlandi'];

export function SozlesmeDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: sozlesme } = useSozlesme(id ?? 0);
  const durumMut = useSozlesmeDurum();
  const yazabilir = useAuthStore((s) => s.izinVar('sozlesme:yaz'));
  const [duzenle, setDuzenle] = useState(false);

  const hedefler = sozlesme && yazabilir ? gecerliHedefler(sozlesme.durum) : [];

  // Süre metrikleri — toplam gün, kalan gün, geçen oran (ilerleme çubuğu için).
  const bugun = dayjs().startOf('day');
  const baslangic = sozlesme ? dayjs(sozlesme.baslangic_tarihi) : bugun;
  const bitis = sozlesme ? dayjs(sozlesme.bitis_tarihi) : bugun;
  const toplamGun = Math.max(bitis.diff(baslangic, 'day'), 1);
  const kalanGun = bitis.diff(bugun, 'day');
  const gecenOran = Math.min(Math.max(bugun.diff(baslangic, 'day') / toplamGun, 0), 1);
  const suredoldu = kalanGun < 0;

  const olumsuz =
    sozlesme?.durum === 'feshedildi'
      ? { anahtar: 'feshedildi', baslik: t('sozlesme.asama_feshedildi') }
      : sozlesme?.durum === 'iptal'
        ? { anahtar: 'iptal', baslik: t('sozlesme.asama_iptal') }
        : undefined;

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={620}
      destroyOnHidden
      title={<span className="sayisal">{sozlesme?.kod}</span>}
      extra={sozlesme && <SozlesmeDurumEtiketi durum={sozlesme.durum} />}
    >
      {sozlesme && (
        <>
          <h3 style={{ margin: '0 0 16px', fontWeight: 600 }}>{sozlesme.baslik}</h3>

          <DetayIstatSira
            ogeler={[
              {
                anahtar: 'tutar',
                deger: (
                  <>
                    {sozlesme.tutar.toLocaleString('tr-TR')}{' '}
                    <span style={{ fontSize: 13, color: 'var(--metin-soluk)' }}>
                      {sozlesme.para_birimi}
                    </span>
                  </>
                ),
                etiket: t('sozlesme.tutar'),
              },
              {
                anahtar: 'kalan',
                deger: suredoldu ? t('sozlesme.ist_doldu') : kalanGun,
                etiket: suredoldu ? t('sozlesme.ist_kalan') : t('sozlesme.ist_kalan_gun'),
                ton: !suredoldu && kalanGun <= 30 ? RENKLER.uyari : undefined,
              },
              {
                anahtar: 'sure',
                deger: toplamGun,
                etiket: t('sozlesme.ist_sure'),
              },
            ]}
          />

          {sozlesme.durum === 'aktif' && (
            <div style={{ marginTop: 14 }}>
              <div
                className="detay-ilerleme"
                style={{ '--ilerleme-renk': HAT } as CSSProperties}
                role="progressbar"
                aria-valuenow={Math.round(gecenOran * 100)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <i style={{ transform: `scaleX(${gecenOran})` }} />
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginTop: 6,
                  fontSize: 11.5,
                  color: 'var(--metin-soluk)',
                }}
              >
                <span>{t('sozlesme.ist_ilerleme')}</span>
                <span className="sayisal">%{Math.round(gecenOran * 100)}</span>
              </div>
            </div>
          )}

          <div className="detay-bolum-baslik">{t('ortak.kunye')}</div>
          <Descriptions column={1} size="small" styles={{ label: { width: 130 } }}>
            <Descriptions.Item label={t('sozlesme.tur')}>
              {t(`sozlesme.tur_${sozlesme.tur}`)}
            </Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.firma')}>#{sozlesme.firma_id}</Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.baslangic')}>
              <span className="sayisal">
                {dayjs(sozlesme.baslangic_tarihi).format('DD.MM.YYYY')}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.bitis')}>
              <span className="sayisal">{dayjs(sozlesme.bitis_tarihi).format('DD.MM.YYYY')}</span>
            </Descriptions.Item>
            {sozlesme.aciklama && (
              <Descriptions.Item label={t('sozlesme.aciklama')}>
                {sozlesme.aciklama}
              </Descriptions.Item>
            )}
          </Descriptions>

          <div className="detay-bolum-baslik">{t('ortak.durum_akisi')}</div>
          <DurumZamanCizelgesi
            adimlar={CIZELGE.map((d) => ({ anahtar: d, baslik: t(`sozlesme.asama_${d}`) }))}
            mevcut={sozlesme.durum}
            olumsuz={olumsuz}
          />

          {(yazabilir || hedefler.length > 0) && (
            <Space style={{ marginTop: 20 }} wrap>
              {yazabilir && (
                <Button onClick={() => setDuzenle(true)}>{t('sozlesme.duzenle')}</Button>
              )}
              {hedefler.map((h) => (
                <Button
                  key={h}
                  type={h === 'aktif' ? 'primary' : 'default'}
                  danger={h === 'feshedildi' || h === 'iptal'}
                  loading={durumMut.isPending}
                  onClick={() => void durumMut.mutateAsync({ id: sozlesme.id, durum: h })}
                >
                  {t(`sozlesme.durum_${h}`)}
                </Button>
              ))}
            </Space>
          )}

          <SozlesmeFormu acik={duzenle} kapat={() => setDuzenle(false)} mevcut={sozlesme} />
        </>
      )}
    </Drawer>
  );
}
