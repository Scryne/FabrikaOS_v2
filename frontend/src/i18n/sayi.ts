/**
 * Arayüzdeki miktar/ölçüm sayılarının tek biçimleyicisi: etkin dile göre ondalık ayıracı ve
 * binlik grubu (TR: 1.234,5 · EN: 1,234.5). Tablolar ham ``{v}`` basınca TR ekranda "11.9"
 * çıkıyordu, aynı değer KPI kartında "11,9" (2026-11-13 gezintisi).
 *
 * API Decimal alanlarını metin olarak da döndürebilir ("11.900"); sayıya çevrilebiliyorsa
 * biçimlenir, çevrilemiyorsa olduğu gibi döner. Boş değer "—".
 */

import i18n from 'i18next';

export function sayiMetni(v: number | string | null | undefined, enCokBasamak = 3): string {
  if (v == null || v === '') return '—';
  const n = typeof v === 'string' ? Number(v) : v;
  if (!Number.isFinite(n)) return String(v);
  const yerel = i18n.language === 'en' ? 'en-US' : 'tr-TR';
  return n.toLocaleString(yerel, { maximumFractionDigits: enCokBasamak });
}
