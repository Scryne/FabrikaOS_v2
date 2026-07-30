import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App as AntApp } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { KvkkSayfasi } from './KvkkSayfasi';

// vi.mock fabrikası dosyanın en üstüne hoist edilir; casusları vi.hoisted ile tanımlarız
// ki fabrika içinden erişilebilsinler (aksi hâlde "cannot access before initialization").
const { ihracBaslat, anonimlestir, temizle, ihracIndir } = vi.hoisted(() => ({
  ihracBaslat: vi.fn(),
  anonimlestir: vi.fn(),
  temizle: vi.fn(),
  ihracIndir: vi.fn().mockResolvedValue(undefined),
}));

/** Farklı durumlarda ihraç satırları — ekranın durum makinesi bunlar üstünde sınanır. */
const IHRACLAR = [
  {
    id: 1,
    kod: 'KV-2026-000001',
    kisi_turu: 'kullanici',
    kisi_id: 5,
    durum: 'hazir',
    dosya_adi: 'kv-2026-000001.zip',
    boyut: 1024,
    kayit_sayisi: 42,
    hata: '',
    olusturma_tarihi: '2026-07-30T10:00:00Z',
  },
  {
    id: 2,
    kod: 'KV-2026-000002',
    kisi_turu: 'personel',
    kisi_id: 9,
    durum: 'kuyrukta',
    dosya_adi: '',
    boyut: 0,
    kayit_sayisi: 0,
    hata: '',
    olusturma_tarihi: '2026-07-30T10:05:00Z',
  },
  {
    id: 3,
    kod: 'KV-2026-000003',
    kisi_turu: 'kullanici',
    kisi_id: 7,
    durum: 'suresi_doldu',
    dosya_adi: '',
    boyut: 0,
    kayit_sayisi: 12,
    hata: '',
    olusturma_tarihi: '2026-07-20T10:00:00Z',
  },
];

vi.mock('./hooks', () => ({
  useKvkkIhraclar: () => ({
    data: { veri: IHRACLAR, meta: { sayfa: 1, adet: 20, toplam: 3 } },
    isPending: false,
    isError: false,
  }),
  useIhracBaslat: () => ({ mutate: ihracBaslat, isPending: false }),
  useAnonimlestir: () => ({ mutate: anonimlestir, isPending: false }),
  useIhraclariTemizle: () => ({ mutate: temizle, isPending: false }),
  useConsentKayitlari: () => ({
    data: [
      {
        id: 1,
        tur: 'acik_riza',
        metin_surumu: 'v1',
        kabul: true,
        olusturma_tarihi: '2026-07-30T10:00:00Z',
      },
    ],
    isLoading: false,
  }),
  useConsentEkle: () => ({ mutate: vi.fn(), isPending: false }),
  ihracIndir,
}));

function ekranaBas() {
  render(
    <AntApp>
      <MemoryRouter>
        <KvkkSayfasi />
      </MemoryRouter>
    </AntApp>,
  );
}

function satir(kod: string) {
  return screen.getByText(kod).closest('tr') as HTMLElement;
}

describe('KvkkSayfasi', () => {
  beforeEach(() => vi.clearAllMocks());

  it('ihraç durumlarını ayrı ayrı etiketler', () => {
    ekranaBas();
    expect(within(satir('KV-2026-000001')).getByText(/hazır/i)).toBeInTheDocument();
    expect(within(satir('KV-2026-000002')).getByText(/kuyrukta/i)).toBeInTheDocument();
    expect(within(satir('KV-2026-000003')).getByText(/süresi doldu/i)).toBeInTheDocument();
  });

  it('yalnız hazır ihraç indirilebilir; kuyruktaki ve süresi dolan PASİF', () => {
    ekranaBas();
    const dugme = (kod: string) =>
      within(satir(kod)).getByRole('button', { name: /ndir/ }) as HTMLButtonElement;

    expect(dugme('KV-2026-000001')).toBeEnabled();
    expect(dugme('KV-2026-000002')).toBeDisabled();
    // Süresi dolan artefakt sunucuda silindi: indirme denemesi 410 verirdi, düğme kapalı.
    expect(dugme('KV-2026-000003')).toBeDisabled();
  });

  it('hazır ihracı indirir', async () => {
    const u = userEvent.setup();
    ekranaBas();
    await u.click(within(satir('KV-2026-000001')).getByRole('button', { name: /ndir/ }));
    await waitFor(() => expect(ihracIndir).toHaveBeenCalledWith(IHRACLAR[0]));
  });

  it('saklama süresi kullanıcıya açıkça bildirilir', () => {
    ekranaBas();
    expect(screen.getByText(/7 gün sonra otomatik silinir/i)).toBeInTheDocument();
  });

  it('süresi dolanları temizle aksiyonu çağrılır', async () => {
    const u = userEvent.setup();
    ekranaBas();
    await u.click(screen.getByRole('button', { name: /temizle/i }));
    await waitFor(() => expect(temizle).toHaveBeenCalled());
  });

  it('anonimleştirme onay metni yazılmadan çalıştırılamaz', async () => {
    const u = userEvent.setup();
    ekranaBas();

    const dugme = screen.getByRole('button', { name: /^Anonimleştir$/ });
    expect(dugme).toBeDisabled();

    // Yanlış metin de açmaz (birebir "ANONIM" şart).
    const onayKutusu = screen.getByPlaceholderText('ANONIM');
    await u.type(onayKutusu, 'anonim');
    expect(dugme).toBeDisabled();

    await u.clear(onayKutusu);
    await u.type(onayKutusu, 'ANONIM');
    await waitFor(() => expect(dugme).toBeEnabled());
  });

  it('ihraç formu kişi no olmadan gönderilmez', async () => {
    const u = userEvent.setup();
    ekranaBas();
    await u.click(screen.getByRole('button', { name: /hracı başlat/ }));
    await waitFor(() => expect(screen.getByText(/kişi numarası gerekli/i)).toBeInTheDocument());
    expect(ihracBaslat).not.toHaveBeenCalled();
  });
});
