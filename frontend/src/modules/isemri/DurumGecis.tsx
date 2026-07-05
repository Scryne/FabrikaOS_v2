/**
 * İş emri durum geçiş aksiyonları — yalnız geçerli hedefleri (durum makinesi) sunar.
 *
 * Atama kuralı: ``atandi``ya geçiş atanan kullanıcı gerektirir. ``kullanici:oku`` izni varsa
 * kullanıcı seçtiren modal açılır; yoksa "bana ata" (giriş yapan kullanıcı) ile atanır. Diğer
 * geçişler doğrudan uygulanır. ``isemri:yaz`` yoksa hiçbir aksiyon gösterilmez.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Modal, Popconfirm, Select, Space } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { gecerliHedefler } from './durum';
import { type IsEmri, useDurumGuncelle, useKullaniciSecenekleri } from './hooks';

export function DurumGecis({
  isEmri,
  boyut = 'small',
}: {
  isEmri: Pick<IsEmri, 'id' | 'durum' | 'atanan_kullanici_id'>;
  boyut?: 'small' | 'middle';
}) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isemri:yaz'));
  const kullaniciOku = useAuthStore((s) => s.izinVar('kullanici:oku'));
  const benId = useAuthStore((s) => s.kullanici?.id);
  const guncelle = useDurumGuncelle();
  const { data: kullanicilar } = useKullaniciSecenekleri(kullaniciOku && yazabilir);
  const [ataAcik, setAtaAcik] = useState(false);
  const [secilen, setSecilen] = useState<number | undefined>();

  if (!yazabilir) return null;
  const hedefler = gecerliHedefler(isEmri.durum);
  if (hedefler.length === 0) return null;

  const gecisYap = (hedef: string) => {
    if (hedef === 'atandi' && isEmri.atanan_kullanici_id == null) {
      if (kullaniciOku) {
        setAtaAcik(true);
        return;
      }
      guncelle.mutate({ id: isEmri.id, govde: { durum: 'atandi', atanan_kullanici_id: benId } });
      return;
    }
    guncelle.mutate({ id: isEmri.id, govde: { durum: hedef } });
  };

  return (
    <>
      <Space size={8} wrap>
        {hedefler.map((hedef) =>
          hedef === 'iptal' ? (
            // İptal geri alınamaz: sakin metin butonu + onay sorusu (kart yüzeyinde kırmızı bağırmaz).
            <Popconfirm
              key={hedef}
              title={t('isemri.iptal_onay')}
              okButtonProps={{ danger: true }}
              onConfirm={() => gecisYap(hedef)}
              onPopupClick={(e) => e.stopPropagation()}
            >
              <Button
                size={boyut}
                type="text"
                loading={guncelle.isPending}
                style={{ color: 'var(--metin-soluk)' }}
                onClick={(e) => e.stopPropagation()}
              >
                {t(`isemri.gecis_${hedef}`)}
              </Button>
            </Popconfirm>
          ) : (
            <Button
              key={hedef}
              size={boyut}
              type={hedef === 'kapandi' ? 'primary' : 'default'}
              loading={guncelle.isPending}
              onClick={(e) => {
                e.stopPropagation();
                gecisYap(hedef);
              }}
            >
              {t(`isemri.gecis_${hedef}`)}
            </Button>
          ),
        )}
      </Space>

      <Modal
        open={ataAcik}
        title={t('isemri.ata_baslik')}
        okText={t('isemri.ata')}
        cancelText={t('ortak.iptal')}
        okButtonProps={{ disabled: secilen == null }}
        confirmLoading={guncelle.isPending}
        onCancel={() => setAtaAcik(false)}
        onOk={() => {
          guncelle.mutate(
            { id: isEmri.id, govde: { durum: 'atandi', atanan_kullanici_id: secilen } },
            { onSuccess: () => setAtaAcik(false) },
          );
        }}
        destroyOnHidden
      >
        <Select
          style={{ width: '100%' }}
          showSearch
          optionFilterProp="label"
          placeholder={t('isemri.atayan_sec')}
          value={secilen}
          onChange={setSecilen}
          options={(kullanicilar ?? []).map((k) => ({
            value: k.id,
            label: `${k.ad_soyad || k.eposta}`,
          }))}
        />
      </Modal>
    </>
  );
}
