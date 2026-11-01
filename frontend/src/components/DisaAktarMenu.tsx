/**
 * Liste dışa aktarma menüsü (S27-B, ADR-0046): ekrandaki arama, süzgeç ve sıralamayla **tüm**
 * sayfaları çeker (100'lük sayfalar, en çok 5.000 satır) ve CSV ya da Excel indirir. Sınır
 * aşılırsa kullanıcıya söylenir ve süzgeç daraltması önerilir; sessizce kesilmez.
 * Excel yazıcısı yalnız ilk kullanımda yüklenir (ayrı parça).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DownloadOutlined } from '@ant-design/icons';
import { App, Button, Dropdown } from 'antd';

import { istekSayfali, PREFIX } from '@/api/client';
import { type SayfaParam, sorguDizesi } from '@/api/sayfalama';

import {
  bosSutunlariAt,
  csvUret,
  DISA_AKTAR_SINIRI,
  type DisaSutun,
  dosyaAdi,
  hucreDegeri,
} from './disaAktar';

export type DisaAktarAyar<T> = {
  /** Liste ucu (PREFIX hariç), ör. ``/malzemeler``. */
  yol: string;
  dosya: string;
  sutunlar: DisaSutun<T>[];
};

function indir(blob: Blob, ad: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = ad;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function DisaAktarMenu<T>({ ayar, param }: { ayar: DisaAktarAyar<T>; param: SayfaParam }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const [mesgul, setMesgul] = useState(false);

  const tumunuGetir = async (): Promise<{ kayitlar: T[]; toplam: number }> => {
    const kayitlar: T[] = [];
    let toplam = 0;
    for (let sayfa = 1; kayitlar.length < DISA_AKTAR_SINIRI; sayfa++) {
      const { veri, meta } = await istekSayfali<T>(
        `${PREFIX}${ayar.yol}?${sorguDizesi({ ...param, sayfa, adet: 100 })}`,
      );
      toplam = meta.toplam;
      kayitlar.push(...veri);
      if (veri.length < 100 || kayitlar.length >= toplam) break;
    }
    return { kayitlar: kayitlar.slice(0, DISA_AKTAR_SINIRI), toplam };
  };

  const aktar = async (bicim: 'csv' | 'xlsx') => {
    setMesgul(true);
    try {
      const { kayitlar, toplam } = await tumunuGetir();
      const sutunlar = bosSutunlariAt(kayitlar, ayar.sutunlar, {
        kod: t('disa.kod'),
        ad: t('disa.ad'),
        ad_soyad: t('disa.ad_soyad'),
        baslik: t('disa.baslik'),
      });
      if (bicim === 'csv') {
        indir(
          new Blob([csvUret(kayitlar, sutunlar)], { type: 'text/csv;charset=utf-8' }),
          dosyaAdi(ayar.dosya, 'csv'),
        );
      } else {
        const { default: yaz } = await import('write-excel-file/browser');
        const veri = [
          sutunlar.map((s) => ({ value: s.baslik, fontWeight: 'bold' as const })),
          ...kayitlar.map((k) => sutunlar.map((s) => ({ value: hucreDegeri(k, s) ?? undefined }))),
        ];
        const blob = await yaz(veri, {
          columns: sutunlar.map((s) => ({
            width: Math.min(Math.max(s.baslik.length + 4, 12), 48),
          })),
          stickyRowsCount: 1,
        }).toBlob();
        indir(blob, dosyaAdi(ayar.dosya, 'xlsx'));
      }
      if (toplam > DISA_AKTAR_SINIRI) {
        message.warning(t('disa.sinir', { sinir: DISA_AKTAR_SINIRI, toplam }));
      } else {
        message.success(t('disa.tamam', { adet: kayitlar.length }));
      }
    } catch {
      message.error(t('disa.hata'));
    } finally {
      setMesgul(false);
    }
  };

  return (
    <Dropdown
      trigger={['click']}
      disabled={mesgul}
      menu={{
        items: [
          { key: 'xlsx', label: t('disa.excel') },
          { key: 'csv', label: t('disa.csv') },
        ],
        onClick: ({ key }) => void aktar(key as 'csv' | 'xlsx'),
      }}
    >
      <Button icon={<DownloadOutlined />} loading={mesgul} aria-label={t('disa.dugme')}>
        <span className="disa-etiket">{t('disa.dugme')}</span>
      </Button>
    </Dropdown>
  );
}
