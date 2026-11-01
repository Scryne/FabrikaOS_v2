import { describe, expect, it } from 'vitest';

import { bosSutunlariAt, csvUret, dosyaAdi, kolonlardanSutunlar } from './disaAktar';

type K = { kod: string; ad: string; miktar: number; aktif: boolean; not: string | null };

describe('disaAktar', () => {
  const kayitlar: K[] = [
    { kod: 'MLZ-1', ad: 'Sac; 3 mm "DKP"', miktar: 12.5, aktif: true, not: null },
    { kod: 'MLZ-2', ad: '=HYPERLINK("x")', miktar: -4, aktif: false, not: '+90 532' },
  ];

  it('Türk Excel biçiminde CSV: BOM, ; ayraç, ondalık virgül, kaçış, formül etkisizleştirme', () => {
    const csv = csvUret(kayitlar, [
      { baslik: 'Kod', alan: 'kod' },
      { baslik: 'Ad', alan: 'ad' },
      { baslik: 'Miktar', alan: 'miktar' },
      { baslik: 'Aktif', alan: 'aktif' },
      { baslik: 'Not', alan: 'not' },
    ]);
    expect(csv.startsWith('﻿Kod;Ad;Miktar;Aktif;Not\r\n')).toBe(true);
    const [, s1, s2] = csv.split('\r\n');
    expect(s1).toBe('MLZ-1;"Sac; 3 mm ""DKP""";12,5;Evet;');
    // Sayı olan "-4" formül değildir; "=" ve "+" ile başlayan metin tek tırnakla etkisiz.
    expect(s2).toBe(`MLZ-2;"'=HYPERLINK(""x"")";-4;Hayır;'+90 532`);
  });

  it('tablo sütunlarından türetir: işlem sütunu atlanır, çeviri uygulanır', () => {
    const sutunlar = kolonlardanSutunlar<K>(
      [
        { title: 'Kod', dataIndex: 'kod' },
        { title: '', dataIndex: 'eylem' },
        { title: 'Aktif', dataIndex: 'aktif' },
        { title: 'Ad', key: 'ad' }, // dataIndex yok → key alan sayılır
        { title: 'İşlem' }, // ne dataIndex ne key → atlanır
      ],
      { aktif: (v) => (v ? 'açık' : 'kapalı') },
    );
    expect(sutunlar.map((s) => s.baslik)).toEqual(['Kod', 'Aktif', 'Ad']);
    expect(csvUret([kayitlar[1]!], sutunlar).split('\r\n')[1]).toBe(
      `MLZ-2;kapalı;"'=HYPERLINK(""x"")"`,
    );
  });

  it('dosya adı güvenli ve zaman damgalı', () => {
    expect(dosyaAdi('İş emirleri/2026', 'xlsx', new Date(2026, 10, 1, 9, 5))).toBe(
      'İş-emirleri-2026-20261101-0905.xlsx',
    );
    expect(dosyaAdi('///', 'csv', new Date(2026, 0, 2, 3, 4))).toBe('liste-20260102-0304.csv');
  });

  it('boş sütunu atar, kod sütununu adlandırır, kimlik alanını ekler', () => {
    const s = bosSutunlariAt(kayitlar, [
      { baslik: 'Ad', alan: 'kod' }, // tabloda kod+ad tek "Ad" hücresinde
      { baslik: 'Seviye', alan: 'seviye' }, // hiçbir kayıtta yok
    ]);
    // Kimlik alanı "ad" başa eklenir, kod'a bağlı sütun "Kod" olur, boş sütun düşer.
    expect(s.map((x) => [x.baslik, x.alan])).toEqual([
      ['Ad', 'ad'],
      ['Kod', 'kod'],
    ]);
  });
});
