/**
 * Uygunsuzluk (CAPA) detayı (Drawer) — künye + kök-neden + durum geçişi + düzeltici/önleyici
 * aksiyonlar. Geçiş butonları ``gecerliHedefler(durum)`` ∩ ``kalite:yaz`` ile filtrelenir;
 * ``kok_neden`` ve ``kapandi`` hedefleri not (kök-neden / doğrulama notu) ister. Nihai
 * doğrulama backend'de (geçersiz geçiş 409).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, Form, Input, List, Modal, Select, Space, Tag } from 'antd';

import { useAuthStore } from '@/store/authStore';

import {
  type AksiyonOlustur,
  useAksiyonEkle,
  useAksiyonGuncelle,
  useCapaDurum,
  useUygunsuzluk,
} from './hooks';
import { gecerliHedefler } from './durum';
import { OnemEtiketi, UygunsuzlukDurumEtiketi } from './rozetler';

const AKSIYON_TURLERI = ['duzeltici', 'onleyici'];
// Not isteyen hedef geçişler: hangi alana yazılacağı.
const NOT_ALANI: Record<string, 'kok_neden' | 'dogrulama_notu'> = {
  kok_neden: 'kok_neden',
  kapandi: 'dogrulama_notu',
};

export function UygunsuzlukDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: u } = useUygunsuzluk(id ?? 0);
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const durumMut = useCapaDurum();
  const aksiyonEkle = useAksiyonEkle();
  const aksiyonGuncelle = useAksiyonGuncelle();

  const [gecisHedef, setGecisHedef] = useState<string | null>(null);
  const [gecisNot, setGecisNot] = useState('');
  const [aksiyonAcik, setAksiyonAcik] = useState(false);
  const [form] = Form.useForm<AksiyonOlustur>();

  const hedefler = u ? gecerliHedefler(u.durum) : [];

  const gecisBaslat = async (hedef: string) => {
    if (!u) return;
    if (hedef in NOT_ALANI) {
      setGecisHedef(hedef);
      setGecisNot('');
      return;
    }
    await durumMut.mutateAsync({ id: u.id, hedef });
  };

  const gecisGonder = async () => {
    if (!u || !gecisHedef) return;
    const ek =
      NOT_ALANI[gecisHedef] === 'kok_neden'
        ? { kok_neden: gecisNot }
        : { dogrulama_notu: gecisNot };
    await durumMut.mutateAsync({ id: u.id, hedef: gecisHedef, ...ek });
    setGecisHedef(null);
    setGecisNot('');
  };

  const aksiyonGonder = async () => {
    if (!u) return;
    const v = await form.validateFields();
    await aksiyonEkle.mutateAsync({ id: u.id, govde: v });
    form.resetFields();
    setAksiyonAcik(false);
  };

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      width={640}
      title={u?.kod}
      extra={u && <UygunsuzlukDurumEtiketi durum={u.durum} />}
    >
      {u && (
        <>
          <Descriptions column={1} size="small" bordered>
            <Descriptions.Item label={t('kalite.baslik')}>{u.baslik}</Descriptions.Item>
            <Descriptions.Item label={t('kalite.onem')}>
              <OnemEtiketi onem={u.onem} />
            </Descriptions.Item>
            {u.aciklama && (
              <Descriptions.Item label={t('kalite.aciklama')}>{u.aciklama}</Descriptions.Item>
            )}
            {u.kok_neden && (
              <Descriptions.Item label={t('kalite.kok_neden')}>{u.kok_neden}</Descriptions.Item>
            )}
            {u.dogrulama_notu && (
              <Descriptions.Item label={t('kalite.dogrulama_notu')}>
                {u.dogrulama_notu}
              </Descriptions.Item>
            )}
          </Descriptions>

          {yazabilir && hedefler.length > 0 && (
            <Space style={{ marginTop: 16 }} wrap>
              {hedefler.map((h) => (
                <Button
                  key={h}
                  type={h === 'kapandi' ? 'primary' : 'default'}
                  danger={h === 'iptal'}
                  loading={durumMut.isPending}
                  onClick={() => void gecisBaslat(h)}
                >
                  {t(`kalite.gecis_${h}`)}
                </Button>
              ))}
            </Space>
          )}

          <div
            style={{
              marginTop: 24,
              marginBottom: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 12,
            }}
          >
            <strong style={{ marginRight: 'auto' }}>{t('kalite.aksiyonlar')}</strong>
            {yazabilir && (
              <Button size="small" onClick={() => setAksiyonAcik(true)}>
                {t('kalite.aksiyon_ekle')}
              </Button>
            )}
          </div>
          <List
            size="small"
            locale={{ emptyText: t('kalite.aksiyon_yok') }}
            dataSource={u.aksiyonlar}
            renderItem={(a) => (
              <List.Item
                actions={
                  yazabilir && a.durum === 'planlandi'
                    ? [
                        <Button
                          key="tamamla"
                          size="small"
                          type="link"
                          loading={aksiyonGuncelle.isPending}
                          onClick={() =>
                            void aksiyonGuncelle.mutateAsync({
                              id: u.id,
                              aksiyonId: a.id,
                              durum: 'tamamlandi',
                            })
                          }
                        >
                          {t('kalite.tamamla')}
                        </Button>,
                      ]
                    : undefined
                }
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <Tag bordered={false}>{t(`kalite.aksiyon_${a.tur}`)}</Tag>
                      <Tag
                        color={a.durum === 'tamamlandi' ? 'success' : 'default'}
                        bordered={false}
                      >
                        {t(`kalite.aksiyon_durum_${a.durum}`)}
                      </Tag>
                    </Space>
                  }
                  description={a.aciklama}
                />
              </List.Item>
            )}
          />

          <Modal
            open={gecisHedef != null}
            onCancel={() => setGecisHedef(null)}
            onOk={() => void gecisGonder()}
            title={gecisHedef ? t(`kalite.gecis_${gecisHedef}`) : ''}
            okText={t('ortak.kaydet')}
            cancelText={t('ortak.iptal')}
            confirmLoading={durumMut.isPending}
          >
            <Input.TextArea
              rows={3}
              value={gecisNot}
              onChange={(e) => setGecisNot(e.target.value)}
              placeholder={
                gecisHedef && NOT_ALANI[gecisHedef] === 'kok_neden'
                  ? t('kalite.kok_neden_ipucu')
                  : t('kalite.dogrulama_notu')
              }
            />
          </Modal>

          <Modal
            open={aksiyonAcik}
            onCancel={() => setAksiyonAcik(false)}
            onOk={() => void aksiyonGonder()}
            title={t('kalite.aksiyon_ekle')}
            okText={t('ortak.kaydet')}
            cancelText={t('ortak.iptal')}
            confirmLoading={aksiyonEkle.isPending}
            destroyOnHidden
          >
            <Form form={form} layout="vertical" requiredMark="optional">
              <Form.Item
                name="tur"
                label={t('kalite.aksiyon_tur')}
                rules={[{ required: true }]}
                initialValue="duzeltici"
              >
                <Select
                  options={AKSIYON_TURLERI.map((x) => ({
                    value: x,
                    label: t(`kalite.aksiyon_${x}`),
                  }))}
                />
              </Form.Item>
              <Form.Item name="aciklama" label={t('kalite.aciklama')} rules={[{ required: true }]}>
                <Input.TextArea rows={3} maxLength={1000} />
              </Form.Item>
            </Form>
          </Modal>
        </>
      )}
    </Drawer>
  );
}
