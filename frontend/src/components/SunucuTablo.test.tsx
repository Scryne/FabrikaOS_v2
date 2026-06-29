import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ColumnsType } from 'antd/es/table';

import '@/i18n';
import type { SayfaParam } from '@/api/sayfalama';

import { SunucuTablo } from './SunucuTablo';

type Satir = { id: number; kod: string; ad: string };

const VERI: Satir[] = [
  { id: 1, kod: 'MAK-A', ad: 'Pres' },
  { id: 2, kod: 'MAK-B', ad: 'CNC' },
];

const KOLONLAR: ColumnsType<Satir> = [
  { title: 'Kod', dataIndex: 'kod', key: 'kod', sorter: true },
  { title: 'Ad', dataIndex: 'ad', key: 'ad' },
];

function kur(param: SayfaParam = { sayfa: 1, adet: 20 }) {
  const paramDegistir = vi.fn();
  render(
    <SunucuTablo<Satir>
      kolonlar={KOLONLAR}
      veri={VERI}
      meta={{ sayfa: param.sayfa, adet: param.adet, toplam: 40 }}
      param={param}
      paramDegistir={paramDegistir}
      rowKey="id"
      aramaYer="Ara"
    />,
  );
  return { paramDegistir };
}

describe('SunucuTablo', () => {
  it('sıralanabilir kolon başlığına tıklayınca sunucu sıralaması (sayfa 1) bildirir', async () => {
    const u = userEvent.setup();
    const { paramDegistir } = kur();

    await u.click(screen.getByRole('columnheader', { name: /kod/i }));

    expect(paramDegistir).toHaveBeenCalledWith(
      expect.objectContaining({ siralama: 'kod', yon: 'asc', sayfa: 1 }),
    );
  });

  it('aramayı debounce ile bildirir', async () => {
    const u = userEvent.setup();
    const { paramDegistir } = kur();

    await u.type(screen.getByPlaceholderText('Ara'), 'pres');

    await waitFor(
      () => expect(paramDegistir).toHaveBeenCalledWith(expect.objectContaining({ arama: 'pres' })),
      { timeout: 1500 },
    );
  });

  it('sayfa değişimini bildirir', async () => {
    const u = userEvent.setup();
    const { paramDegistir } = kur();

    await u.click(screen.getByTitle('2'));

    expect(paramDegistir).toHaveBeenCalledWith(expect.objectContaining({ sayfa: 2 }));
  });
});
