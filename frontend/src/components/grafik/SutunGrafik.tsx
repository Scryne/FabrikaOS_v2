/** Hafif sütun grafiği (bağımsız). Bir sütun vurgulanır. Gerçek grafikler S6'da (ECharts). */

export type SutunVeri = { etiket: string; deger: number };

export function SutunGrafik({
  veri,
  vurguIndeks,
  yukseklik = 200,
}: {
  veri: SutunVeri[];
  vurguIndeks?: number;
  yukseklik?: number;
}) {
  const enBuyuk = Math.max(...veri.map((v) => v.deger), 1);

  return (
    <div
      style={{ display: 'flex', alignItems: 'flex-end', gap: 'min(3%, 16px)', height: yukseklik }}
    >
      {veri.map((v, i) => {
        const vurgulu = i === vurguIndeks;
        return (
          <div
            key={v.etiket}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: 8,
              height: '100%',
            }}
          >
            <div
              title={`${v.etiket}: ${v.deger}`}
              style={{
                width: '64%',
                maxWidth: 34,
                height: `${(v.deger / enBuyuk) * 100}%`,
                minHeight: 4,
                borderRadius: '7px 7px 2px 2px',
                background: vurgulu ? 'var(--mavi)' : 'rgba(255, 255, 255, 0.10)',
                boxShadow: vurgulu ? '0 0 18px rgba(59,110,246,0.45)' : 'none',
                // Yükseklik (layout) yerine transform ile büyüt — performanslı.
                transformOrigin: 'bottom',
                animation: 'sutunGiris 460ms cubic-bezier(0.22, 1, 0.36, 1) both',
              }}
            />
            <span style={{ fontSize: 11, color: 'var(--metin-soluk)' }}>{v.etiket}</span>
          </div>
        );
      })}
    </div>
  );
}
