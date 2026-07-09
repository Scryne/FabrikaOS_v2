/**
 * Uygulama kabuğu — bölümlü sol kenar çubuğu (RBAC filtreli menü + hat renkli grup başlıkları
 * + alt tenant kartı) + üst bar (arama, saat, canlı durum, dil, bildirim, kullanıcı+rol) +
 * içerik (Outlet). Modül ikonları/renkleri tek kaynaktan: tema/modulKimlik.
 */

import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  BellOutlined,
  DownOutlined,
  GlobalOutlined,
  LogoutOutlined,
  SearchOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Dropdown, Layout, Menu } from 'antd';
import type { CSSProperties } from 'react';
import type { MenuProps } from 'antd';

import { cikisYap } from '@/api/kimlik';
import { cozumleTenant } from '@/api/tenant';
import { KomutPaleti } from '@/components/KomutPaleti';
import { LogoIsareti } from '@/components/Marka';
import { DILLER, dilDegistir } from '@/i18n';
import { gorunurMenu, MENU } from '@/layouts/menu';
import { useGercekZaman } from '@/modules/ortak/gercekZamanBaglam';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI, MENU_IKONLARI } from '@/tema/modulKimlik';

function basharfler(ad: string): string {
  return (
    ad
      .split(' ')
      .map((p) => p[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || '?'
  );
}

/** Üst bar saati — kontrol odası bağlamı (dakika hassasiyeti; 15 sn'de bir tazelenir). */
function BarSaat() {
  const { i18n } = useTranslation();
  const [simdi, setSimdi] = useState(() => new Date());
  useEffect(() => {
    const sayac = setInterval(() => setSimdi(new Date()), 15_000);
    return () => clearInterval(sayac);
  }, []);
  const tarih = new Intl.DateTimeFormat(i18n.language, { day: '2-digit', month: 'short' }).format(
    simdi,
  );
  const saat = new Intl.DateTimeFormat(i18n.language, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(simdi);
  return (
    <span
      className="sayisal"
      style={{ color: 'var(--metin-soluk)', fontSize: 12.5, whiteSpace: 'nowrap' }}
    >
      {tarih} · {saat}
    </span>
  );
}

export function UygulamaKabugu() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const konum = useLocation();
  const kullanici = useAuthStore((s) => s.kullanici);
  // izinler'e (Set) abone ol: oturum/izinler değişince menü yeniden hesaplanır
  // (s.izinVar sabit fonksiyon referansıdır; memo'yu tetiklemez).
  const izinler = useAuthStore((s) => s.izinler);
  const { bagli } = useGercekZaman();
  const [paletAcik, setPaletAcik] = useState(false);

  // Global ⌘K / Ctrl+K → komut paletini aç (form alanında da çalışır).
  useEffect(() => {
    const isle = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletAcik(true);
      }
    };
    window.addEventListener('keydown', isle);
    return () => window.removeEventListener('keydown', isle);
  }, []);

  const kisayolEtiket =
    typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.userAgent)
      ? '⌘K'
      : 'Ctrl K';

  const tenant = cozumleTenant();
  const gorunur = useMemo(() => gorunurMenu(MENU, (izin) => izinler.has(izin)), [izinler]);

  // Bölümlere göre grupla (sidebar grup başlıkları — hat rengi noktası ile).
  const menuOgeleri: MenuProps['items'] = useMemo(() => {
    const bolumler = [...new Set(gorunur.map((o) => o.bolum))];
    return bolumler.map((b) => ({
      type: 'group' as const,
      key: b,
      label: (
        <span className="menu-grup" style={{ '--hat': BOLUM_RENGI[b] } as CSSProperties}>
          <i className="hat-nokta" aria-hidden="true" />
          {t(b)}
        </span>
      ),
      children: gorunur
        .filter((o) => o.bolum === b)
        .map((o) => ({ key: o.yol, icon: MENU_IKONLARI[o.anahtar], label: t(o.etiketAnahtari) })),
    }));
  }, [gorunur, t]);

  const seciliYol =
    gorunur
      .map((o) => o.yol)
      .filter((y) => konum.pathname === y || (y !== '/' && konum.pathname.startsWith(y)))
      .sort((a, b) => b.length - a.length)[0] ?? '/';

  const dilMenusu: MenuProps['items'] = Object.entries(DILLER).map(([kod, ad]) => ({
    key: kod,
    label: ad,
    onClick: () => dilDegistir(kod),
  }));

  const kullaniciMenusu: MenuProps['items'] = [
    {
      key: 'cikis',
      icon: <LogoutOutlined />,
      label: t('ortak.cikis'),
      onClick: async () => {
        await cikisYap();
        navigate('/giris', { replace: true });
      },
    },
  ];

  const rol = kullanici?.roller[0];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider
        breakpoint="lg"
        collapsedWidth="0"
        width={248}
        style={{ borderRight: '1px solid var(--kenarlik)' }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {/* Marka */}
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '0 20px',
              borderBottom: '1px solid var(--kenarlik)',
              flexShrink: 0,
            }}
          >
            <LogoIsareti boyut={26} />
            <span style={{ fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--metin)' }}>
              Fabrika<span style={{ color: 'var(--mavi)' }}>OS</span>
            </span>
          </div>

          {/* Bölümlü menü */}
          <Menu
            mode="inline"
            selectedKeys={[seciliYol]}
            items={menuOgeleri}
            onClick={({ key }) => navigate(key)}
            style={{
              borderInlineEnd: 'none',
              flex: 1,
              padding: '6px 12px 12px',
              overflowY: 'auto',
            }}
          />

          {/* Alt: tenant (çalışma alanı) kartı */}
          {tenant && (
            <div style={{ padding: 12, borderTop: '1px solid var(--kenarlik)', flexShrink: 0 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 12px',
                  background: 'var(--yuzey)',
                  border: '1px solid var(--kenarlik)',
                  borderRadius: 12,
                }}
              >
                <span
                  className="sayisal"
                  aria-hidden="true"
                  style={{
                    width: 32,
                    height: 32,
                    flexShrink: 0,
                    display: 'grid',
                    placeItems: 'center',
                    borderRadius: 9,
                    background: 'rgba(59,110,246,0.14)',
                    border: '1px solid rgba(59,110,246,0.28)',
                    color: 'var(--mavi)',
                    fontSize: 12,
                    fontWeight: 700,
                    textTransform: 'uppercase',
                  }}
                >
                  {tenant.slice(0, 2)}
                </span>
                <div style={{ lineHeight: 1.3, overflow: 'hidden' }}>
                  <div
                    className="sayisal"
                    style={{
                      color: 'var(--metin)',
                      fontWeight: 600,
                      fontSize: 13,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {tenant}
                  </div>
                  <div style={{ color: 'var(--metin-soluk)', fontSize: 11 }}>
                    {t('ortak.calisma_alani')}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </Layout.Sider>

      <Layout>
        <Layout.Header
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: '0 24px',
            borderBottom: '1px solid var(--kenarlik)',
          }}
        >
          <button type="button" className="komut-tetik" onClick={() => setPaletAcik(true)}>
            <SearchOutlined style={{ color: 'var(--metin-soluk)' }} />
            <span className="tetik-metin">{t('ortak.ara')}</span>
            <kbd className="komut-kisayol">{kisayolEtiket}</kbd>
          </button>
          <div style={{ flex: 1 }} />

          <BarSaat />

          {/* Gerçek-zaman bağlantı durumu (renk + nokta + etiket; renk tek başına değil). */}
          <span className="canli-rozet">
            {bagli ? (
              <>
                <span className="canli-nokta" aria-hidden="true" />
                {t('ortak.canli')}
              </>
            ) : (
              <>
                <span
                  className="durum-nokta"
                  aria-hidden="true"
                  style={{ background: 'var(--uyari)' }}
                />
                {t('ortak.baglaniyor')}
              </>
            )}
          </span>

          <span className="bar-ayrac" aria-hidden="true" />

          <Dropdown menu={{ items: dilMenusu }} trigger={['click']}>
            <button type="button" className="bar-dugme" aria-label={t('ortak.dil')}>
              <GlobalOutlined />
            </button>
          </Dropdown>

          <button type="button" className="bar-dugme" aria-label={t('ortak.bildirimler')}>
            <Badge dot offset={[-1, 3]} color="var(--mavi)">
              <BellOutlined style={{ fontSize: 17, color: 'inherit' }} />
            </Badge>
          </button>

          <span className="bar-ayrac" aria-hidden="true" />

          <Dropdown menu={{ items: kullaniciMenusu }} trigger={['click']}>
            <button type="button" className="kullanici-cip">
              <Avatar
                size={32}
                style={{ backgroundColor: 'rgba(59,110,246,0.18)', color: 'var(--mavi)' }}
                icon={kullanici ? undefined : <UserOutlined />}
              >
                {kullanici ? basharfler(kullanici.ad_soyad || kullanici.eposta) : null}
              </Avatar>
              <span style={{ lineHeight: 1.25, textAlign: 'left' }}>
                <span
                  style={{
                    display: 'block',
                    color: 'var(--metin)',
                    fontSize: 13,
                    fontWeight: 600,
                  }}
                >
                  {kullanici?.ad_soyad}
                </span>
                {rol && (
                  <span
                    style={{
                      display: 'block',
                      color: 'var(--metin-soluk)',
                      fontSize: 11,
                      textTransform: 'capitalize',
                    }}
                  >
                    {rol}
                  </span>
                )}
              </span>
              <DownOutlined style={{ fontSize: 10, color: 'var(--metin-soluk)' }} />
            </button>
          </Dropdown>
        </Layout.Header>

        <Layout.Content style={{ padding: '28px 32px' }}>
          <div className="icerik-acilis">
            <Outlet />
          </div>
        </Layout.Content>
      </Layout>

      <KomutPaleti acik={paletAcik} kapat={() => setPaletAcik(false)} />
    </Layout>
  );
}
