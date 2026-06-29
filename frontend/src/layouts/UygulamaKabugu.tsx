/**
 * Uygulama kabuğu — bölümlü sol kenar çubuğu (RBAC filtreli menü + grup başlıkları + alt
 * tenant kartı) + üst bar (arama, bildirim, dil, kullanıcı+rol) + içerik (Outlet).
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  BellOutlined,
  DashboardOutlined,
  DownOutlined,
  FileDoneOutlined,
  GlobalOutlined,
  LineChartOutlined,
  LogoutOutlined,
  SearchOutlined,
  TeamOutlined,
  ToolOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Dropdown, Input, Layout, Menu, Space } from 'antd';
import type { MenuProps } from 'antd';

import { cikisYap } from '@/api/kimlik';
import { cozumleTenant } from '@/api/tenant';
import { LogoIsareti } from '@/components/Marka';
import { DILLER, dilDegistir } from '@/i18n';
import { gorunurMenu, MENU } from '@/layouts/menu';
import { useGercekZaman } from '@/modules/ortak/gercekZamanBaglam';
import { useAuthStore } from '@/store/authStore';

const IKONLAR: Record<string, React.ReactNode> = {
  pano: <DashboardOutlined />,
  makineler: <ToolOutlined />,
  'uretim-verileri': <LineChartOutlined />,
  'is-emirleri': <FileDoneOutlined />,
  bakim: <ToolOutlined />,
  kullanicilar: <TeamOutlined />,
};

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

export function UygulamaKabugu() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const konum = useLocation();
  const kullanici = useAuthStore((s) => s.kullanici);
  // izinler'e (Set) abone ol: oturum/izinler değişince menü yeniden hesaplanır
  // (s.izinVar sabit fonksiyon referansıdır; memo'yu tetiklemez).
  const izinler = useAuthStore((s) => s.izinler);
  const { bagli } = useGercekZaman();

  const tenant = cozumleTenant();
  const gorunur = useMemo(() => gorunurMenu(MENU, (izin) => izinler.has(izin)), [izinler]);

  // Bölümlere göre grupla (sidebar grup başlıkları).
  const menuOgeleri: MenuProps['items'] = useMemo(() => {
    const bolumler = [...new Set(gorunur.map((o) => o.bolum))];
    return bolumler.map((b) => ({
      type: 'group' as const,
      key: b,
      label: t(b),
      children: gorunur
        .filter((o) => o.bolum === b)
        .map((o) => ({ key: o.yol, icon: IKONLAR[o.anahtar], label: t(o.etiketAnahtari) })),
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
            style={{ borderInlineEnd: 'none', flex: 1, padding: '4px 12px', overflowY: 'auto' }}
          />

          {/* Alt: tenant kartı */}
          {tenant && (
            <div style={{ padding: 12 }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  padding: '12px 14px',
                  background: 'var(--yuzey)',
                  border: '1px solid var(--kenarlik)',
                  borderRadius: 12,
                }}
              >
                {bagli ? (
                  <span className="canli-nokta" aria-hidden="true" />
                ) : (
                  <span
                    aria-hidden="true"
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: 'var(--uyari)',
                      flexShrink: 0,
                    }}
                  />
                )}
                <div style={{ lineHeight: 1.25, overflow: 'hidden' }}>
                  <div
                    className="sayisal"
                    style={{ color: 'var(--metin)', fontWeight: 600, fontSize: 13 }}
                  >
                    {tenant}
                  </div>
                  <div style={{ color: 'var(--metin-soluk)', fontSize: 11 }}>
                    {t(bagli ? 'ortak.sistem_cevrimici' : 'ortak.baglaniyor')}
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
            gap: 16,
            padding: '0 24px',
            borderBottom: '1px solid var(--kenarlik)',
          }}
        >
          <Input
            prefix={<SearchOutlined style={{ color: 'var(--metin-soluk)' }} />}
            placeholder={t('ortak.ara')}
            variant="filled"
            style={{ maxWidth: 320 }}
          />
          <div style={{ flex: 1 }} />

          <Dropdown menu={{ items: dilMenusu }} trigger={['click']}>
            <button
              type="button"
              aria-label={t('ortak.dil')}
              style={{
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--metin-soluk)',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <GlobalOutlined style={{ fontSize: 18 }} />
            </button>
          </Dropdown>

          <Badge dot offset={[-2, 4]} color="var(--mavi)">
            <BellOutlined style={{ fontSize: 18, color: 'var(--metin-soluk)' }} />
          </Badge>

          <Dropdown menu={{ items: kullaniciMenusu }} trigger={['click']}>
            <Space style={{ cursor: 'pointer' }} size={10}>
              <Avatar
                size={34}
                style={{ backgroundColor: 'rgba(59,110,246,0.18)', color: 'var(--mavi)' }}
                icon={kullanici ? undefined : <UserOutlined />}
              >
                {kullanici ? basharfler(kullanici.ad_soyad || kullanici.eposta) : null}
              </Avatar>
              <span style={{ lineHeight: 1.2, textAlign: 'right' }}>
                <div style={{ color: 'var(--metin)', fontSize: 13, fontWeight: 600 }}>
                  {kullanici?.ad_soyad}
                </div>
                {rol && (
                  <div
                    style={{
                      color: 'var(--metin-soluk)',
                      fontSize: 11,
                      textTransform: 'capitalize',
                    }}
                  >
                    {rol}
                  </div>
                )}
              </span>
              <DownOutlined style={{ fontSize: 10, color: 'var(--metin-soluk)' }} />
            </Space>
          </Dropdown>
        </Layout.Header>

        <Layout.Content style={{ padding: 24 }}>
          <div className="icerik-acilis">
            <Outlet />
          </div>
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
