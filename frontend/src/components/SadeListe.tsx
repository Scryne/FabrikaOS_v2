/**
 * Sade liste: antd 6'da `List` kullanımdan kalktı (bir sonraki major'da kaldırılacak) ve yerine
 * önerilen `Listy` sanal kaydırmalı, sabit yükseklikli bir bileşen; çekmece ve kart içindeki
 * birkaç satırlık listeler için uygun değil. Projede kullanılan alt küme (dataSource,
 * renderItem, boş metin, başlık, yükleniyor; öğede eylemler; avatar/başlık/açıklama) anlamsal
 * <ul>/<li> ile burada. Görünüm eski küçük antd listesiyle aynı ritimde.
 */

import type { Key, ReactNode } from 'react';
import { Empty, Spin } from 'antd';

type SadeListeProps<T> = {
  dataSource?: readonly T[];
  renderItem: (oge: T, sira: number) => ReactNode;
  rowKey?: (oge: T, sira: number) => Key;
  locale?: { emptyText?: ReactNode };
  header?: ReactNode;
  loading?: boolean;
  /** Eski API ile uyum için kabul edilir; tek boyut (küçük) vardır. */
  size?: 'small';
};

export function SadeListe<T>({
  dataSource = [],
  renderItem,
  rowKey,
  locale,
  header,
  loading = false,
}: SadeListeProps<T>) {
  return (
    <div className="sade-liste">
      {header && <div className="sade-liste-baslik">{header}</div>}
      <Spin spinning={loading}>
        {dataSource.length === 0 ? (
          <div className="sade-liste-bos">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={locale?.emptyText} />
          </div>
        ) : (
          <ul>
            {dataSource.map((oge, i) => (
              <li key={rowKey ? rowKey(oge, i) : i}>{renderItem(oge, i)}</li>
            ))}
          </ul>
        )}
      </Spin>
    </div>
  );
}

function Oge({ children, actions }: { children?: ReactNode; actions?: ReactNode[] }) {
  return (
    <div className="sade-liste-oge">
      <div className="sade-liste-icerik">{children}</div>
      {actions && actions.length > 0 && <div className="sade-liste-eylem">{actions}</div>}
    </div>
  );
}

function Meta({
  avatar,
  title,
  description,
}: {
  avatar?: ReactNode;
  title?: ReactNode;
  description?: ReactNode;
}) {
  return (
    <div className="sade-liste-meta">
      {avatar && <div className="sade-liste-avatar">{avatar}</div>}
      <div className="sade-liste-metin">
        {title && <div className="sade-liste-ad">{title}</div>}
        {description && <div className="sade-liste-aciklama">{description}</div>}
      </div>
    </div>
  );
}

SadeListe.Oge = Oge;
SadeListe.Meta = Meta;
