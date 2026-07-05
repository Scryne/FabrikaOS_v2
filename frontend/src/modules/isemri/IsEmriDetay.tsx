/**
 * İş emri detay çekmecesi — künye (Descriptions) + durum geçiş aksiyonları + yorum/aktivite akışı.
 * ``isemri:yaz`` ile yorum eklenir ve durum ilerletilir. Makine/atanan adları sözlüklerden çözülür.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Button,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Input,
  Skeleton,
  Space,
  Typography,
} from 'antd';
import dayjs from 'dayjs';

import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';

import { DurumGecis } from './DurumGecis';
import { useIsEmri, useKullaniciSecenekleri, useYorumEkle } from './hooks';
import { DurumEtiketi, OncelikRozet } from './rozetler';

function tarih(v?: string | null): string {
  return v ? dayjs(v).format('DD.MM.YYYY HH:mm') : '—';
}

export function IsEmriDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isemri:yaz'));
  const kullaniciOku = useAuthStore((s) => s.izinVar('kullanici:oku'));
  const acik = id != null;
  const { data: isEmri, isPending } = useIsEmri(id ?? 0);
  const { data: makineler } = useMakineSecenekleri();
  const { data: kullanicilar } = useKullaniciSecenekleri(kullaniciOku);
  const yorumEkle = useYorumEkle();
  const [yorum, setYorum] = useState('');

  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);
  const kullaniciHarita = useMemo(
    () => new Map((kullanicilar ?? []).map((k) => [k.id, k])),
    [kullanicilar],
  );

  const atananAd = (kid?: number | null) => {
    if (kid == null) return t('isemri.atanmamis');
    return kullaniciHarita.get(kid)?.ad_soyad || `#${kid}`;
  };

  const yorumGonder = () => {
    if (!id || !yorum.trim()) return;
    yorumEkle.mutate({ id, metin: yorum.trim() }, { onSuccess: () => setYorum('') });
  };

  return (
    <Drawer
      open={acik}
      onClose={kapat}
      width={520}
      destroyOnHidden
      title={
        isEmri ? (
          <Space size={10} wrap>
            <span className="sayisal">{isEmri.kod}</span>
            <DurumEtiketi durum={isEmri.durum} />
          </Space>
        ) : (
          t('menu.is_emirleri')
        )
      }
    >
      {isPending || !isEmri ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : (
        <>
          <Typography.Title level={4} style={{ marginTop: 0 }}>
            {isEmri.baslik}
          </Typography.Title>

          {yazabilir && (
            <div style={{ marginBottom: 16 }}>
              <DurumGecis isEmri={isEmri} boyut="middle" />
            </div>
          )}

          <Descriptions column={1} size="small" styles={{ label: { width: 130 } }}>
            <Descriptions.Item label={t('isemri.makine')}>
              {makineHarita.get(isEmri.makine_id)?.kod ?? `#${isEmri.makine_id}`}
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.oncelik')}>
              <OncelikRozet oncelik={isEmri.oncelik} />
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.atanan')}>
              {atananAd(isEmri.atanan_kullanici_id)}
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.olusturma')}>
              {tarih(isEmri.olusturma_tarihi)}
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.kapanis')}>
              {tarih(isEmri.kapanis_tarihi)}
            </Descriptions.Item>
          </Descriptions>

          {isEmri.aciklama && (
            <Typography.Paragraph style={{ color: 'var(--metin-soluk)', marginTop: 4 }}>
              {isEmri.aciklama}
            </Typography.Paragraph>
          )}

          <Divider orientation="left" plain>
            {t('isemri.yorumlar')}
          </Divider>

          {isEmri.yorumlar && isEmri.yorumlar.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {isEmri.yorumlar.map((y) => (
                <div
                  key={y.id}
                  style={{
                    background: 'var(--yuzey-ust)',
                    border: '1px solid var(--kenarlik)',
                    borderRadius: 10,
                    padding: '10px 12px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 8,
                      marginBottom: 4,
                    }}
                  >
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{y.yazan_eposta ?? '—'}</span>
                    <span className="sayisal" style={{ fontSize: 11, color: 'var(--metin-soluk)' }}>
                      {tarih(y.olusturma_tarihi)}
                    </span>
                  </div>
                  <div style={{ color: 'var(--metin)' }}>{y.metin}</div>
                </div>
              ))}
            </div>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('isemri.yorum_yok')} />
          )}

          {yazabilir && (
            <div style={{ marginTop: 16 }}>
              <Input.TextArea
                rows={2}
                value={yorum}
                onChange={(e) => setYorum(e.target.value)}
                maxLength={2000}
                placeholder={t('isemri.yorum_yaz')}
              />
              <Button
                type="primary"
                style={{ marginTop: 10 }}
                loading={yorumEkle.isPending}
                disabled={!yorum.trim()}
                onClick={yorumGonder}
              >
                {t('isemri.yorum_ekle')}
              </Button>
            </div>
          )}
        </>
      )}
    </Drawer>
  );
}
