/**
 * 5×5 risk matrisi ısı görseli — olasılık (x) × şiddet (y); hücrede sayaç, hücre rengi risk
 * seviyesinden gelir. Hücreye tıklama liste filtresini tetikler (``onHucre``). Skor/seviye
 * mantığı çağıran ekrandan (``renk`` fonksiyonu) gelir — bileşen jenerik ve isg'den bağımsız.
 */

import { Fragment } from 'react';
import type { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';

const EKSEN = [1, 2, 3, 4, 5];
const SIDDETLER = [5, 4, 3, 2, 1];

export function RiskMatrisi({
  sayac,
  renk,
  onHucre,
  secili,
}: {
  /** (olasılık, şiddet) → hücredeki kayıt sayısı. */
  sayac: (olasilik: number, siddet: number) => number;
  /** (olasılık, şiddet) → risk seviyesi rengi (hex). */
  renk: (olasilik: number, siddet: number) => string;
  /** Hücre tıklanınca (opsiyonel — verilmezse hücreler pasif). */
  onHucre?: (olasilik: number, siddet: number) => void;
  secili?: { olasilik: number; siddet: number } | null;
}) {
  const { t } = useTranslation();
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '20px repeat(5, 1fr)', gap: 6 }}>
        {SIDDETLER.map((siddet) => (
          <Fragment key={siddet}>
            <span
              className="sayisal"
              style={{
                display: 'grid',
                placeItems: 'center',
                color: 'var(--metin-soluk)',
                fontSize: 11,
              }}
            >
              {siddet}
            </span>
            {EKSEN.map((olasilik) => {
              const n = sayac(olasilik, siddet);
              const r = renk(olasilik, siddet);
              const isSecili = secili?.olasilik === olasilik && secili?.siddet === siddet;
              return (
                <button
                  key={olasilik}
                  type="button"
                  onClick={onHucre ? () => onHucre(olasilik, siddet) : undefined}
                  aria-label={`${t('isg.olasilik')} ${olasilik}, ${t('isg.siddet')} ${siddet}: ${n}`}
                  style={
                    {
                      aspectRatio: '1 / 1',
                      border: `1px solid ${isSecili ? r : 'var(--kenarlik)'}`,
                      borderRadius: 8,
                      background:
                        n > 0
                          ? `color-mix(in srgb, ${r} ${isSecili ? 32 : 18}%, transparent)`
                          : 'var(--yuzey-ust)',
                      color: n > 0 ? 'var(--metin)' : 'var(--metin-soluk)',
                      cursor: onHucre ? 'pointer' : 'default',
                      fontFamily: 'var(--font-mono)',
                      fontWeight: 600,
                      fontSize: 14,
                      transition: 'border-color var(--gecis), background var(--gecis)',
                    } as CSSProperties
                  }
                >
                  {n > 0 ? n : ''}
                </button>
              );
            })}
          </Fragment>
        ))}
        <span />
        {EKSEN.map((o) => (
          <span
            key={o}
            className="sayisal"
            style={{ textAlign: 'center', color: 'var(--metin-soluk)', fontSize: 11 }}
          >
            {o}
          </span>
        ))}
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginTop: 10,
          color: 'var(--metin-soluk)',
          fontSize: 12,
        }}
      >
        <span>↑ {t('isg.siddet')}</span>
        <span>{t('isg.olasilik')} →</span>
      </div>
    </div>
  );
}
