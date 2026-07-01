/**
 * Satınalma talebi detayı (Drawer) — künye + durum rozeti + kalem tablosu + tahmini toplam.
 * Aksiyon butonları ``gecerliHedefler(durum)`` ∩ kullanıcı izni ile filtrelenir (görev ayrımı):
 * ``onayla``/``reddet`` yalnız ``satinalma:onay`` varsa görünür. Reddet ``red_nedeni`` sorar.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, Input, Modal, Space, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { useAuthStore } from '@/store/authStore';

import { useTalep, useTalepDurumAksiyon } from './hooks';
import { TalepDurumEtiketi } from './rozetler';
import { gecerliHedefler } from './talepDurum';

type KalemSatiri = {
  id: number;
  malzeme_id: number;
  miktar: number;
  birim: string;
  tahmini_birim_fiyat?: number | null;
  aciklama: string;
};

type Aksiyon = { aksiyon: string; izin: string; etiket: string };

const HEDEF_AKSIYON: Record<string, Aksiyon> = {
  onay_bekliyor: { aksiyon: 'gonder', izin: 'satinalma:yaz', etiket: 'satinalma.gonder' },
  onaylandi: { aksiyon: 'onayla', izin: 'satinalma:onay', etiket: 'satinalma.onayla' },
  reddedildi: { aksiyon: 'reddet', izin: 'satinalma:onay', etiket: 'satinalma.reddet' },
  iptal: { aksiyon: 'iptal', izin: 'satinalma:yaz', etiket: 'satinalma.iptal' },
};

export function SatinalmaTalepDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: talep } = useTalep(id ?? 0);
  const aksiyonMut = useTalepDurumAksiyon();
  const izinVar = useAuthStore((s) => s.izinVar);
  const [redAcik, setRedAcik] = useState(false);
  const [redNeden, setRedNeden] = useState('');

  const hedefler = talep ? gecerliHedefler(talep.durum) : [];
  const butonlar = hedefler
    .map((h) => HEDEF_AKSIYON[h])
    .filter((a): a is Aksiyon => a != null && izinVar(a.izin));

  const calistir = async (aksiyon: string) => {
    if (!talep) return;
    if (aksiyon === 'reddet') {
      setRedAcik(true);
      return;
    }
    await aksiyonMut.mutateAsync({ id: talep.id, aksiyon });
  };

  const redGonder = async () => {
    if (!talep) return;
    await aksiyonMut.mutateAsync({ id: talep.id, aksiyon: 'reddet', red_nedeni: redNeden });
    setRedAcik(false);
    setRedNeden('');
  };

  const kolonlar: ColumnsType<KalemSatiri> = [
    { title: t('satinalma.malzeme'), dataIndex: 'malzeme_id', key: 'malzeme_id' },
    {
      title: t('satinalma.miktar'),
      dataIndex: 'miktar',
      key: 'miktar',
      align: 'right',
      render: (v: number, k) => (
        <span className="sayisal">
          {v} {k.birim}
        </span>
      ),
    },
    {
      title: t('satinalma.birim_fiyat'),
      dataIndex: 'tahmini_birim_fiyat',
      key: 'tahmini_birim_fiyat',
      align: 'right',
      render: (v: number | null) => <span className="sayisal">{v ?? '—'}</span>,
    },
  ];

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
            <Descriptions.Item label={t('satinalma.baslik')}>{talep.baslik}</Descriptions.Item>
            <Descriptions.Item label={t('satinalma.tahmini_toplam')}>
              {talep.tahmini_toplam != null ? `${talep.tahmini_toplam} ${talep.para_birimi}` : '—'}
            </Descriptions.Item>
            {talep.red_nedeni && (
              <Descriptions.Item label={t('satinalma.red_nedeni')}>
                {talep.red_nedeni}
              </Descriptions.Item>
            )}
          </Descriptions>
          <Table<KalemSatiri>
            style={{ marginTop: 16 }}
            rowKey="id"
            pagination={false}
            dataSource={talep.kalemler}
            columns={kolonlar}
          />
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
            title={t('satinalma.red_baslik')}
            okText={t('ortak.kaydet')}
            cancelText={t('ortak.iptal')}
            confirmLoading={aksiyonMut.isPending}
          >
            <Input.TextArea
              rows={3}
              value={redNeden}
              onChange={(e) => setRedNeden(e.target.value)}
              placeholder={t('satinalma.red_nedeni')}
            />
          </Modal>
        </>
      )}
    </Drawer>
  );
}
