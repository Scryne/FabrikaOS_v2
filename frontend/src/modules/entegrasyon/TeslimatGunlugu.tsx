/**
 * Webhook teslimat günlüğü sekmesi — durum pimli tablo + payload çekmecesi +
 * "yeniden dene" (terminal başarısız dahil bir deneme daha kuyruğa alır).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { RedoOutlined } from '@ant-design/icons';
import { Button, Descriptions, Drawer, Select, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { DurumPim } from '@/components/DurumPim';
import { SunucuTablo } from '@/components/SunucuTablo';
import { useSayfaParam } from '@/modules/ortak/useSayfaParam';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { type Teslimat, useTeslimatlar, useYenidenDene } from './hooks';

const DURUM_RENGI: Record<string, string> = {
  basarili: RENKLER.basari,
  beklemede: RENKLER.uyari,
  yeniden_denenecek: RENKLER.uyari,
  basarisiz: RENKLER.hata,
};

function tarih(v: string | null | undefined): string {
  return v ? new Date(v).toLocaleString('tr-TR') : '—';
}

export function TeslimatGunlugu() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('entegrasyon:yaz'));
  const [param, paramDegistir] = useSayfaParam();
  const { data, isPending, isError } = useTeslimatlar(param);
  const yenidenDene = useYenidenDene();
  const [secili, setSecili] = useState<Teslimat | null>(null);

  const durumEtiketi = (durum: string) => t(`entegrasyon.durum_${durum}`, durum);

  const kolonlar: ColumnsType<Teslimat> = [
    {
      title: t('entegrasyon.olay'),
      dataIndex: 'olay_turu',
      key: 'olay_turu',
      render: (v: string) => <Tag bordered={false}>{v}</Tag>,
    },
    {
      title: t('entegrasyon.durum'),
      dataIndex: 'durum',
      key: 'durum',
      render: (durum: string) => (
        <DurumPim renk={DURUM_RENGI[durum] ?? RENKLER.metinSoluk} etiket={durumEtiketi(durum)} />
      ),
    },
    {
      title: t('entegrasyon.deneme'),
      dataIndex: 'deneme_sayisi',
      key: 'deneme_sayisi',
      align: 'right',
      render: (v: number) => <span className="sayisal">{v}</span>,
    },
    {
      title: t('entegrasyon.yanit'),
      dataIndex: 'yanit_kodu',
      key: 'yanit_kodu',
      align: 'right',
      render: (v: number | null) => <span className="sayisal">{v ?? '—'}</span>,
    },
    {
      title: t('entegrasyon.son_deneme'),
      dataIndex: 'son_deneme_tarihi',
      key: 'son_deneme_tarihi',
      render: (v: string | null) => <span className="sayisal">{tarih(v)}</span>,
    },
    {
      title: '',
      key: 'aksiyon',
      align: 'right',
      render: (_v: unknown, kayit: Teslimat) => (
        <span style={{ display: 'inline-flex', gap: 8 }}>
          <Button size="small" onClick={() => setSecili(kayit)}>
            {t('entegrasyon.payload')}
          </Button>
          {yazabilir && (
            <Button
              size="small"
              icon={<RedoOutlined />}
              disabled={kayit.durum === 'basarili'}
              loading={yenidenDene.isPending && yenidenDene.variables === kayit.id}
              onClick={() => yenidenDene.mutate(kayit.id)}
            >
              {t('entegrasyon.yeniden_dene')}
            </Button>
          )}
        </span>
      ),
    },
  ];

  return (
    <>
      <SunucuTablo<Teslimat>
        kolonlar={kolonlar}
        veri={data?.veri ?? []}
        meta={data?.meta}
        yukleniyor={isPending}
        param={param}
        paramDegistir={paramDegistir}
        rowKey="id"
        bosMetin={isError ? t('ortak.hata_baslik') : t('entegrasyon.teslimat_bos')}
        araclar={
          <Select
            allowClear
            placeholder={t('entegrasyon.durum')}
            style={{ minWidth: 180 }}
            value={(param.filtreler?.durum as string) ?? undefined}
            onChange={(v: string | undefined) => paramDegistir({ filtreler: { durum: v } })}
            options={['basarili', 'beklemede', 'yeniden_denenecek', 'basarisiz'].map((d) => ({
              value: d,
              label: durumEtiketi(d),
            }))}
          />
        }
      />
      <Drawer
        open={secili !== null}
        onClose={() => setSecili(null)}
        title={secili ? `${secili.olay_turu} · #${secili.id}` : ''}
        width={480}
      >
        {secili && (
          <>
            <Descriptions
              column={1}
              size="small"
              items={[
                {
                  key: 'durum',
                  label: t('entegrasyon.durum'),
                  children: durumEtiketi(secili.durum),
                },
                {
                  key: 'deneme',
                  label: t('entegrasyon.deneme'),
                  children: secili.deneme_sayisi,
                },
                {
                  key: 'yanit',
                  label: t('entegrasyon.yanit'),
                  children: secili.yanit_kodu ?? '—',
                },
                {
                  key: 'yanit_ozeti',
                  label: t('entegrasyon.yanit_ozeti'),
                  children: secili.yanit_ozeti || '—',
                },
                {
                  key: 'sonraki',
                  label: t('entegrasyon.sonraki_deneme'),
                  children: tarih(secili.sonraki_deneme_tarihi),
                },
                {
                  key: 'idempotency',
                  label: t('entegrasyon.teslimat_anahtari'),
                  children: <span className="sayisal">{secili.dis_anahtar}</span>,
                },
              ]}
            />
            <pre
              className="sayisal"
              style={{
                marginTop: 16,
                padding: 12,
                borderRadius: 8,
                background: 'rgba(148,163,184,0.08)',
                fontSize: 12,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}
            >
              {JSON.stringify(secili.govde, null, 2)}
            </pre>
          </>
        )}
      </Drawer>
    </>
  );
}
