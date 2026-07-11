/**
 * Hero canlı enstrümanı (landing imzası) — nazikçe güncellenen OEE göstergesi + akan üretim hattı
 * şeması + KPI kutucukları + durum LED'leri. Ürünün gerçek görsel dilini (kontrol odası) yansıtır;
 * sahte ekran görüntüsü değil, soyut bir enstrüman panelidir (dekoratif, aria-hidden). Hareket
 * ``prefers-reduced-motion``'a saygılıdır (statik değere düşer).
 */

import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DashboardOutlined } from '@ant-design/icons';

import { EGrafik } from '@/components/grafik/EGrafik';
import { gostergeSecenek } from '@/components/grafik/grafikSecenek';

function azalanHareket(): boolean {
  return (
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches
  );
}

export function HeroEnstruman() {
  const { t } = useTranslation();
  const [oee, setOee] = useState(84);

  useEffect(() => {
    if (azalanHareket()) return;
    const id = setInterval(() => {
      setOee((v) => {
        const d = (Math.random() - 0.5) * 3.2;
        return Math.max(78, Math.min(89, Math.round((v + d) * 10) / 10));
      });
    }, 2600);
    return () => clearInterval(id);
  }, []);

  const gauge = useMemo(() => gostergeSecenek(oee), [oee]);

  return (
    <div className="tn-enstruman tn-belir tn-belir-2" aria-hidden="true">
      <div className="tn-ens-bas">
        <span className="tn-ens-baslik">
          <DashboardOutlined style={{ color: 'var(--cyan)' }} />
          {t('tanitim.ens_baslik')}
        </span>
        <span className="tn-ens-canli">
          <i className="canli-nokta" />
          {t('tanitim.ens_canli')}
        </span>
      </div>

      <div className="tn-ens-govde">
        <div>
          <EGrafik secenek={gauge} yukseklik={168} />
        </div>
        <div className="tn-ens-kpi">
          <div className="tn-ens-kpi-kart">
            <div className="tn-ens-kpi-deger" style={{ color: 'var(--basari)' }}>
              9<span style={{ color: 'var(--metin-soluk)', fontSize: 15 }}> / 12</span>
            </div>
            <div className="tn-ens-kpi-etiket">{t('tanitim.ens_hat')}</div>
          </div>
          <div className="tn-ens-kpi-kart">
            <div className="tn-ens-kpi-deger">1.240</div>
            <div className="tn-ens-kpi-etiket">{t('tanitim.ens_adet')}</div>
          </div>
          <div className="tn-ens-kpi-kart">
            <div className="tn-ens-kpi-deger" style={{ color: 'var(--uyari)' }}>
              1
            </div>
            <div className="tn-ens-kpi-etiket">{t('tanitim.ens_uyari')}</div>
          </div>
        </div>
      </div>

      <div className="tn-ens-hat">
        <svg viewBox="0 0 380 90" fill="none" role="presentation">
          <path
            d="M8 66 H86 C98 66 104 60 104 48 V32 C104 20 110 14 122 14 H196 C208 14 214 20 214 32 V48 C214 60 220 66 232 66 H372"
            stroke="var(--kenarlik-parlak)"
            strokeWidth="1.5"
          />
          <path
            className="tn-ens-akis"
            d="M8 66 H86 C98 66 104 60 104 48 V32 C104 20 110 14 122 14 H196 C208 14 214 20 214 32 V48 C214 60 220 66 232 66 H372"
            stroke="var(--cyan)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <g>
            <rect
              x="30"
              y="50"
              width="32"
              height="32"
              rx="8"
              fill="var(--yuzey-ust)"
              stroke="var(--kenarlik-parlak)"
            />
            <circle cx="46" cy="66" r="3.5" fill="var(--basari)" />
          </g>
          <g>
            <rect
              x="140"
              y="0"
              width="32"
              height="32"
              rx="8"
              fill="var(--yuzey-ust)"
              stroke="var(--kenarlik-parlak)"
            />
            <circle cx="156" cy="16" r="3.5" fill="var(--basari)" />
          </g>
          <g>
            <rect
              x="248"
              y="50"
              width="32"
              height="32"
              rx="8"
              fill="var(--yuzey-ust)"
              stroke="var(--kenarlik-parlak)"
            />
            <circle cx="264" cy="66" r="3.5" fill="var(--uyari)" />
          </g>
          <g>
            <rect
              x="330"
              y="50"
              width="32"
              height="32"
              rx="8"
              fill="var(--yuzey-ust)"
              stroke="var(--kenarlik-parlak)"
            />
            <circle cx="346" cy="66" r="3.5" fill="var(--cyan)" />
          </g>
        </svg>
      </div>

      <div className="tn-ens-leds">
        <span className="tn-led">
          <i style={{ background: 'var(--basari)' }} />
          {t('uretim.durum_calisiyor')}
        </span>
        <span className="tn-led">
          <i style={{ background: 'var(--uyari)' }} />
          {t('uretim.durum_bakimda')}
        </span>
        <span className="tn-led">
          <i style={{ background: 'var(--metin-soluk)' }} />
          {t('uretim.durum_durdu')}
        </span>
      </div>
    </div>
  );
}
