/**
 * Marka kilidi: gösterge/dial motifi (izleme/kontrol odası kimliği) + "FabrikaOS" sözcük markası.
 */

export function LogoIsareti({ boyut = 28 }: { boyut?: number }) {
  return (
    <svg width={boyut} height={boyut} viewBox="0 0 32 32" fill="none" aria-hidden="true" role="img">
      <rect
        x="2"
        y="2"
        width="28"
        height="28"
        rx="7"
        stroke="var(--kenarlik-parlak)"
        strokeWidth="1.5"
      />
      {/* gösterge yayı (cyan) */}
      <path
        d="M9 21 A 9 9 0 1 1 23 21"
        stroke="var(--cyan)"
        strokeWidth="2"
        strokeLinecap="round"
      />
      {/* ibre (mavi) */}
      <path d="M16 16 L 21.5 11.5" stroke="var(--mavi)" strokeWidth="2" strokeLinecap="round" />
      <circle cx="16" cy="16" r="1.7" fill="var(--mavi)" />
    </svg>
  );
}

export function Marka({ boyut = 28 }: { boyut?: number }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <LogoIsareti boyut={boyut} />
      <span
        style={{
          fontWeight: 700,
          letterSpacing: '-0.02em',
          fontSize: Math.round(boyut * 0.6),
          color: 'var(--metin)',
        }}
      >
        Fabrika<span style={{ color: 'var(--mavi)' }}>OS</span>
      </span>
    </span>
  );
}
