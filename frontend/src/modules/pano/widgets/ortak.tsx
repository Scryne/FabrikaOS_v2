/**
 * Persona panosu domain panelleri (widget) için paylaşılan primitifler.
 *
 * Her domain paneli ``WidgetKabuk`` ile sarılır: modül hat rengi + ikonu + başlık + sağda
 * "panele git" bağlantısı; yükleniyorken sakin skeleton, veri yoksa öğretici boş metin.
 * ``IstatSira`` widget içi kompakt KPI sırasıdır (büyük mono değer + soluk etiket). Tümü saf
 * sunum — veri, çağıran widget'ın ``use<Modul>Ozet()`` hook'undan gelir (Kontrol Odası deseni).
 */

import type { CSSProperties, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ArrowRightOutlined } from '@ant-design/icons';
import { Skeleton } from 'antd';

import { PanelKart } from '@/components/PanelKart';
import { BOLUM_RENGI, MENU_IKONLARI } from '@/tema/modulKimlik';

export function WidgetKabuk({
  bolum,
  ikonAnahtar,
  baslikAnahtari,
  yol,
  yukleniyor,
  bos,
  bosMetin,
  genis,
  children,
}: {
  /** Hat rengi kaynağı (ör. 'menu.bolum_uretim'). */
  bolum: string;
  /** İkon anahtarı (tema/modulKimlik MENU_IKONLARI). */
  ikonAnahtar: string;
  /** Başlık i18n anahtarı (ör. 'pano.widget_uretim'). */
  baslikAnahtari: string;
  /** "Panele git" bağlantısı hedefi. */
  yol: string;
  yukleniyor?: boolean;
  bos?: boolean;
  bosMetin?: string;
  /** İki iz kaplasın mı (grafik taşıyan geniş paneller). */
  genis?: boolean;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  return (
    <div className={genis ? 'genis' : undefined}>
      <PanelKart
        renk={BOLUM_RENGI[bolum]}
        ikon={MENU_IKONLARI[ikonAnahtar]}
        baslik={t(baslikAnahtari)}
        sag={
          <Link className="widget-link" to={yol}>
            {t('pano.panele_git')}
            <ArrowRightOutlined style={{ fontSize: 11 }} />
          </Link>
        }
      >
        {yukleniyor ? (
          <Skeleton active paragraph={{ rows: 2 }} title={{ width: '42%' }} />
        ) : bos ? (
          <div className="widget-bos">{bosMetin}</div>
        ) : (
          children
        )}
      </PanelKart>
    </div>
  );
}

export type Istat = {
  anahtar: string;
  deger: ReactNode;
  etiket: string;
  /** Değer tonu (semantik renk; ör. var(--hata) kritik sayaç). Verilmezse nötr metin. */
  ton?: string;
};

/** Widget içi kompakt KPI sırası — büyük mono değer + soluk etiket. */
export function IstatSira({ ogeler }: { ogeler: Istat[] }) {
  return (
    <div className="pano-istat-sira">
      {ogeler.map((o) => (
        <div key={o.anahtar} className="pano-istat">
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

/** Widget içi ikincil bölüm etiketi (ör. "Kritik malzemeler", "Makine OEE"). */
export function AltBaslik({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        fontSize: 12,
        fontWeight: 600,
        color: 'var(--metin-soluk)',
        marginBottom: 6,
        letterSpacing: '0.01em',
      }}
    >
      {children}
    </div>
  );
}

export type Segment = { anahtar: string; ad: string; deger: number; renk: string };

/** Yatay orantı barı + lejant — kategorik yaşam-döngüsü dağılımı (ör. uygunsuzluk durumu). */
export function SegmentBar({ segmentler }: { segmentler: Segment[] }) {
  const toplam = segmentler.reduce((a, s) => a + s.deger, 0) || 1;
  return (
    <div>
      <div
        style={{
          display: 'flex',
          height: 8,
          borderRadius: 4,
          overflow: 'hidden',
          background: 'rgba(255,255,255,0.06)',
        }}
        aria-hidden="true"
      >
        {segmentler
          .filter((s) => s.deger > 0)
          .map((s) => (
            <div
              key={s.anahtar}
              style={{ width: `${(s.deger / toplam) * 100}%`, background: s.renk }}
            />
          ))}
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '7px 16px', marginTop: 10 }}>
        {segmentler.map((s) => (
          <span
            key={s.anahtar}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}
          >
            <span
              style={{ width: 8, height: 8, borderRadius: 2, background: s.renk }}
              aria-hidden="true"
            />
            <span style={{ color: 'var(--metin-soluk)' }}>{s.ad}</span>
            <span className="sayisal" style={{ color: 'var(--metin)', fontWeight: 600 }}>
              {s.deger}
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
