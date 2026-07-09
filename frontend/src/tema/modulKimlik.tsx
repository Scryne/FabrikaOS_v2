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
  ApartmentOutlined,
  AreaChartOutlined,
  BankOutlined,
  CalendarOutlined,
  CreditCardOutlined,
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
  ikiz: <ApartmentOutlined />,
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
  abonelik: <CreditCardOutlined />,
};

/**
 * Entitlement modül kodu → menü bölümü (hat rengi kaynağı) + temsilci menü anahtarı
 * (ikon kaynağı). Abonelik ekranındaki modül matrisi bu eşlemeden beslenir (S16).
 */
export const MODUL_KIMLIK: Record<string, { bolum: string; anahtar: string }> = {
  uretim: { bolum: 'menu.bolum_uretim', anahtar: 'makineler' },
  saha: { bolum: 'menu.bolum_uretim', anahtar: 'saha-cihazlar' },
  isemri: { bolum: 'menu.bolum_uretim', anahtar: 'is-emirleri' },
  bakim: { bolum: 'menu.bolum_uretim', anahtar: 'bakim' },
  stok: { bolum: 'menu.bolum_stok', anahtar: 'malzemeler' },
  kalite: { bolum: 'menu.bolum_kalite', anahtar: 'kalite' },
  enerji: { bolum: 'menu.bolum_kalite', anahtar: 'enerji' },
  isg: { bolum: 'menu.bolum_isg_ik', anahtar: 'is-kazalari' },
  ik: { bolum: 'menu.bolum_isg_ik', anahtar: 'personeller' },
  crm: { bolum: 'menu.bolum_ticari', anahtar: 'firmalar' },
  sozlesme: { bolum: 'menu.bolum_ticari', anahtar: 'sozlesmeler' },
  talep: { bolum: 'menu.bolum_ticari', anahtar: 'talepler' },
  dys: { bolum: 'menu.bolum_dokuman', anahtar: 'belgeler' },
  duyuru: { bolum: 'menu.bolum_dokuman', anahtar: 'duyurular' },
  ai: { bolum: 'menu.bolum_zeka', anahtar: 'tahminler' },
  analitik: { bolum: 'menu.bolum_zeka', anahtar: 'analitik' },
  rapor: { bolum: 'menu.bolum_zeka', anahtar: 'raporlar' },
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
