import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Her testten sonra DOM'u temizle (test izolasyonu).
afterEach(() => {
  cleanup();
});

// jsdom'da olmayan, Ant Design'ın beklediği tarayıcı API'leri için polyfill.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (sorgu: string) => ({
    matches: false,
    media: sorgu,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
});

class SahteResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = SahteResizeObserver as unknown as typeof ResizeObserver;
