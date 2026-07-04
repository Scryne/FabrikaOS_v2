/**
 * Duyuru detayı (Drawer) — künye + içerik + yayınla/kaldır (``duyuru:yaz``).
 */

import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, Space, Tag } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { useDuyuru, useDuyuruYayin } from './hooks';
import { DuyuruOnemEtiketi } from './rozetler';

export function DuyuruDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: duyuru } = useDuyuru(id ?? 0);
  const yayinMut = useDuyuruYayin();
  const yazabilir = useAuthStore((s) => s.izinVar('duyuru:yaz'));

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={560}
      title={duyuru?.baslik}
      extra={duyuru && <DuyuruOnemEtiketi onem={duyuru.onem} />}
    >
      {duyuru && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('duyuru.kod')}>
              <span className="sayisal">{duyuru.kod}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('duyuru.durum')}>
              <Tag color={duyuru.yayinda ? 'success' : 'default'} bordered={false}>
                {duyuru.yayinda ? t('duyuru.yayinda') : t('duyuru.taslak')}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label={t('duyuru.hedef_departman')}>
              {duyuru.hedef_departman || t('duyuru.tum_departmanlar')}
            </Descriptions.Item>
            <Descriptions.Item label={t('duyuru.icerik')}>{duyuru.icerik || '—'}</Descriptions.Item>
          </Descriptions>

          {yazabilir && (
            <Space style={{ marginTop: 16 }}>
              {!duyuru.yayinda ? (
                <Button
                  type="primary"
                  loading={yayinMut.isPending}
                  onClick={() => void yayinMut.mutateAsync({ id: duyuru.id, aksiyon: 'yayinla' })}
                >
                  {t('duyuru.yayinla')}
                </Button>
              ) : (
                <Button
                  loading={yayinMut.isPending}
                  onClick={() => void yayinMut.mutateAsync({ id: duyuru.id, aksiyon: 'kaldir' })}
                >
                  {t('duyuru.kaldir')}
                </Button>
              )}
            </Space>
          )}
        </>
      )}
    </Drawer>
  );
}
