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
      itemHeight: 42,
      iconSize: 18,
    },
    Card: {
      colorBgContainer: RENKLER.yuzey,
      borderRadiusLG: 16,
      paddingLG: 20,
    },
    Button: {
      primaryShadow: 'none',
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
    Segmented: {
      itemSelectedBg: RENKLER.yuzeyUst,
      trackBg: RENKLER.yuzey2,
    },
  },
};
