/**
 * Modül kimlik sistemi — "hat rengi" (endüstriyel hat/boru renk kodlaması metaforu).
 *
 * Her menü bölümü bir hat rengi taşır; sayfa başlığı ikon plakası, kenar çubuğu grup
 * noktası ve KPI ikonları bu tek kaynaktan beslenir. Renk %2-3 yüzeyde kalır (kimlik
 * sinyali, dekorasyon değil) — DESIGN.md "Restrained" stratejisi korunur.
 */

import type { ReactNode } from 'react';
import {
  AlertOutlined,
  AreaChartOutlined,
  BankOutlined,
  CalendarOutlined,
  DashboardOutlined,
  ExperimentOutlined,
  FileDoneOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  FolderOpenOutlined,
  FundOutlined,
  GoldOutlined,
  IdcardOutlined,
  InboxOutlined,
  IssuesCloseOutlined,
  LineChartOutlined,
  MedicineBoxOutlined,
  NotificationOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  SafetyOutlined,
  ShoppingCartOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  ToolOutlined,
  WifiOutlined,
} from '@ant-design/icons';

import { MENU } from '@/layouts/menu';

/** Bölüm → hat rengi (index.css `--hat-*` değişkenleriyle hizalı). */
export const BOLUM_RENGI: Record<string, string> = {
  'menu.bolum_genel': '#3b6ef6',
  'menu.bolum_uretim': '#38bdf8',
  'menu.bolum_stok': '#2dd4bf',
  'menu.bolum_kalite': '#8b5cf6',
  'menu.bolum_isg_ik': '#f59e0b',
  'menu.bolum_ticari': '#34d399',
  'menu.bolum_dokuman': '#f472b6',
  'menu.bolum_zeka': '#d946ef',
  'menu.bolum_yonetim': '#94a3b8',
};

/** Menü anahtarı → modül ikonu (kenar çubuğu + sayfa başlığı plakası aynı dili konuşur). */
export const MENU_IKONLARI: Record<string, ReactNode> = {
  pano: <DashboardOutlined />,
  makineler: <RobotOutlined />,
  'uretim-verileri': <LineChartOutlined />,
  'is-emirleri': <FileDoneOutlined />,
  'saha-cihazlar': <WifiOutlined />,
  bakim: <ToolOutlined />,
  malzemeler: <GoldOutlined />,
  'kritik-stok': <AlertOutlined />,
  satinalma: <ShoppingCartOutlined />,
  kalite: <SafetyCertificateOutlined />,
  uygunsuzluklar: <IssuesCloseOutlined />,
  enerji: <ThunderboltOutlined />,
  'is-kazalari': <MedicineBoxOutlined />,
  'risk-degerlendirme': <SafetyOutlined />,
  personeller: <TeamOutlined />,
  'izin-talepleri': <CalendarOutlined />,
  'ticari-pano': <FundOutlined />,
  firmalar: <BankOutlined />,
  sozlesmeler: <FileProtectOutlined />,
  talepler: <InboxOutlined />,
  belgeler: <FolderOpenOutlined />,
  duyurular: <NotificationOutlined />,
  tahminler: <ExperimentOutlined />,
  analitik: <AreaChartOutlined />,
  raporlar: <FileTextOutlined />,
  kullanicilar: <IdcardOutlined />,
};

export type ModulKimlik = {
  /** Bölüm i18n anahtarı (ör. 'menu.bolum_uretim'). */
  bolum: string;
  /** Hat rengi (hex). */
  renk: string;
  /** Modül ikonu. */
  ikon: ReactNode;
  /** Sayfa etiketi i18n anahtarı (ör. 'menu.makineler'). */
  etiketAnahtari: string;
};

const VARSAYILAN: ModulKimlik = {
  bolum: 'menu.bolum_genel',
  renk: '#3b6ef6',
  ikon: <DashboardOutlined />,
  etiketAnahtari: 'menu.pano',
};

/** Rota yolundan modül kimliğini çözer (en uzun önek eşleşmesi; detay yolları da eşleşir). */
export function yolKimlik(pathname: string): ModulKimlik {
  const oge = MENU.filter(
    (o) => pathname === o.yol || (o.yol !== '/' && pathname.startsWith(o.yol)),
  ).sort((a, b) => b.yol.length - a.yol.length)[0];
  if (!oge) return VARSAYILAN;
  return {
    bolum: oge.bolum,
    renk: BOLUM_RENGI[oge.bolum] ?? VARSAYILAN.renk,
    ikon: MENU_IKONLARI[oge.anahtar] ?? VARSAYILAN.ikon,
    etiketAnahtari: oge.etiketAnahtari,
  };
}
