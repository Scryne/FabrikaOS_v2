/**
 * Etiketli oran çubuğu — OEE bileşenleri (kullanılabilirlik/performans/kalite) gibi 0–100
 * değerleri ince yatay bar + monospace yüzde ile gösterir. Saf sunum; veri ekrandan gelir.
 */

export function OranSatiri({
  etiket,
  yuzde,
  renk = 'var(--mavi)',
}: {
  etiket: string;
  yuzde: number;
  renk?: string;
}) {
  const oran = Math.max(0, Math.min(100, yuzde));
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>{etiket}</span>
        <span className="sayisal" style={{ color: 'var(--metin)', fontWeight: 600 }}>
          %{Math.round(oran)}
        </span>
      </div>
      <div
        style={{
          height: 6,
          borderRadius: 4,
          background: 'rgba(255,255,255,0.07)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            width: '100%',
            height: '100%',
            borderRadius: 4,
            background: renk,
            // Layout yerine transform ile büyüt (DESIGN.md: layout animasyonu değil).
            transform: `scaleX(${oran / 100})`,
            transformOrigin: 'left',
            transition: 'transform 480ms cubic-bezier(0.22, 1, 0.36, 1)',
          }}
        />
      </div>
    </div>
  );
}
