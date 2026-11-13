import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import '@/i18n';

import { SayfaBulunamadi } from './SayfaBulunamadi';

describe('SayfaBulunamadi', () => {
  it('bilinmeyen adreste 404 gösterir, adresi yazar ve panoya/ana sayfaya çıkış verir', async () => {
    render(
      <MemoryRouter initialEntries={['/makinelr']}>
        <Routes>
          <Route path="/pano" element={<p>pano</p>} />
          <Route path="*" element={<SayfaBulunamadi />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByRole('heading', { name: 'Bu sayfa bulunamadı' })).toBeInTheDocument();
    expect(screen.getByText('/makinelr')).toBeInTheDocument();
    expect(screen.queryByText('pano')).not.toBeInTheDocument();
    expect(document.title).toBe('Sayfa bulunamadı · FabrikaOS');

    await userEvent.setup().click(screen.getByRole('button', { name: 'Panoya dön' }));
    expect(screen.getByText('pano')).toBeInTheDocument();
  });
});
