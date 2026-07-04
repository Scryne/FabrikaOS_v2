/**
 * Belge detayı (Drawer) — künye + sürüm listesi (indir) + yeni sürüm yükleme.
 * Yükleme ``dys:yaz``; indirme ``dys:oku`` (herkes okuyabilir).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DownloadOutlined, UploadOutlined } from '@ant-design/icons';
import { App, Button, Descriptions, Drawer, Input, List, Space, Upload } from 'antd';
import type { UploadFile } from 'antd';

import { useAuthStore } from '@/store/authStore';

import { type BelgeSurumu, surumuIndir, useBelge, useSurumler, useSurumYukle } from './hooks';

export function BelgeDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const { data: belge } = useBelge(id ?? 0);
  const { data: surumler } = useSurumler(id ?? 0);
  const yukle = useSurumYukle();
  const yazabilir = useAuthStore((s) => s.izinVar('dys:yaz'));
  const [dosya, setDosya] = useState<File | null>(null);
  const [aciklama, setAciklama] = useState('');
  const [dosyaListe, setDosyaListe] = useState<UploadFile[]>([]);

  const yukleGonder = async () => {
    if (!belge || !dosya) return;
    await yukle.mutateAsync({ belgeId: belge.id, dosya, aciklama });
    setDosya(null);
    setAciklama('');
    setDosyaListe([]);
  };

  const indir = async (s: BelgeSurumu) => {
    if (!belge) return;
    try {
      await surumuIndir(belge.id, s.surum_no, s.dosya_adi);
    } catch {
      message.error(t('ortak.hata_baslik'));
    }
  };

  return (
    <Drawer open={id != null} onClose={kapat} width={620} title={belge?.ad}>
      {belge && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('dys.kod')}>
              <span className="sayisal">{belge.kod}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('dys.kategori')}>{belge.kategori || '—'}</Descriptions.Item>
            <Descriptions.Item label={t('dys.guncel_surum')}>
              {belge.guncel_surum}
            </Descriptions.Item>
            {belge.aciklama && (
              <Descriptions.Item label={t('dys.aciklama')}>{belge.aciklama}</Descriptions.Item>
            )}
          </Descriptions>

          {yazabilir && (
            <Space direction="vertical" style={{ marginTop: 16, width: '100%' }}>
              <Upload
                fileList={dosyaListe}
                beforeUpload={(f) => {
                  setDosya(f);
                  setDosyaListe([{ uid: '-1', name: f.name } as UploadFile]);
                  return false;
                }}
                onRemove={() => {
                  setDosya(null);
                  setDosyaListe([]);
                }}
                maxCount={1}
              >
                <Button icon={<UploadOutlined />}>{t('dys.dosya_sec')}</Button>
              </Upload>
              <Input
                placeholder={t('dys.surum_aciklama')}
                value={aciklama}
                onChange={(e) => setAciklama(e.target.value)}
              />
              <Button
                type="primary"
                disabled={!dosya}
                loading={yukle.isPending}
                onClick={() => void yukleGonder()}
              >
                {t('dys.surum_yukle')}
              </Button>
            </Space>
          )}

          <h4 style={{ marginTop: 24 }}>{t('dys.surumler')}</h4>
          <List
            size="small"
            bordered
            dataSource={surumler ?? []}
            locale={{ emptyText: t('dys.surum_bos') }}
            renderItem={(s) => (
              <List.Item
                actions={[
                  <Button
                    key="indir"
                    type="link"
                    icon={<DownloadOutlined />}
                    onClick={() => void indir(s)}
                  >
                    {t('dys.indir')}
                  </Button>,
                ]}
              >
                <List.Item.Meta
                  title={
                    <span className="sayisal">
                      v{s.surum_no} · {s.dosya_adi}
                    </span>
                  }
                  description={`${(s.boyut / 1024).toFixed(1)} KB${s.aciklama ? ` · ${s.aciklama}` : ''}`}
                />
              </List.Item>
            )}
          />
        </>
      )}
    </Drawer>
  );
}
