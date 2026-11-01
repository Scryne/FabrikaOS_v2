/**
 * S25-B satınalma siparişi → teslim alma → iade hook'ları (ADR-0024 §3, §4b).
 * Teslim ve iade stok bakiyesini değiştirdiği için depo/malzeme sorgularını da geçersizleştirir.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, istekIndir, istekSayfali, PREFIX } from '@/api/client';
import { pimUret } from '@/components/DurumPim';
import { RENKLER } from '@/tema/tema';

import { STOK_ANAHTAR } from './hooks';

export type SiparisDurum = 'acik' | 'kismi_teslim' | 'tamamlandi' | 'kapatildi' | 'iptal';

/** Sipariş durum pimi (nokta + metin; liste ve detayda aynı dil). */
export const SiparisPim = pimUret(
  {
    acik: RENKLER.mavi,
    kismi_teslim: RENKLER.uyari,
    tamamlandi: RENKLER.basari,
    kapatildi: RENKLER.metinSoluk,
    iptal: '#4b4b52',
  },
  'siparis.durum_',
);

export interface SiparisOzet {
  id: number;
  kod: string;
  talep_id: number;
  tedarikci_firma_id: number;
  tedarikci_ad: string | null;
  durum: SiparisDurum;
  para_birimi: string;
  beklenen_teslim_tarihi: string | null;
  aciklama: string;
  kapanis_nedeni: string | null;
  kalem_sayisi: number;
  toplam_tutar: number;
  teslim_orani: number;
  olusturma_tarihi: string | null;
}

export interface SiparisKalem {
  id: number;
  malzeme_id: number;
  malzeme_kod: string | null;
  malzeme_ad: string | null;
  birim: string | null;
  lot_takipli: boolean;
  miktar: number;
  teslim_alinan_miktar: number;
  kalan_miktar: number;
  birim_fiyat: number | null;
  fazla_teslim_toleransi_yuzde: number;
}

export interface TeslimKalem {
  id: number;
  siparis_kalemi_id: number;
  malzeme_kod: string | null;
  malzeme_ad: string | null;
  birim: string | null;
  miktar: number;
  iade_edilen_miktar: number;
  lokasyon_id: number;
  lokasyon: string | null;
  lot_no: string;
  fazla_teslim: boolean;
  hizli_kabulden: boolean;
}

export interface Teslim {
  id: number;
  tur: 'teslim' | 'iade';
  irsaliye_no: string;
  iade_edilen_id: number | null;
  fiili_tarih: string;
  zamaninda: boolean | null;
  aciklama: string;
  kalemler: TeslimKalem[];
}

export interface SiparisDetay extends SiparisOzet {
  kalemler: SiparisKalem[];
  teslimler: Teslim[];
}

export interface EslesmemisKabul {
  hareket_id: number;
  malzeme_id: number;
  malzeme_kod: string;
  malzeme_ad: string;
  birim: string;
  miktar: number;
  irsaliye_no: string;
  lokasyon: string | null;
  lot_no: string;
  olusturma_tarihi: string;
  bekleyen_gun: number;
}

export interface TedarikciSecenek {
  id: number;
  ad: string;
}

export const SIPARIS_ANAHTAR = {
  liste: (filtre: SiparisFiltre) => ['satinalma-siparisleri', filtre] as const,
  detay: (id: number) => ['satinalma-siparisi', id] as const,
  eslesmemis: ['eslesmemis-hizli-kabul'] as const,
  tedarikciler: ['tedarikci-secenekleri'] as const,
};

export type SiparisFiltre = { durum?: SiparisDurum; talep_id?: number };

/** Beklenen tarihi geçmiş ve hâlâ teslim bekleyen sipariş (yerel gün). */
export function gecikmis(s: Pick<SiparisOzet, 'durum' | 'beklenen_teslim_tarihi'>): boolean {
  if (!s.beklenen_teslim_tarihi) return false;
  if (s.durum !== 'acik' && s.durum !== 'kismi_teslim') return false;
  const bugun = new Date();
  const yerel = `${bugun.getFullYear()}-${String(bugun.getMonth() + 1).padStart(2, '0')}-${String(
    bugun.getDate(),
  ).padStart(2, '0')}`;
  return s.beklenen_teslim_tarihi < yerel;
}

function useHataBildir() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useSiparisler(filtre: SiparisFiltre = {}, etkin = true) {
  const q = new URLSearchParams();
  if (filtre.durum) q.set('durum', filtre.durum);
  if (filtre.talep_id != null) q.set('talep_id', String(filtre.talep_id));
  const ek = q.toString();
  return useQuery({
    queryKey: SIPARIS_ANAHTAR.liste(filtre),
    queryFn: () =>
      istek<SiparisOzet[]>('GET', `${PREFIX}/satinalma-siparisleri${ek ? `?${ek}` : ''}`),
    enabled: etkin,
  });
}

