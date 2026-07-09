/**
 * Ant Design v5 koyu tema — "premium dark SaaS": nötr antrasit zemin (R=G=B, lacivert
 * değil), mavi YALNIZCA vurgu (aksiyon/aktif/seçim), yumuşak yuvarlak kartlar, ince
 * düşük-kontrast kenarlık. Değerler index.css CSS değişkenleriyle hizalıdır (AntD renk
 * algoritması hex bekler). Nötr rampa referansı: koyu kontrol-odası panoları (#101010/#181818).
 */

import { theme, type ThemeConfig } from 'antd';

export const RENKLER = {
  zemin: '#0e0e0f',
  yuzey: '#161617',
  yuzey2: '#0b0b0c',
  yuzeyUst: '#1d1d1f',
  kenarlik: '#262628',
  kenarlikParlak: '#34343a',
  metin: '#f4f4f6',
  metinSoluk: '#8c8c92',
  mavi: '#3b6ef6',
  maviKoyu: '#315fd6',
  cyan: '#38bdf8',
  basari: '#22c55e',
  uyari: '#f59e0b',
  hata: '#ef4444',
  mor: '#8b5cf6',
} as const;

/** Grafik/kategorik veri serisi paleti (OEE: kullanılabilirlik/performans/kalite vb.). */
export const GRAFIK_PALETI = [
  RENKLER.mavi,
  RENKLER.basari,
  RENKLER.uyari,
  RENKLER.mor,
  RENKLER.cyan,
  RENKLER.hata,
];

const FONT_GOVDE =
  "'Inter Variable', 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
const FONT_MONO = "'JetBrains Mono Variable', ui-monospace, 'Cascadia Code', 'Consolas', monospace";

/** Açılır katmanlar (dropdown/popover/modal): karartı + 1px ışık halkası — koyu zeminde net kenar. */
const KATMAN_GOLGE = '0 12px 32px -8px rgba(0, 0, 0, 0.65), 0 0 0 1px #2a2a2d';

export const tema: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: RENKLER.mavi,
    colorInfo: RENKLER.cyan,
    colorSuccess: RENKLER.basari,
    colorWarning: RENKLER.uyari,
    colorError: RENKLER.hata,

    colorBgBase: RENKLER.zemin,
    colorBgContainer: RENKLER.yuzey,
    colorBgElevated: RENKLER.yuzeyUst,
    colorBorder: RENKLER.kenarlik,
    colorBorderSecondary: '#1e1e20',
    colorText: RENKLER.metin,
    colorTextSecondary: RENKLER.metinSoluk,

    fontFamily: FONT_GOVDE,
    fontFamilyCode: FONT_MONO,
    fontSize: 14,
    borderRadius: 10,
    wireframe: false,
    motionDurationMid: '0.18s',
    controlHeight: 38,

    boxShadow: KATMAN_GOLGE,
    boxShadowSecondary: KATMAN_GOLGE,
  },
  components: {
    Layout: {
      headerBg: RENKLER.zemin,
      siderBg: RENKLER.yuzey2,
      bodyBg: RENKLER.zemin,
      headerHeight: 64,
    },
    Menu: {
      itemBg: 'transparent',
      subMenuItemBg: 'transparent',
      itemSelectedBg: 'rgba(59, 110, 246, 0.14)',
      itemSelectedColor: '#ffffff',
      itemColor: RENKLER.metinSoluk,
      itemHoverColor: RENKLER.metin,
      itemHoverBg: 'rgba(255,255,255,0.04)',
      itemBorderRadius: 10,
      itemHeight: 40,
      itemMarginBlock: 2,
      iconSize: 17,
      groupTitleColor: '#6d6d74',
    },
    Card: {
      colorBgContainer: RENKLER.yuzey,
      borderRadiusLG: 16,
      paddingLG: 20,
      headerFontSize: 15,
    },
    Button: {
      primaryShadow: 'none',
      defaultShadow: 'none',
      dangerShadow: 'none',
      fontWeight: 600,
      controlHeight: 40,
    },
    Table: {
      headerBg: 'transparent',
      headerColor: RENKLER.metinSoluk,
      headerSplitColor: 'transparent',
      borderColor: RENKLER.kenarlik,
      rowHoverBg: 'rgba(255,255,255,0.03)',
      cellPaddingBlock: 14,
    },
    Input: {
      colorBgContainer: RENKLER.yuzeyUst,
      activeBorderColor: RENKLER.mavi,
    },
    InputNumber: {
      colorBgContainer: RENKLER.yuzeyUst,
    },
    Select: {
      colorBgContainer: RENKLER.yuzeyUst,
      optionSelectedBg: 'rgba(59, 110, 246, 0.16)',
    },
    DatePicker: {
      colorBgContainer: RENKLER.yuzeyUst,
    },
    Segmented: {
      itemSelectedBg: RENKLER.yuzeyUst,
      trackBg: RENKLER.yuzey2,
    },
    Tabs: {
      itemColor: RENKLER.metinSoluk,
      itemHoverColor: RENKLER.metin,
      inkBarColor: RENKLER.mavi,
      horizontalMargin: '0 0 20px 0',
    },
    Modal: {
      contentBg: RENKLER.yuzey,
      headerBg: RENKLER.yuzey,
      titleFontSize: 16,
    },
    Drawer: {
      colorBgElevated: RENKLER.yuzey,
    },
    Tooltip: {
      colorBgSpotlight: '#28282c',
    },
    Descriptions: {
      colorTextSecondary: RENKLER.metinSoluk,
      titleMarginBottom: 12,
    },
    Statistic: {
      titleFontSize: 13,
      contentFontSize: 22,
    },
    Skeleton: {
      gradientFromColor: 'rgba(255,255,255,0.045)',
      gradientToColor: 'rgba(255,255,255,0.10)',
    },
    Tag: {
      defaultBg: RENKLER.yuzeyUst,
    },
    Alert: {
      colorInfoBg: 'rgba(56, 189, 248, 0.09)',
      colorInfoBorder: 'rgba(56, 189, 248, 0.28)',
      colorErrorBg: 'rgba(239, 68, 68, 0.09)',
      colorErrorBorder: 'rgba(239, 68, 68, 0.28)',
      colorWarningBg: 'rgba(245, 158, 11, 0.09)',
      colorWarningBorder: 'rgba(245, 158, 11, 0.28)',
      colorSuccessBg: 'rgba(34, 197, 94, 0.09)',
      colorSuccessBorder: 'rgba(34, 197, 94, 0.28)',
    },
  },
};
