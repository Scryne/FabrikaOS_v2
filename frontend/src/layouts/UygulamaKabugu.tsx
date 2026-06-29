/**
 * Uygulama kabuğu — sol kenar çubuğu (RBAC'a göre filtrelenmiş menü) + üst bar
 * (tenant rozeti, canlı gösterge, dil, kullanıcı/çıkış) + içerik (Outlet).
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  FileDoneOutlined,
  GlobalOutlined,
  LogoutOutlined,
  TeamOutlined,
  ToolOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Dropdown, Layout, Menu, Space, Typography } from 'antd';
import type { MenuProps } from 'antd';

import { cikisYap } from '@/api/kimlik';
import { cozumleTenant } from '@/api/tenant';
import { LogoIsareti } from '@/components/Marka';
import { DILLER, dilDegistir } from '@/i18n';
import { gorunurMenu, MENU } from '@/layouts/menu';
import { useAuthStore } from '@/store/authStore';

const IKONLAR: Record<string, React.ReactNode> = {
  pano: <DashboardOutlined />,
  makineler: <ToolOutlined />,
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
  const izinVar = useAuthStore((s) => s.izinVar);

  const tenant = cozumleTenant();
  const ogeler = useMemo(() => gorunurMenu(MENU, izinVar), [izinVar]);

  const menuOgeleri: MenuProps['items'] = ogeler.map((o) => ({
    key: o.yol,
    icon: IKONLAR[o.anahtar],
    label: t(o.etiketAnahtari),
  }));

  // En uzun eşleşen yolu seçili göster (örn. /is-emirleri/5 → /is-emirleri).
  const seciliYol =
    ogeler
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

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Layout.Sider
        breakpoint="lg"
        collapsedWidth="0"
        width={232}
        style={{ borderRight: '1px solid var(--kenarlik)' }}
      >
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '0 18px',
            borderBottom: '1px solid var(--kenarlik)',
          }}
        >
          <LogoIsareti boyut={26} />
          <span style={{ fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--metin)' }}>
            Fabrika<span style={{ color: 'var(--amber)' }}>OS</span>
          </span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[seciliYol]}
          items={menuOgeleri}
          onClick={({ key }) => navigate(key)}
          style={{ borderInlineEnd: 'none', paddingTop: 8 }}
        />
      </Layout.Sider>

      <Layout>
        <Layout.Header
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            padding: '0 20px',
            borderBottom: '1px solid var(--kenarlik)',
          }}
        >
          {tenant && (
            <Space size={8} className="giris-durum">
              <span className="canli-nokta" aria-hidden="true" />
              <span className="sayisal" style={{ color: 'var(--metin)', fontWeight: 600 }}>
                {tenant}
              </span>
            </Space>
          )}
          <div style={{ flex: 1 }} />

          <Dropdown menu={{ items: dilMenusu }} trigger={['click']}>
            <Typography.Link aria-label={t('ortak.dil')} style={{ color: 'var(--metin-soluk)' }}>
              <GlobalOutlined style={{ fontSize: 18 }} />
            </Typography.Link>
          </Dropdown>

          <Dropdown menu={{ items: kullaniciMenusu }} trigger={['click']}>
            <Space style={{ cursor: 'pointer' }}>
              <Avatar
                size="small"
                style={{ backgroundColor: 'rgba(245,165,36,0.18)', color: 'var(--amber)' }}
                icon={kullanici ? undefined : <UserOutlined />}
              >
                {kullanici ? basharfler(kullanici.ad_soyad || kullanici.eposta) : null}
              </Avatar>
              <span style={{ color: 'var(--metin)' }}>{kullanici?.ad_soyad}</span>
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
