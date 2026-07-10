import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import '@/i18n';

import { TehlikeOnayModal } from './TehlikeOnayModal';

function ac(onayla = vi.fn(), kapat = vi.fn()) {
  render(
    <TehlikeOnayModal
      acik
      baslik="Tenant'ı sil"
      aciklama="Geri alınamaz"
      slug="alfa"
      onayla={onayla}
      kapat={kapat}
    />,
  );
  return { onayla, kapat };
}

describe('TehlikeOnayModal', () => {
  it('slug birebir yazılmadan onay butonu devre dışıdır', () => {
    ac();
    const onayButonu = screen.getByRole('button', { name: "Tenant'ı sil" });
    expect(onayButonu).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText('alfa'), { target: { value: 'alf' } });
    expect(onayButonu).toBeDisabled();
  });

  it('slug doğru yazılınca onay etkinleşir ve tıklamada onayla çağrılır', () => {
    const { onayla } = ac();
    fireEvent.change(screen.getByPlaceholderText('alfa'), { target: { value: 'alfa' } });

    const onayButonu = screen.getByRole('button', { name: "Tenant'ı sil" });
    expect(onayButonu).toBeEnabled();
    fireEvent.click(onayButonu);
    expect(onayla).toHaveBeenCalledTimes(1);
  });
});
