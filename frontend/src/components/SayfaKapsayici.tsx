/**
 * Sayfa kapsayıcısı — standart genişlik (``enGenis``, vars. 1320) + üstte modül hat şeridi.
 * Hat rengi rotadan otomatik çözülür (``yolKimlik``); router dışı render'da (test) sakin
 * varsayılana düşer. Ekranlar bunu en dış sarmalayıcı olarak kullanır (SayfaBaslik'ten önce).
 */

import type { CSSProperties, ReactNode } from 'react';
import { useInRouterContext, useLocation } from 'react-router-dom';

import { yolKimlik } from '@/tema/modulKimlik';

function Govde({
  children,
  enGenis,
  renk,
}: {
  children: ReactNode;
  enGenis: number;
  renk: string;
}) {
  return (
    <div style={{ maxWidth: enGenis }}>
      <div className="hat-serit" style={{ '--hat': renk, marginBottom: 18 } as CSSProperties} />
      {children}
    </div>
  );
}

function RotaliGovde({ children, enGenis }: { children: ReactNode; enGenis: number }) {
  const konum = useLocation();
  return (
    <Govde enGenis={enGenis} renk={yolKimlik(konum.pathname).renk}>
      {children}
    </Govde>
  );
}

export function SayfaKapsayici({
  children,
  enGenis = 1320,
}: {
  children: ReactNode;
  enGenis?: number;
}) {
  const routerIcinde = useInRouterContext();
  if (!routerIcinde) {
    return (
      <Govde enGenis={enGenis} renk={yolKimlik('/').renk}>
        {children}
      </Govde>
    );
  }
  return <RotaliGovde enGenis={enGenis}>{children}</RotaliGovde>;
}
