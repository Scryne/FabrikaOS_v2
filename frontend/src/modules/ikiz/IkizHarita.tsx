/**
 * Coğrafi site haritası (S-VB) — koordinatı olan makineler OSM karo katmanı üzerinde
 * durum LED renginde işaretlenir (ikiz LED dili birebir). İşaretçi tıklama detay
 * panelini besler (şema sekmesiyle aynı seçim akışı). Koordinatsız makineler yalnız
 * SVG şema sekmesinde görünür.
 *
 * Karo katmanı dev'de public OSM'dir; prod'da tenant gizliliği için self-host/ücretli
 * karo kararı ADR-0021'de not edilmiştir.
 */

import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet';
import { LatLngBounds } from 'leaflet';
import { Typography } from 'antd';

import 'leaflet/dist/leaflet.css';

import { durumRengi, oeeEtiket } from './sunum';

export type HaritaMakinesi = {
  makine_id: number;
  makine_kod: string;
  makine_ad: string;
  durum: string;
  enlem?: number | null;
  boylam?: number | null;
  oee?: number | null;
  toplam_adet?: number;
};

/** Türkiye merkezi — hiç koordinat yokken sakin varsayılan görünüm. */
const VARSAYILAN_MERKEZ: [number, number] = [39.0, 35.0];

export function IkizHarita({
  makineler,
  sec,
}: {
  makineler: HaritaMakinesi[];
  sec: (makineId: number) => void;
}) {
  const { t } = useTranslation();
  const koordinatli = useMemo(
    () => makineler.filter((m) => m.enlem != null && m.boylam != null),
    [makineler],
  );

  const sinirlar = useMemo(() => {
    if (koordinatli.length === 0) return null;
    const b = new LatLngBounds(
      koordinatli.map((m) => [m.enlem as number, m.boylam as number] as [number, number]),
    );
    return b.pad(0.35);
  }, [koordinatli]);

  return (
    <div style={{ borderRadius: 8, overflow: 'hidden' }}>
      <MapContainer
        key={koordinatli.length > 0 ? 'dolu' : 'bos'}
        style={{ height: 520, width: '100%', background: 'var(--zemin)' }}
        {...(sinirlar ? { bounds: sinirlar } : { center: VARSAYILAN_MERKEZ, zoom: 6 })}
        scrollWheelZoom
        attributionControl
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {koordinatli.map((m) => (
          <CircleMarker
            key={m.makine_id}
            center={[m.enlem as number, m.boylam as number]}
            radius={10}
            pathOptions={{
              color: durumRengi(m.durum),
              fillColor: durumRengi(m.durum),
              fillOpacity: 0.55,
              weight: 2,
            }}
            eventHandlers={{ click: () => sec(m.makine_id) }}
          >
            <Popup>
              <div style={{ minWidth: 160 }}>
                <div style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                  {m.makine_kod}
                </div>
                <div>{m.makine_ad}</div>
                <div style={{ marginTop: 4, fontSize: 12 }}>
                  {t(`uretim.durum_${m.durum}`, { defaultValue: m.durum })}
                  {m.oee != null && <> · OEE {oeeEtiket(m.oee)}</>}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      {koordinatli.length === 0 && (
        <Typography.Paragraph type="secondary" style={{ fontSize: 12.5, margin: '10px 4px 2px' }}>
          {t('ikiz.harita_bos')}
        </Typography.Paragraph>
      )}
    </div>
  );
}
