/**
 * Kurumsal tanıtım (landing) — public `/tanitim` rotası. Ürünün gerçek hikâyesini (sahadan
 * kontrol odasına, on yedi modül, çok-kiracılı platform) koyu kontrol-odası estetiğiyle anlatır.
 * Bölümler: nav → hero (canlı enstrüman) → yetenek şeridi → modül vitrini → veri akışı → persona
 * → platform → kapanış CTA → footer. Marka kimliği (hat renkleri, Marka/logo, akan hat) korunur.
 */

import type { CSSProperties, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  ApiOutlined,
  AppstoreOutlined,
  AreaChartOutlined,
  ClusterOutlined,
  FolderOpenOutlined,
  FundOutlined,
  GoldOutlined,
  MedicineBoxOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
  SlidersOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  UserOutlined,
  WifiOutlined,
} from '@ant-design/icons';

import { Marka } from '@/components/Marka';
import { useAuthStore } from '@/store/authStore';

import { HeroEnstruman } from './HeroEnstruman';
import './tanitim.css';

type Modul = { anahtar: string; ikon: ReactNode; hat: string; genis?: boolean };

const MODULLER: Modul[] = [
  { anahtar: 'uretim', ikon: <RobotOutlined />, hat: 'var(--hat-uretim)', genis: true },
  { anahtar: 'stok', ikon: <GoldOutlined />, hat: 'var(--hat-stok)' },
  { anahtar: 'kalite', ikon: <SafetyCertificateOutlined />, hat: 'var(--hat-kalite)' },
  { anahtar: 'isgik', ikon: <MedicineBoxOutlined />, hat: 'var(--hat-isg-ik)' },
  { anahtar: 'ticari', ikon: <FundOutlined />, hat: 'var(--hat-ticari)' },
  { anahtar: 'dokuman', ikon: <FolderOpenOutlined />, hat: 'var(--hat-dokuman)' },
  { anahtar: 'zeka', ikon: <AreaChartOutlined />, hat: 'var(--hat-zeka)' },
  { anahtar: 'yonetim', ikon: <SlidersOutlined />, hat: 'var(--hat-yonetim)' },
];

const AKIS = ['saha', 'iletim', 'isleme', 'kontrol'] as const;
const PERSONALAR = [
  { anahtar: 'operator', ikon: <UserOutlined /> },
  { anahtar: 'yonetici', ikon: <AppstoreOutlined /> },
  { anahtar: 'sorumlu', ikon: <TeamOutlined /> },
];
const PLATFORM = [
  { anahtar: 'izolasyon', ikon: <ClusterOutlined /> },
  { anahtar: 'rbac', ikon: <SafetyOutlined /> },
  { anahtar: 'entitlement', ikon: <AppstoreOutlined /> },
  { anahtar: 'dis', ikon: <WifiOutlined /> },
  { anahtar: 'webhook', ikon: <ApiOutlined /> },
  { anahtar: 'gerceklzaman', ikon: <ThunderboltOutlined /> },
];
const CIPLER = [
  { anahtar: 'modul', renk: 'var(--mavi)' },
  { anahtar: 'kiracili', renk: 'var(--hat-stok)' },
  { anahtar: 'gerceklzaman', renk: 'var(--cyan)' },
  { anahtar: 'edge', renk: 'var(--hat-uretim)' },
  { anahtar: 'erisim', renk: 'var(--basari)' },
  { anahtar: 'dil', renk: 'var(--hat-dokuman)' },
];

