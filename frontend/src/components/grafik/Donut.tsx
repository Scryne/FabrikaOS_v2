/** Hafif donut grafiği (conic-gradient, bağımsız). Gerçek/etkileşimli grafikler S6'da (ECharts). */

export type DonutSegment = { etiket: string; deger: number; renk: string };

export function Donut({
  segmentler,
  merkezUst,
  merkezAlt,
  boyut = 168,
}: {
  segmentler: DonutSegment[];
  merkezUst: string;
  merkezAlt: string;
  boyut?: number;
}) {
  const toplam = segmentler.reduce((a, s) => a + s.deger, 0) || 1;
  let imlec = 0;
  const duraklar = segmentler
    .map((s) => {
      const bas = (imlec / toplam) * 100;
      imlec += s.deger;
      const son = (imlec / toplam) * 100;
      return `${s.renk} ${bas}% ${son}%`;
    })
    .join(', ');
  const maske = 'radial-gradient(transparent 60%, #000 61%)';

  return (
    <div style={{ display: 'flex', gap: 24, alignItems: 'center', flexWrap: 'wrap' }}>
      <div style={{ position: 'relative', width: boyut, height: boyut, flexShrink: 0 }}>
        <div
          style={{
            width: '100%',
            height: '100%',
            borderRadius: '50%',
            background: `conic-gradient(${duraklar})`,
            mask: maske,
            WebkitMask: maske,
          }}
        />
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span
            className="sayisal"
            style={{ fontSize: 26, fontWeight: 700, color: 'var(--metin)' }}
          >
            {merkezUst}
          </span>
          <span style={{ fontSize: 12, color: 'var(--metin-soluk)' }}>{merkezAlt}</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, flex: 1, minWidth: 140 }}>
        {segmentler.map((s) => (
          <div
            key={s.etiket}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}
          >
            <span
              style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--metin-soluk)' }}
            >
              <span
                style={{ width: 9, height: 9, borderRadius: 3, background: s.renk, flexShrink: 0 }}
              />
              {s.etiket}
            </span>
            <span className="sayisal" style={{ fontWeight: 600, color: 'var(--metin)' }}>
              %{Math.round(s.deger)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
