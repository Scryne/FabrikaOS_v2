/**
 * Gerçek-zaman WebSocket istemcisi — tenant-kapsamlı olay akışına bağlanır (S7).
 *
 * Kimlik query ile taşınır (tarayıcı WS el sıkışmasında başlık gönderemez):
 * ``/api/v1/ws/olaylar?token=<access>&tenant=<slug>``. Bağlantı düşerse otomatik yeniden
 * dener; her denemede güncel access token okunur (``tokenAl``) → rotasyon sonrası geçerli kalır.
 */

const WS_TABANI = (import.meta.env.VITE_API_URL ?? 'http://localhost:8000').replace(/^http/, 'ws');
const YENIDEN_GECIKME = 2000;

export type Olay = { tur: string } & Record<string, unknown>;

export type GercekZamanSecenek = {
  tokenAl: () => string | null;
  tenant: string;
  onOlay: (olay: Olay) => void;
  onDurum?: (bagli: boolean) => void;
};

export type GercekZamanBaglanti = { kapat: () => void };

/** WS bağlantısı kurar (oto-reconnect). ``kapat()`` ile temizlenir. */
export function gercekZamanBaglan(secenek: GercekZamanSecenek): GercekZamanBaglanti {
  let kapatildi = false;
  let ws: WebSocket | null = null;
  let zamanlayici: ReturnType<typeof setTimeout> | null = null;

  const baglan = () => {
    if (kapatildi) return;
    const token = secenek.tokenAl();
    if (!token || !secenek.tenant) {
      zamanlayici = setTimeout(baglan, YENIDEN_GECIKME);
      return;
    }
    const url =
      `${WS_TABANI}/api/v1/ws/olaylar` +
      `?token=${encodeURIComponent(token)}&tenant=${encodeURIComponent(secenek.tenant)}`;
    ws = new WebSocket(url);

    ws.onopen = () => secenek.onDurum?.(true);
    ws.onmessage = (e) => {
      try {
        secenek.onOlay(JSON.parse(e.data as string) as Olay);
      } catch {
        // Bozuk mesaj yok sayılır.
      }
    };
    ws.onerror = () => ws?.close();
    ws.onclose = () => {
      secenek.onDurum?.(false);
      if (!kapatildi) zamanlayici = setTimeout(baglan, YENIDEN_GECIKME);
    };
  };

  baglan();

  return {
    kapat: () => {
      kapatildi = true;
      if (zamanlayici) clearTimeout(zamanlayici);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    },
  };
}
