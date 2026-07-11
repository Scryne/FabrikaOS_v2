/**
 * İzin talebi detayı (Drawer) — KPI şeridi (gün / tür / personel) + künye (Descriptions) +
 * **onay akışı çizelgesi** (taslak→onay bekliyor→onaylandı; reddedildi/iptal olumsuz terminal)
 * + onay aksiyonları. Butonlar ``gecerliHedefler(durum)`` ∩ kullanıcı izni ile filtrelenir
 * (görev ayrımı): ``onayla``/``reddet`` yalnız ``ik:onay`` varsa görünür. Reddet ``red_nedeni`` sorar.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, Input, Modal, Space } from 'antd';

import { DetayIstatSira, DurumZamanCizelgesi } from '@/components/DetayOgeleri';
import { useAuthStore } from '@/store/authStore';

import { useIzin, useIzinDurumAksiyon } from './hooks';
import { gecerliHedefler } from './izinDurum';
import { IzinDurumEtiketi, IzinTuruEtiketi } from './rozetler';

type Aksiyon = { aksiyon: string; izin: string; etiket: string };

const CIZELGE = ['taslak', 'onay_bekliyor', 'onaylandi'];

const HEDEF_AKSIYON: Record<string, Aksiyon> = {
  onay_bekliyor: { aksiyon: 'gonder', izin: 'ik:yaz', etiket: 'ik.gonder' },
  onaylandi: { aksiyon: 'onayla', izin: 'ik:onay', etiket: 'ik.onayla' },
  reddedildi: { aksiyon: 'reddet', izin: 'ik:onay', etiket: 'ik.reddet' },
  iptal: { aksiyon: 'iptal', izin: 'ik:yaz', etiket: 'ik.iptal' },
};

export function IzinDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: izin } = useIzin(id ?? 0);
  const aksiyonMut = useIzinDurumAksiyon();
  const izinVar = useAuthStore((s) => s.izinVar);
  const [redAcik, setRedAcik] = useState(false);
  const [redNeden, setRedNeden] = useState('');

  const hedefler = izin ? gecerliHedefler(izin.durum) : [];
  const butonlar = hedefler
    .map((h) => HEDEF_AKSIYON[h])
    .filter((a): a is Aksiyon => a != null && izinVar(a.izin));

  // Olumsuz terminal (reddedildi/iptal) → çizelgede mutlu yol kesilir.
  const olumsuz =
    izin?.durum === 'reddedildi'
      ? { anahtar: 'reddedildi', baslik: t('ik.durum_reddedildi') }
      : izin?.durum === 'iptal'
        ? { anahtar: 'iptal', baslik: t('ik.durum_iptal') }
        : undefined;

  const calistir = async (aksiyon: string) => {
    if (!izin) return;
    if (aksiyon === 'reddet') {
      setRedAcik(true);
      return;
    }
    await aksiyonMut.mutateAsync({ id: izin.id, aksiyon });
  };

  const redGonder = async () => {
    if (!izin) return;
    await aksiyonMut.mutateAsync({ id: izin.id, aksiyon: 'reddet', red_nedeni: redNeden });
    setRedAcik(false);
    setRedNeden('');
  };

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={560}
      destroyOnHidden
      title={<span className="sayisal">{izin?.kod}</span>}
      extra={izin && <IzinDurumEtiketi durum={izin.durum} />}
    >
      {izin && (
        <>
          <DetayIstatSira
            ogeler={[
              {
                anahtar: 'gun',
                deger: izin.gun_sayisi,
                etiket: t('ik.gun_sayisi'),
              },
              {
                anahtar: 'tur',
                deger: t(`ik.izin_turu_${izin.izin_turu}`),
                etiket: t('ik.izin_turu'),
              },
              {
                anahtar: 'personel',
                deger: `#${izin.personel_id}`,
                etiket: t('ik.personel'),
              },
            ]}
          />

          <div className="detay-bolum-baslik">{t('ortak.kunye')}</div>
          <Descriptions column={1} size="small" styles={{ label: { width: 130 } }}>
            <Descriptions.Item label={t('ik.izin_turu')}>
              <IzinTuruEtiketi tur={izin.izin_turu} />
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.baslangic')}>
              <span className="sayisal">{izin.baslangic_tarihi}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.bitis')}>
              <span className="sayisal">{izin.bitis_tarihi}</span>
            </Descriptions.Item>
            {izin.aciklama && (
              <Descriptions.Item label={t('ik.aciklama')}>{izin.aciklama}</Descriptions.Item>
            )}
            {izin.red_nedeni && (
              <Descriptions.Item label={t('ik.red_nedeni')}>{izin.red_nedeni}</Descriptions.Item>
            )}
          </Descriptions>

          <div className="detay-bolum-baslik">{t('ortak.durum_akisi')}</div>
          <DurumZamanCizelgesi
            adimlar={CIZELGE.map((d) => ({ anahtar: d, baslik: t(`ik.durum_${d}`) }))}
            mevcut={izin.durum}
            olumsuz={olumsuz}
          />

          {butonlar.length > 0 && (
            <Space style={{ marginTop: 20 }} wrap>
              {butonlar.map((a) => (
                <Button
                  key={a.aksiyon}
                  type={a.aksiyon === 'onayla' ? 'primary' : 'default'}
                  danger={a.aksiyon === 'reddet'}
                  loading={aksiyonMut.isPending}
                  onClick={() => void calistir(a.aksiyon)}
                >
                  {t(a.etiket)}
                </Button>
              ))}
            </Space>
          )}
          <Modal
            open={redAcik}
            onCancel={() => setRedAcik(false)}
            onOk={() => void redGonder()}
            title={t('ik.red_baslik')}
            okText={t('ortak.kaydet')}
            cancelText={t('ortak.iptal')}
            confirmLoading={aksiyonMut.isPending}
          >
            <Input.TextArea
              rows={3}
              value={redNeden}
              onChange={(e) => setRedNeden(e.target.value)}
              placeholder={t('ik.red_nedeni')}
            />
          </Modal>
        </>
      )}
    </Drawer>
  );
}
