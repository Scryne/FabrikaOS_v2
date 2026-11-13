import { afterEach, describe, expect, it } from 'vitest';

import i18n from '@/i18n';

import { sayiMetni } from './sayi';

describe('sayiMetni', () => {
  afterEach(async () => {
    await i18n.changeLanguage('tr');
  });

  it('TR: virgül ondalık, nokta binlik', () => {
    expect(sayiMetni(11.9)).toBe('11,9');
    expect(sayiMetni(1234.5)).toBe('1.234,5');
  });

  it('API Decimal metnini de biçimler, boşa tire', () => {
    expect(sayiMetni('11.900')).toBe('11,9');
    expect(sayiMetni(null)).toBe('—');
    expect(sayiMetni('')).toBe('—');
  });

  it('basamak sınırı', () => {
    expect(sayiMetni(48.04, 1)).toBe('48');
    expect(sayiMetni(4.7654)).toBe('4,765');
  });

  it('EN: nokta ondalık', async () => {
    await i18n.changeLanguage('en');
    expect(sayiMetni(1234.5)).toBe('1,234.5');
  });
});
