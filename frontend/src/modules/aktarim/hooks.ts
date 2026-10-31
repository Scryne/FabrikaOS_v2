/**
 * S21 veri içe aktarma hook'ları (ADR-0042): tür listesi, şablon indirme, önizleme, uygulama.
 * Uygulama hepsi-ya-hiçtir; başarılı uygulama ilgili modülün liste sorgularını tazeler.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { istek, istekIndir, PREFIX } from '@/api/client';

export type AktarimAlan = { ad: string; zorunlu: boolean; aciklama: string; ornek: string };

export interface AktarimTur {
  kod: string;
  baslik: string;
  aciklama: string;
  anahtar: string[];
  yetkili: boolean;
  alanlar: AktarimAlan[];
}

export type SatirIslem = 'yeni' | 'guncelle' | 'ayni' | 'hata';

export interface SatirSonucu {
  satir: number;
  anahtar: string;
  islem: SatirIslem;
  hatalar: { alan: string; mesaj: string }[];
  degisen: string[];
}

export interface Onizleme {
  tur: string;
  toplam: number;
  yeni: number;
  guncelle: number;
  ayni: number;
  hatali: number;
  eksik_kolonlar: string[];
  bilinmeyen_kolonlar: string[];
  satirlar: SatirSonucu[];
}

const TABAN = `${PREFIX}/ice-aktarma`;

/** Uygulamadan sonra tazelenecek liste sorgularının kökleri (tür → sorgu anahtarı öneki). */
const TAZELENECEK: Record<string, string[]> = {
  firma: ['firmalar', 'firma'],
  makine: ['makineler', 'makine'],
  malzeme: ['malzemeler', 'malzeme', 'stok-kritik'],
  personel: ['personeller', 'personel'],
  acilis_stogu: ['malzemeler', 'malzeme', 'stok-hareketleri', 'stok-kritik', 'stok-bakiyeleri'],
};

export function useAktarimTurleri() {
  return useQuery({
    queryKey: ['ice-aktarma', 'turler'],
    queryFn: () => istek<AktarimTur[]>('GET', `${TABAN}/turler`),
  });
}

function formVerisi(dosya: File): FormData {
  const fd = new FormData();
  fd.append('dosya', dosya);
  return fd;
}

export function useOnizle() {
  return useMutation({
    mutationFn: ({ tur, dosya }: { tur: string; dosya: File }) =>
      istek<Onizleme>('POST', `${TABAN}/${tur}/onizle`, formVerisi(dosya)),
  });
}

export function useUygula() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ tur, dosya }: { tur: string; dosya: File }) =>
      istek<Onizleme>('POST', `${TABAN}/${tur}/uygula`, formVerisi(dosya)),
    onSuccess: (_v, { tur }) => {
      for (const kok of TAZELENECEK[tur] ?? []) {
        void qc.invalidateQueries({ queryKey: [kok] });
      }
    },
  });
}

export async function sablonIndir(tur: string): Promise<void> {
  const { blob } = await istekIndir(`${TABAN}/${tur}/sablon`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `fabrikaos-${tur}-sablon.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
