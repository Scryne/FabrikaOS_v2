/**
 * Görünüm geçişi — Liste / Board / Analiz ``Segmented``'i. Durum-odaklı modüllerde board
 * gösterilir; grafik-zengin modüllerde analiz. Kontrollü (``deger``/``degisti``); ekran isterse
 * rota/query state'e bağlar (deep-link + geri davranışı). Etiketler i18n ``gorunum.*``.
 */

import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { AppstoreOutlined, AreaChartOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { Segmented } from 'antd';

export type Gorunum = 'liste' | 'pano' | 'analiz';

const IKON: Record<Gorunum, ReactNode> = {
  liste: <UnorderedListOutlined />,
  pano: <AppstoreOutlined />,
  analiz: <AreaChartOutlined />,
};

export function GorunumGecis({
  deger,
  degisti,
  secenekler = ['liste', 'pano', 'analiz'],
}: {
  deger: Gorunum;
  degisti: (g: Gorunum) => void;
  secenekler?: Gorunum[];
}) {
  const { t } = useTranslation();
  return (
    <Segmented<Gorunum>
      value={deger}
      onChange={degisti}
      options={secenekler.map((g) => ({ value: g, icon: IKON[g], label: t(`gorunum.${g}`) }))}
    />
  );
}
