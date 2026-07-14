import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import '@/i18n';

import { IkizHarita } from './IkizHarita';

describe('IkizHarita', () => {
  it('koordinatsız veri setinde boş-durum ipucunu gösterir (harita yine çizilir)', () => {
    render(
      <IkizHarita
        makineler={[{ makine_id: 1, makine_kod: 'CNC-1', makine_ad: 'CNC', durum: 'calisiyor' }]}
        sec={() => {}}
      />,
    );
    expect(
      screen.getByText('Koordinatı girilmiş makine yok — makine detayından enlem/boylam ekleyin.'),
    ).toBeInTheDocument();
  });
});
