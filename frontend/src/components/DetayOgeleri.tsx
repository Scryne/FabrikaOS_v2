/**
 * Detay çekmecesi paylaşılan primitifleri (Kontrol Odası dili):
 *
 * - ``DetayIstatSira``: 2-4 metrikli kompakt istatistik şeridi (büyük mono değer + soluk etiket,
 *   ince ayraçlı ızgara). Detay bölmesinin üstünde bağlam verir.
 * - ``DurumZamanCizelgesi``: bir durum makinesinin mutlu yolunu dikey ``Steps`` olarak çizer;
 *   ``mevcut`` ilerlemeyi belirler (tamamlanan aşamalar işaretli). Olumsuz terminal (iptal/
 *   feshedildi) ``olumsuz`` ile verilir ve mevcut durum o ise mutlu yol soluk (bekliyor)
 *   gösterilir, en alta kırmızı hata düğümü eklenir — kayıt normal akıştan çıkmıştır.
 *
 * Tümü salt sunum; veri çağıran çekmecenin kendi hook'undan gelir.
 */

import type { CSSProperties, ReactNode } from 'react';
import { Steps } from 'antd';
import type { StepProps } from 'antd';

export type DetayIstat = {
  anahtar: string;
  deger: ReactNode;
  etiket: string;
  /** Değer tonu (semantik renk; ör. var(--hata)). Verilmezse nötr metin. */
  ton?: string;
};

export function DetayIstatSira({ ogeler }: { ogeler: DetayIstat[] }) {
  return (
    <div className="detay-istat-sira">
      {ogeler.map((o) => (
        <div key={o.anahtar} className="detay-istat">
          <span
            className="deger sayisal"
            style={o.ton ? ({ '--istat-renk': o.ton } as CSSProperties) : undefined}
          >
            {o.deger}
          </span>
          <span className="etiket">{o.etiket}</span>
        </div>
      ))}
    </div>
  );
}

export type CizelgeAdim = { anahtar: string; baslik: string };

export function DurumZamanCizelgesi({
  adimlar,
  mevcut,
  olumsuz,
}: {
  /** Mutlu yol (sıralı). */
  adimlar: CizelgeAdim[];
  mevcut: string;
  /** Olumsuz terminal durum (iptal/feshedildi) — mevcut buysa akış kesilmiş gösterilir. */
  olumsuz?: CizelgeAdim;
}) {
  if (olumsuz != null && mevcut === olumsuz.anahtar) {
    const items: StepProps[] = [
      ...adimlar.map((a) => ({ title: a.baslik, status: 'wait' as const })),
      { title: olumsuz.baslik, status: 'error' as const },
    ];
    return <Steps direction="vertical" size="small" items={items} />;
  }

  const indeks = adimlar.findIndex((a) => a.anahtar === mevcut);
  return (
    <Steps
      direction="vertical"
      size="small"
      current={indeks < 0 ? 0 : indeks}
      items={adimlar.map((a) => ({ title: a.baslik }))}
    />
  );
}
