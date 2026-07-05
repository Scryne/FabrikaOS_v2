/** Kullanıcı yönetimi veri hook'ları (TanStack Query) — kullanıcı listesi + rol kataloğu. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Kullanici = components['schemas']['KullaniciCevapDTO'];
export type KullaniciOlustur = components['schemas']['KullaniciOlusturDTO'];
export type Rol = components['schemas']['RolCevapDTO'];

export const KULLANICI_ANAHTAR = {
  kullanicilar: ['kullanicilar'] as const,
  roller: ['roller'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useKullanicilar(param: SayfaParam) {
  return useSayfaliSorgu<Kullanici>(KULLANICI_ANAHTAR.kullanicilar, '/kullanicilar', param);
}

/** Rol kataloğu (``rol:oku``) — kullanıcı oluştururken rol seçimi için. */
export function useRoller(etkin = true) {
  return useQuery({
    queryKey: KULLANICI_ANAHTAR.roller,
    queryFn: () => istek<Rol[]>('GET', `${PREFIX}/roller`),
    enabled: etkin,
  });
}

export function useKullaniciOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: KullaniciOlustur) =>
      istek<Kullanici>('POST', `${PREFIX}/kullanicilar`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KULLANICI_ANAHTAR.kullanicilar });
      message.success(t('kullanici.olusturuldu'));
    },
    onError: hataGoster,
  });
}
