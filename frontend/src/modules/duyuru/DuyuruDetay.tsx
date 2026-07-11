/**
 * Duyuru detayı (Drawer) — KPI şeridi (durum / önem / hedef) + okunur içerik bloğu +
 * yayınla/kaldır (``duyuru:yaz``).
 */

import { useTranslation } from 'react-i18next';
import { Button, Drawer, Space } from 'antd';

import { DetayIstatSira } from '@/components/DetayOgeleri';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { useDuyuru, useDuyuruYayin } from './hooks';
import { DuyuruOnemEtiketi } from './rozetler';

const ONEM_RENK: Record<string, string> = {
  bilgi: RENKLER.mavi,
  uyari: RENKLER.uyari,
  kritik: RENKLER.hata,
};

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
      destroyOnHidden
      title={duyuru?.baslik}
      extra={duyuru && <DuyuruOnemEtiketi onem={duyuru.onem} />}
    >
      {duyuru && (
        <>
          <DetayIstatSira
            ogeler={[
              {
                anahtar: 'durum',
                deger: duyuru.yayinda ? t('duyuru.yayinda') : t('duyuru.taslak'),
                etiket: t('duyuru.durum'),
                ton: duyuru.yayinda ? RENKLER.basari : RENKLER.metinSoluk,
              },
              {
                anahtar: 'onem',
                deger: t(`duyuru.onem_${duyuru.onem}`),
                etiket: t('duyuru.onem'),
                ton: ONEM_RENK[duyuru.onem],
              },
              {
                anahtar: 'hedef',
                deger: duyuru.hedef_departman || t('duyuru.tum_departmanlar'),
                etiket: t('duyuru.hedef_departman'),
              },
            ]}
          />

          <div className="detay-bolum-baslik">{t('duyuru.kod')}</div>
          <span className="sayisal" style={{ color: 'var(--metin-soluk)' }}>
            {duyuru.kod}
          </span>

          <div className="detay-bolum-baslik">{t('duyuru.icerik')}</div>
          <div
            style={{
              background: 'var(--yuzey-ust)',
              border: '1px solid var(--kenarlik)',
              borderRadius: 12,
              padding: '14px 16px',
              color: 'var(--metin)',
              lineHeight: 1.6,
              whiteSpace: 'pre-wrap',
            }}
          >
            {duyuru.icerik || '—'}
          </div>

          {yazabilir && (
            <Space style={{ marginTop: 20 }}>
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
