/**
 * Talep detayı (Drawer) — künye + durum/öncelik rozetleri + durum geçiş butonları
 * (``gecerliHedefler`` ∩ ``talep:yaz``) + atama (InputNumber, ``talep:yaz``).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, InputNumber, Space } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { gecerliHedefler } from './durum';
import { useTalep, useTalepDurum, useTalepGuncelle } from './hooks';
import { TalepDurumEtiketi, TalepOncelikEtiketi } from './rozetler';

export function TalepDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: talep } = useTalep(id ?? 0);
  const durumMut = useTalepDurum();
  const guncelle = useTalepGuncelle();
  const yazabilir = useAuthStore((s) => s.izinVar('talep:yaz'));
  const [atanan, setAtanan] = useState<number | null>(null);

  const hedefler = talep && yazabilir ? gecerliHedefler(talep.durum) : [];

  const ata = async () => {
    if (!talep || atanan == null) return;
    await guncelle.mutateAsync({ id: talep.id, govde: { atanan_kullanici_id: atanan } });
    setAtanan(null);
  };

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={620}
      title={talep?.kod}
      extra={talep && <TalepDurumEtiketi durum={talep.durum} />}
    >
      {talep && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('talep.baslik')}>{talep.baslik}</Descriptions.Item>
            <Descriptions.Item label={t('talep.tur')}>
              {t(`talep.tur_${talep.tur}`)}
            </Descriptions.Item>
            <Descriptions.Item label={t('talep.oncelik')}>
              <TalepOncelikEtiketi oncelik={talep.oncelik} />
            </Descriptions.Item>
            <Descriptions.Item label={t('talep.firma')}>
              {talep.firma_id ? `#${talep.firma_id}` : '—'}
            </Descriptions.Item>
            <Descriptions.Item label={t('talep.atanan')}>
              {talep.atanan_kullanici_id ? `#${talep.atanan_kullanici_id}` : '—'}
            </Descriptions.Item>
            {talep.aciklama && (
              <Descriptions.Item label={t('talep.aciklama')}>{talep.aciklama}</Descriptions.Item>
            )}
          </Descriptions>

          {yazabilir && (
            <Space style={{ marginTop: 16 }}>
              <InputNumber
                min={1}
                value={atanan ?? undefined}
                onChange={(v) => setAtanan(v)}
                placeholder={t('talep.atanan_id')}
              />
              <Button
                loading={guncelle.isPending}
                onClick={() => void ata()}
                disabled={atanan == null}
              >
                {t('talep.ata')}
              </Button>
            </Space>
          )}

          <Space style={{ marginTop: 16 }} wrap>
            {hedefler.map((h) => (
              <Button
                key={h}
                type={h === 'cozuldu' || h === 'kapandi' ? 'primary' : 'default'}
                danger={h === 'iptal'}
                loading={durumMut.isPending}
                onClick={() => void durumMut.mutateAsync({ id: talep.id, durum: h })}
              >
                {t(`talep.durum_${h}`)}
              </Button>
            ))}
          </Space>
        </>
      )}
    </Drawer>
  );
}
