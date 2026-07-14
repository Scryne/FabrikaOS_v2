/**
 * Bakım takvimi (S-VB) — aktif bakım planlarının sonraki bakım tarihleri + (ik:oku varsa)
 * onaylı izinler tek aylık takvimde, tür pimi renkli. FE-only: mevcut uçlardan beslenir;
 * İSG eğitim + kalibrasyon beslemeleri S26'da bağlanır.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';
import { Badge, Calendar } from 'antd';
import type { Dayjs } from 'dayjs';

import { istek, PREFIX } from '@/api/client';
import type { IzinTalebi } from '@/modules/ik/hooks';
import { useAuthStore } from '@/store/authStore';

import type { BakimPlani } from './hooks';

type TakvimGirdisi = { tur: 'bakim' | 'izin'; etiket: string };

/** Yerel gün anahtarı (YYYY-MM-DD) — toISOString kullanılmaz (UTC kayması gün kaydırırdı). */
function gunAnahtari(d: Date): string {
  const ay = String(d.getMonth() + 1).padStart(2, '0');
  const gun = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${ay}-${gun}`;
}

/** Gün anahtarı (YYYY-MM-DD) → girdiler. İzinler başlangıç–bitiş aralığına yayılır. */
// eslint-disable-next-line react-refresh/only-export-components
export function takvimGirdileri(
  planlar: BakimPlani[],
  izinler: IzinTalebi[],
): Map<string, TakvimGirdisi[]> {
  const harita = new Map<string, TakvimGirdisi[]>();
  const ekle = (gun: string, girdi: TakvimGirdisi) => {
    const mevcut = harita.get(gun);
    if (mevcut) mevcut.push(girdi);
    else harita.set(gun, [girdi]);
  };
  for (const p of planlar) {
    if (!p.aktif || !p.sonraki_bakim_tarihi) continue;
    ekle(p.sonraki_bakim_tarihi.slice(0, 10), { tur: 'bakim', etiket: p.ad });
  }
  for (const izin of izinler) {
    if (izin.durum !== 'onaylandi') continue;
    // Aralık gün gün açılır (izinler kısa; sınır olarak 62 günde kes — patolojik veri koruması).
    const baslangic = new Date(`${izin.baslangic_tarihi.slice(0, 10)}T00:00:00`);
    const bitis = new Date(`${izin.bitis_tarihi.slice(0, 10)}T00:00:00`);
    for (
      let gun = new Date(baslangic), sayac = 0;
      gun <= bitis && sayac < 62;
      gun.setDate(gun.getDate() + 1), sayac++
    ) {
      ekle(gunAnahtari(gun), { tur: 'izin', etiket: izin.kod });
    }
  }
  return harita;
}

export function BakimTakvimi({ planlar }: { planlar: BakimPlani[] }) {
  const { t } = useTranslation();
  const ikOku = useAuthStore((s) => s.izinVar('ik:oku'));

  // Onaylı izinler (yalnız ik:oku olan kullanıcıda; yoksa takvim salt bakım gösterir).
  const { data: izinler } = useQuery({
    queryKey: ['izin-talepleri', 'takvim'],
    queryFn: () =>
      istek<IzinTalebi[]>('GET', `${PREFIX}/izin-talepleri?sayfa=1&adet=100&durum=onaylandi`),
    enabled: ikOku,
  });

  const girdiler = useMemo(() => takvimGirdileri(planlar, izinler ?? []), [planlar, izinler]);

  const hucre = (tarih: Dayjs) => {
    const gunun = girdiler.get(tarih.format('YYYY-MM-DD')) ?? [];
    if (gunun.length === 0) return null;
    return (
      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {gunun.slice(0, 3).map((g, i) => (
          <li key={i} style={{ fontSize: 11.5, lineHeight: 1.5, whiteSpace: 'nowrap' }}>
            <Badge
              color={g.tur === 'bakim' ? 'var(--hat-uretim)' : 'var(--hat-isg-ik)'}
              text={
                <span style={{ fontSize: 11.5, color: 'var(--metin-soluk)' }}>
                  {g.tur === 'bakim' ? g.etiket : `${t('bakim.takvim_izin')} ${g.etiket}`}
                </span>
              }
            />
          </li>
        ))}
        {gunun.length > 3 && (
          <li style={{ fontSize: 11, color: 'var(--metin-soluk)' }}>+{gunun.length - 3}</li>
        )}
      </ul>
    );
  };

  return <Calendar cellRender={(tarih, info) => (info.type === 'date' ? hucre(tarih) : null)} />;
}
