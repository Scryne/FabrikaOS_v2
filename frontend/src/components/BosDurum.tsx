/**
 * Boş durum — "kayıt yok"u öğreten sakin blok: ikon + başlık + açıklama + opsiyonel aksiyon.
 * Tablolarda (SunucuTablo emptyText) ve kart gövdelerinde kullanılır.
 */

import type { ReactNode } from 'react';
import { InboxOutlined } from '@ant-design/icons';

export function BosDurum({
  ikon,
  baslik,
  aciklama,
  aksiyon,
}: {
  ikon?: ReactNode;
  baslik: ReactNode;
  aciklama?: ReactNode;
  aksiyon?: ReactNode;
}) {
  return (
    <div className="bos-durum">
      <span className="bos-ikon" aria-hidden="true">
        {ikon ?? <InboxOutlined />}
      </span>
      <span className="bos-baslik">{baslik}</span>
      {aciklama && <span className="bos-aciklama">{aciklama}</span>}
      {aksiyon && <div style={{ marginTop: 10 }}>{aksiyon}</div>}
    </div>
  );
}
