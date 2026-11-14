/**
 * Gerçek-zaman WebSocket istemcisi — tenant-kapsamlı olay akışına bağlanır (S7).
 *
 * Kimlik query ile taşınır (tarayıcı WS el sıkışmasında başlık gönderemez):
 * ``/api/v1/ws/olaylar?token=<access>&tenant=<slug>``. Bağlantı düşerse otomatik yeniden
 * dener; her denemede güncel access token okunur (``tokenAl``) → rotasyon sonrası geçerli kalır.
 */

// Üretim imajı VITE_API_URL'i boş derler (API aynı alan adında): o zaman sayfanın kendi
// kökenine bağlanılır (https → wss). Göreli WS adresini her tarayıcı kabul etmez.
const WS_TABANI = (
  import.meta.env.VITE_API_URL ||
  (import.meta.env.VITE_API_URL === '' ? window.location.origin : 'http://localhost:8000')
).replace(/^http/, 'ws');
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

  // İlk bağlantı bir sonraki makro göreve ertelenir: React StrictMode (geliştirme) efekti
  // bağla → temizle → bağla diye çift çalıştırır; ilk soket CONNECTING iken kapanınca tarayıcı
  // "WebSocket is closed before the connection is established" hatası basıyordu (sızıntı değil,
  // ölçüldü: ikinci soket tek açık kalan). Ertelenince temizlik zamanlayıcıyı iptal eder,
  // gereksiz soket hiç açılmaz. Üretimde fark yalnız bir tik gecikme.
  zamanlayici = setTimeout(baglan, 0);

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