export function useSiparis(id: number) {
  return useQuery({
    queryKey: SIPARIS_ANAHTAR.detay(id),
    queryFn: () => istek<SiparisDetay>('GET', `${PREFIX}/satinalma-siparisleri/${id}`),
    enabled: Number.isFinite(id) && id > 0,
  });
}

export function useEslesmemisKabuller(etkin = true) {
  return useQuery({
    queryKey: SIPARIS_ANAHTAR.eslesmemis,
    queryFn: () => istek<EslesmemisKabul[]>('GET', `${PREFIX}/teslim-almalar/eslesmemis`),
    enabled: etkin,
  });
}

export function useTedarikciler(etkin = true) {
  return useQuery({
    queryKey: SIPARIS_ANAHTAR.tedarikciler,
    queryFn: async () =>
      (await istekSayfali<TedarikciSecenek>(`${PREFIX}/firmalar?tip=tedarikci&sayfa=1&adet=100`))
        .veri,
    enabled: etkin,
    staleTime: 60_000,
  });
}

function useSiparisGecersizle() {
  const qc = useQueryClient();
  return (id?: number) => {
    void qc.invalidateQueries({ queryKey: ['satinalma-siparisleri'] });
    if (id != null) void qc.invalidateQueries({ queryKey: SIPARIS_ANAHTAR.detay(id) });
    void qc.invalidateQueries({ queryKey: SIPARIS_ANAHTAR.eslesmemis });
    void qc.invalidateQueries({ queryKey: ['stok-bakiyeleri'] });
    void qc.invalidateQueries({ queryKey: ['depolar'] });
    void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
    void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.hareketler });
    void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.stokOzet });
  };
}

export function useSiparisOlustur() {
  const gecersizle = useSiparisGecersizle();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: {
      talep_id: number;
      tedarikci_firma_id: number;
      beklenen_teslim_tarihi?: string | null;
      aciklama?: string;
      kalemler?: { talep_kalemi_id: number; fazla_teslim_toleransi_yuzde?: number }[];
    }) => istek<SiparisDetay>('POST', `${PREFIX}/satinalma-siparisleri`, govde),
    onSuccess: (s) => gecersizle(s.id),
    onError: hata,
  });
}

export function useTeslimAl(siparisId: number) {
  const qc = useQueryClient();
  const gecersizle = useSiparisGecersizle();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: {
      irsaliye_no: string;
      fiili_tarih?: string;
      lokasyon_id?: number;
      aciklama?: string;
      kalemler: { siparis_kalemi_id: number; miktar: number; lot_no?: string }[];
    }) =>
      istek<SiparisDetay>('POST', `${PREFIX}/satinalma-siparisleri/${siparisId}/teslim-al`, govde),
    onSuccess: (s) => {
      qc.setQueryData(SIPARIS_ANAHTAR.detay(siparisId), s);
      gecersizle(siparisId);
    },
    onError: hata,
  });
}

export function useIade(siparisId: number) {
  const qc = useQueryClient();
  const gecersizle = useSiparisGecersizle();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: ({
      teslimId,
      ...govde
    }: {
      teslimId: number;
      irsaliye_no: string;
      aciklama?: string;
      kalemler: { teslim_alma_kalemi_id: number; miktar: number }[];
    }) => istek<SiparisDetay>('POST', `${PREFIX}/teslim-almalar/${teslimId}/iade`, govde),
    onSuccess: (s) => {
      qc.setQueryData(SIPARIS_ANAHTAR.detay(siparisId), s);
      gecersizle(siparisId);
    },
    onError: hata,
  });
}

export function useSiparisAksiyon(siparisId: number) {
  const qc = useQueryClient();
  const gecersizle = useSiparisGecersizle();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: ({ aksiyon, neden }: { aksiyon: 'iptal' | 'kapat'; neden?: string }) =>
      istek<SiparisDetay>(
        'POST',
        `${PREFIX}/satinalma-siparisleri/${siparisId}/${aksiyon}`,
        aksiyon === 'kapat' ? { neden } : undefined,
      ),
    onSuccess: (s) => {
      qc.setQueryData(SIPARIS_ANAHTAR.detay(siparisId), s);
      gecersizle(siparisId);
    },
    onError: hata,
  });
}

/** Malzeme etiketini (100×50 mm, QR + Code 128) indirir. */
export async function etiketIndir(malzemeId: number, kod: string, adet = 1): Promise<void> {
  const { blob } = await istekIndir(`${PREFIX}/malzemeler/${malzemeId}/etiket.pdf?adet=${adet}`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `etiket-${kod}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/** Sipariş formunu (PDF) yeni sekmede açar; tarayıcı engellerse indirir (S27-B, ADR-0046). */
export async function siparisPdfAc(siparisId: number, kod: string): Promise<void> {
  const { blob } = await istekIndir(`${PREFIX}/satinalma-siparisleri/${siparisId}/pdf`);
  const url = URL.createObjectURL(blob);
  const pencere = window.open(url, '_blank', 'noopener');
  if (!pencere) {
    const a = document.createElement('a');
    a.href = url;
    a.download = `${kod}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