export function TanitimSayfasi() {
  const { t } = useTranslation();
  // Oturum açıksa CTA'lar panoya, değilse girişe yönlenir (landing artık kök `/`).
  const girisYapildi = useAuthStore((s) => s.girisYapildi);
  const girisHedef = girisYapildi ? '/pano' : '/giris';
  const girisEtiket = girisYapildi ? t('tanitim.nav_pano') : t('tanitim.nav_giris');

  return (
    <div className="tanitim" id="tepe">
      <header className="tn-nav">
        <div className="tn-kap">
          <Link to="/" className="tn-nav-marka" aria-label="FabrikaOS">
            <Marka boyut={28} />
          </Link>
          <nav className="tn-nav-menu">
            <a href="#moduller">{t('tanitim.nav_moduller')}</a>
            <a href="#nasil">{t('tanitim.nav_nasil')}</a>
            <a href="#platform">{t('tanitim.nav_platform')}</a>
          </nav>
          <Link to={girisHedef} className="tn-dugme birincil kucuk tn-nav-giris">
            {girisEtiket}
          </Link>
        </div>
      </header>

      <main>
        {/* Hero */}
        <section className="tn-kap">
          <div className="tn-hero">
            <div>
              <span className="tn-rozet tn-belir">
                <span className="canli-nokta" aria-hidden="true" />
                {t('tanitim.hero_rozet')}
              </span>
              <h1 className="tn-h1 tn-belir">
                {t('tanitim.hero_baslik_1')}
                <br />
                <span className="vurgu">{t('tanitim.hero_baslik_2')}</span>
              </h1>
              <p className="tn-alt tn-belir tn-belir-2">{t('tanitim.hero_alt')}</p>
              <div className="tn-hero-cta tn-belir tn-belir-2">
                <Link to={girisHedef} className="tn-dugme birincil">
                  {t('tanitim.hero_cta_giris')}
                </Link>
                <a href="#moduller" className="tn-dugme ikincil">
                  {t('tanitim.hero_cta_modul')}
                </a>
              </div>
            </div>
            <HeroEnstruman />
          </div>
        </section>

        {/* Yetenek şeridi */}
        <section className="tn-kap">
          <div className="tn-serit">
            {CIPLER.map((c) => (
              <span
                key={c.anahtar}
                className="tn-cip"
                style={{ '--cip-renk': c.renk } as CSSProperties}
              >
                <span className="nokta" aria-hidden="true" />
                {t(`tanitim.cip_${c.anahtar}`)}
              </span>
            ))}
          </div>
        </section>

        {/* Modül vitrini */}
        <section className="tn-bolum" id="moduller">
          <div className="tn-kap">
            <div className="tn-bolum-bas">
              <div className="tn-etiket">{t('tanitim.moduller_etiket')}</div>
              <h2 className="tn-h2">{t('tanitim.moduller_baslik')}</h2>
              <p>{t('tanitim.moduller_alt')}</p>
            </div>
            <div className="tn-modul-izgara">
              {MODULLER.map((m) => (
                <article
                  key={m.anahtar}
                  className={m.genis ? 'tn-modul-kart genis' : 'tn-modul-kart'}
                  style={{ '--hat': m.hat } as CSSProperties}
                >
                  <div className="tn-modul-ikon">{m.ikon}</div>
                  <h3 className="tn-modul-ad">{t(`tanitim.mod_${m.anahtar}_ad`)}</h3>
                  <p className="tn-modul-aciklama">{t(`tanitim.mod_${m.anahtar}_ac`)}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Veri akışı */}
        <section className="tn-bolum" id="nasil">
          <div className="tn-kap">
            <div className="tn-bolum-bas">
              <div className="tn-etiket">{t('tanitim.nasil_etiket')}</div>
              <h2 className="tn-h2">{t('tanitim.nasil_baslik')}</h2>
              <p>{t('tanitim.nasil_alt')}</p>
            </div>
            <div className="tn-akis">
              {AKIS.map((a, i) => (
                <div key={a} className="tn-adim">
                  <div className="tn-adim-no">{i + 1}</div>
                  <h3 className="tn-adim-ad">{t(`tanitim.adim_${a}_ad`)}</h3>
                  <p>{t(`tanitim.adim_${a}_ac`)}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Persona */}
        <section className="tn-bolum">
          <div className="tn-kap">
            <div className="tn-bolum-bas">
              <div className="tn-etiket">{t('tanitim.persona_etiket')}</div>
              <h2 className="tn-h2">{t('tanitim.persona_baslik')}</h2>
              <p>{t('tanitim.persona_alt')}</p>
            </div>
            <div className="tn-izgara-3">
              {PERSONALAR.map((p) => (
                <article key={p.anahtar} className="tn-kart">
                  <div className="tn-kart-ikon">{p.ikon}</div>
                  <h3 className="tn-kart-ad">{t(`tanitim.persona_${p.anahtar}_ad`)}</h3>
                  <p>{t(`tanitim.persona_${p.anahtar}_ac`)}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Platform */}
        <section className="tn-bolum" id="platform">
          <div className="tn-kap">
            <div className="tn-bolum-bas">
              <div className="tn-etiket">{t('tanitim.platform_etiket')}</div>
              <h2 className="tn-h2">{t('tanitim.platform_baslik')}</h2>
              <p>{t('tanitim.platform_alt')}</p>
            </div>
            <div className="tn-izgara-2x3">
              {PLATFORM.map((p) => (
                <article key={p.anahtar} className="tn-kart">
                  <div className="tn-kart-ikon">{p.ikon}</div>
                  <h3 className="tn-kart-ad">{t(`tanitim.plat_${p.anahtar}_ad`)}</h3>
                  <p>{t(`tanitim.plat_${p.anahtar}_ac`)}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Kapanış CTA */}
        <section className="tn-kap">
          <div className="tn-cta-band">
            <h2>{t('tanitim.cta_baslik')}</h2>
            <p>{t('tanitim.cta_alt')}</p>
            <Link to={girisHedef} className="tn-dugme birincil">
              {girisYapildi ? girisEtiket : t('tanitim.cta_dugme')}
            </Link>
          </div>
        </section>
      </main>

      <footer className="tn-footer">
        <div className="tn-kap">
          <Marka boyut={24} />
          <div className="tn-footer-sag">
            <a href="#moduller">{t('tanitim.nav_moduller')}</a>
            <a href="#platform">{t('tanitim.nav_platform')}</a>
            <Link to={girisHedef}>{girisEtiket}</Link>
            <span className="sayisal">{t('tanitim.footer_telif')}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
