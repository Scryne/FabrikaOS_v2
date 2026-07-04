/**
 * İzin talebi detayı (Drawer) — künye + durum rozeti + onay akışı aksiyonları.
 * Butonlar ``gecerliHedefler(durum)`` ∩ kullanıcı izni ile filtrelenir (görev ayrımı):
 * ``onayla``/``reddet`` yalnız ``ik:onay`` varsa görünür. Reddet ``red_nedeni`` sorar.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, Input, Modal, Space } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { useIzin, useIzinDurumAksiyon } from './hooks';
import { gecerliHedefler } from './izinDurum';
import { IzinDurumEtiketi, IzinTuruEtiketi } from './rozetler';

type Aksiyon = { aksiyon: string; izin: string; etiket: string };

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
      title={izin?.kod}
      extra={izin && <IzinDurumEtiketi durum={izin.durum} />}
    >
      {izin && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('ik.izin_turu')}>
              <IzinTuruEtiketi tur={izin.izin_turu} />
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.personel')}>
              <span className="sayisal">{izin.personel_id}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.baslangic')}>
              <span className="sayisal">{izin.baslangic_tarihi}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.bitis')}>
              <span className="sayisal">{izin.bitis_tarihi}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('ik.gun_sayisi')}>
              <span className="sayisal">{izin.gun_sayisi}</span>
            </Descriptions.Item>
            {izin.aciklama && (
              <Descriptions.Item label={t('ik.aciklama')}>{izin.aciklama}</Descriptions.Item>
            )}
            {izin.red_nedeni && (
              <Descriptions.Item label={t('ik.red_nedeni')}>{izin.red_nedeni}</Descriptions.Item>
            )}
          </Descriptions>
          <Space style={{ marginTop: 16 }} wrap>
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
