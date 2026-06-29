/**
 * Ant Design v5 koyu tema — endüstriyel kontrol odası "deri"si (bkz. DESIGN.md).
 *
 * AntD motoru (Table/Form/...) bu token'larla giydirilir; değerler CSS değişkenleriyle
 * (index.css) hizalıdır. AntD renk algoritması hex beklediğinden değerler hex'tir.
 */

import { theme, type ThemeConfig } from 'antd';

export const RENKLER = {
  zemin: '#0b0f14',
  yuzey: '#131a24',
  yuzey2: '#1a2330',
  kenarlik: '#26303f',
  metin: '#e6edf3',
  metinSoluk: '#94a3b8',
  amber: '#f5a524',
  cyan: '#22d3ee',
  basari: '#10b981',
  uyari: '#fb923c',
  hata: '#ef4444',
} as const;

const FONT_GOVDE =
  "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif";
const FONT_MONO = "ui-monospace, 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace";

export const tema: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: RENKLER.amber,
    colorInfo: RENKLER.cyan,
    colorSuccess: RENKLER.basari,
    colorWarning: RENKLER.uyari,
    colorError: RENKLER.hata,

    colorBgBase: RENKLER.zemin,
    colorBgContainer: RENKLER.yuzey,
    colorBgElevated: RENKLER.yuzey2,
    colorBorder: RENKLER.kenarlik,
    colorText: RENKLER.metin,
    colorTextSecondary: RENKLER.metinSoluk,

    fontFamily: FONT_GOVDE,
    fontFamilyCode: FONT_MONO,
    borderRadius: 6,
    wireframe: false,
    motionDurationMid: '0.18s',
  },
  components: {
    Layout: {
      headerBg: RENKLER.yuzey2,
      siderBg: RENKLER.yuzey2,
      bodyBg: RENKLER.zemin,
      headerHeight: 56,
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(245, 165, 36, 0.14)',
      itemSelectedColor: RENKLER.amber,
      itemHoverColor: RENKLER.metin,
    },
    Button: {
      primaryShadow: 'none',
      fontWeight: 600,
      // Amber (açık) birincil üzerinde KOYU metin — beyaz metin AA kontrastı geçmez.
      primaryColor: RENKLER.zemin,
    },
  },
};
