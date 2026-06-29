/**
 * i18n kurulumu (i18next) — TR varsayılan, EN opsiyonel. Arayüz metinleri her zaman
 * çeviri anahtarına bağlanır (türkçe-identifier-standardi: hardcode metin yok).
 */

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './en.json';
import tr from './tr.json';

export const DILLER: Record<string, string> = { tr: 'Türkçe', en: 'English' };
const DIL_ANAHTARI = 'fabrikaos.dil';

void i18n.use(initReactI18next).init({
  resources: {
    tr: { translation: tr },
    en: { translation: en },
  },
  lng: localStorage.getItem(DIL_ANAHTARI) ?? 'tr',
  fallbackLng: 'tr',
  interpolation: { escapeValue: false },
});

export function dilDegistir(dil: string): void {
  localStorage.setItem(DIL_ANAHTARI, dil);
  void i18n.changeLanguage(dil);
}

export default i18n;
