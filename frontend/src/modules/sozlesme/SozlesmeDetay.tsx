/**
 * Sözleşme detayı (Drawer) — künye + durum rozeti + durum geçiş butonları (``gecerliHedefler``
 * ∩ ``sozlesme:yaz``) + düzenle. Yaklaşan bitiş rozeti (kalan gün).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, Space, Tag } from 'antd';
import dayjs from 'dayjs';

import { useAuthStore } from '@/store/authStore';

import { gecerliHedefler } from './durum';
import { useSozlesme, useSozlesmeDurum } from './hooks';
import { SozlesmeDurumEtiketi } from './rozetler';
import { SozlesmeFormu } from './SozlesmeFormu';

export function SozlesmeDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: sozlesme } = useSozlesme(id ?? 0);
  const durumMut = useSozlesmeDurum();
  const yazabilir = useAuthStore((s) => s.izinVar('sozlesme:yaz'));
  const [duzenle, setDuzenle] = useState(false);

  const hedefler = sozlesme && yazabilir ? gecerliHedefler(sozlesme.durum) : [];
  const kalan = sozlesme ? dayjs(sozlesme.bitis_tarihi).diff(dayjs().startOf('day'), 'day') : 0;

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={620}
      title={sozlesme?.kod}
      extra={sozlesme && <SozlesmeDurumEtiketi durum={sozlesme.durum} />}
    >
      {sozlesme && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('sozlesme.baslik')}>{sozlesme.baslik}</Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.firma')}>#{sozlesme.firma_id}</Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.tur')}>
              {t(`sozlesme.tur_${sozlesme.tur}`)}
            </Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.baslangic')}>
              {sozlesme.baslangic_tarihi}
            </Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.bitis')}>
              {sozlesme.bitis_tarihi}{' '}
              {sozlesme.durum === 'aktif' && kalan >= 0 && kalan <= 30 && (
                <Tag color="warning" bordered={false}>
                  {t('sozlesme.kalan_gun', { gun: kalan })}
                </Tag>
              )}
            </Descriptions.Item>
            <Descriptions.Item label={t('sozlesme.tutar')}>
              <span className="sayisal">
                {sozlesme.tutar} {sozlesme.para_birimi}
              </span>
            </Descriptions.Item>
            {sozlesme.aciklama && (
              <Descriptions.Item label={t('sozlesme.aciklama')}>
                {sozlesme.aciklama}
              </Descriptions.Item>
            )}
          </Descriptions>

          <Space style={{ marginTop: 16 }} wrap>
            {yazabilir && <Button onClick={() => setDuzenle(true)}>{t('sozlesme.duzenle')}</Button>}
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

          <SozlesmeFormu acik={duzenle} kapat={() => setDuzenle(false)} mevcut={sozlesme} />
        </>
      )}
    </Drawer>
  );
}
