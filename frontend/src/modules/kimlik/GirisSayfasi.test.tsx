import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { girisYap } from '@/api/kimlik';

import { GirisSayfasi } from './GirisSayfasi';

vi.mock('@/api/kimlik', () => ({ girisYap: vi.fn().mockResolvedValue(undefined) }));

describe('GirisSayfasi', () => {
  beforeEach(() => vi.clearAllMocks());

  it('subdomain yokken firma kodu alanı görünür ve giriş çağrılır', async () => {
    // jsdom host = localhost → subdomain yok → fallback firma kodu alanı.
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <GirisSayfasi />
      </MemoryRouter>,
    );

    const firma = screen.getByLabelText(/firma kodu/i);
    expect(firma).toBeInTheDocument();

    await u.type(firma, 'alfa');
    await u.type(screen.getByLabelText(/e-posta/i), 'admin@alfa.test');
    await u.type(screen.getByLabelText(/^parola/i), 'Parola123!');
    await u.click(screen.getByRole('button', { name: /giriş yap/i }));

    await waitFor(() =>
      expect(girisYap).toHaveBeenCalledWith('alfa', 'admin@alfa.test', 'Parola123!'),
    );
  });
});
