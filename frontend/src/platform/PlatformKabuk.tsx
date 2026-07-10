/**
 * Platform kabuğu — tenant kabuğundan AYRIK, sade control-plane düzeni: sol menü
 * (Tenantlar / Abonelikler / Sağlık) + üst barda kalıcı PLATFORM filigran çipi +
 * yönetici kimliği. Turuncu "platform" hattı yalnız bu düzlemde kullanılır.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  ApartmentOutlined,
  CreditCardOutlined,
  HeartOutlined,
  LogoutOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { Button, Layout, Menu } from 'antd';
import type { MenuProps } from 'antd';

import { LogoIsareti } from '@/components/Marka';

import { platformCikisYap } from './kimlik';
import { usePlatformAuthStore } from './store';
import './platform.css';

const HAT_PLATFORM = '#f97316';

export function PlatformKabuk() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const konum = useLocation();
  const yonetici = usePlatformAuthStore((s) => s.yonetici);

  const menuOgeleri: MenuProps['items'] = useMemo(
    () => [
      { key: '/platform', icon: <ApartmentOutlined />, label: t('platform.tenantlar') },
      {
        key: '/platform/abonelikler',
        icon: <CreditCardOutlined />,
        label: t('platform.abonelikler'),
      },
      { key: '/platform/saglik', icon: <HeartOutlined />, label: t('platform.saglik') },
    ],
    [t],
  );

  // Detay rotaları (/platform/tenantlar/:id, /platform/yeni) listede "Tenantlar"ı seçili tutar.
  const seciliAnahtar = menuOgeleri.some((o) => o?.key === konum.pathname)
    ? konum.pathname
    : '/platform';

  async function cikis() {
    await platformCikisYap();
    navigate('/platform/giris', { replace: true });
  }

  return (
    <Layout className="platform-kabuk">
      <Layout.Sider width={230} style={{ borderRight: '1px solid var(--kenarlik)' }}>
        <div className="platform-marka">
          <LogoIsareti boyut={26} />
          <span className="platform-cip">{t('platform.filigran')}</span>
        </div>
        <Menu
          mode="inline"
          items={menuOgeleri}
          selectedKeys={[seciliAnahtar]}
          onClick={({ key }) => navigate(key)}
          style={{ borderInlineEnd: 'none' }}
        />
        <div style={{ padding: '12px 16px' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={() => navigate('/platform/yeni')}
          >
            {t('platform.yeni_tenant')}
          </Button>
        </div>
      </Layout.Sider>

      <Layout>
        <Layout.Header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            paddingInline: 24,
            borderBottom: `1px solid var(--kenarlik)`,
            background: 'transparent',
          }}
        >
          <span style={{ fontWeight: 600, color: HAT_PLATFORM, letterSpacing: '0.02em' }}>
            {t('platform.baslik')}
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 14, minWidth: 0 }}>
            <span
              style={{
                color: 'var(--metin-soluk)',
                fontSize: 13,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {yonetici?.eposta}
            </span>
            <Button size="small" icon={<LogoutOutlined />} onClick={() => void cikis()}>
              {t('ortak.cikis')}
            </Button>
          </span>
        </Layout.Header>
        <Layout.Content style={{ padding: 24 }}>
          <Outlet />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}
