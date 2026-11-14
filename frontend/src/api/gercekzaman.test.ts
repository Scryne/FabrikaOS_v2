import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { gercekZamanBaglan } from './gercekzaman';

class SahteSoket {
  static ornekler: SahteSoket[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  kapandi = false;
  constructor(public url: string) {
    SahteSoket.ornekler.push(this);
  }
  close() {
    this.kapandi = true;
  }
}

describe('gercekZamanBaglan', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    SahteSoket.ornekler = [];
    vi.stubGlobal('WebSocket', SahteSoket);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  const ac = () => gercekZamanBaglan({ tokenAl: () => 'tkn', tenant: 'alfa', onOlay: () => {} });

  it('hemen kapatılan bağlantı (StrictMode bağla→temizle) soket açmaz', () => {
    ac().kapat();
    const ikinci = ac();
    vi.runOnlyPendingTimers();
    expect(SahteSoket.ornekler).toHaveLength(1); // yalnız ikinci bağlantının soketi
    expect(SahteSoket.ornekler[0]?.url).toContain('tenant=alfa');
    ikinci.kapat();
    expect(SahteSoket.ornekler[0]?.kapandi).toBe(true);
  });
});
