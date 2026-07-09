/**
 * Tasarım vitrini (yalnız DEV) — "Kontrol Odası (Evrim)" desen sözlüğünün canlı kataloğu.
 * Backend gerektirmez; statik demo veriyle her primitifi ve grafik üreticisini gösterir. Yeni
 * bir ekran kurulurken buradaki kullanım örnekleri referanstır. Rota: ``/onizleme/primitifler``.
 */

import { useState } from 'react';
import { Button, Col, Row, Space } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';

import { AktiviteAkisi } from '@/components/AktiviteAkisi';
import { DurumPim } from '@/components/DurumPim';
import { EGrafik } from '@/components/grafik/EGrafik';
import {
  alanSecenek,
  donutSecenek,
  isiHaritaSecenek,
  paretoSecenek,
  yiginCubukSecenek,
} from '@/components/grafik/grafikSecenek';
import { GorunumGecis, type Gorunum } from '@/components/GorunumGecis';
import { KanbanPano } from '@/components/KanbanPano';
import { KomutPaleti } from '@/components/KomutPaleti';
import { MiniBar } from '@/components/MiniBar';
import { OzetSerit } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { RiskMatrisi } from '@/components/RiskMatrisi';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { UyariKarti } from '@/components/UyariKarti';
import { VeriKart } from '@/components/VeriKart';
import { riskSeviyesi, riskSkoru } from '@/modules/isg/riskMatris';
import { RENKLER } from '@/tema/tema';

const HAT = RENKLER.cyan;
const GUNLER = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];

const SEVIYE_RENK: Record<string, string> = {
  dusuk: RENKLER.basari,
  orta: RENKLER.cyan,
  yuksek: RENKLER.uyari,
  cok_yuksek: RENKLER.hata,
};

type IsDemo = { id: number; durum: string; kod: string; baslik: string };
const IS_DEMO: IsDemo[] = [
  { id: 1, durum: 'acik', kod: 'IE-1042', baslik: 'Rulman değişimi' },
  { id: 2, durum: 'acik', kod: 'IE-1043', baslik: 'Yağ seviyesi kontrolü' },
  { id: 3, durum: 'atandi', kod: 'IE-1039', baslik: 'Konveyör bant hizalama' },
  { id: 4, durum: 'devam_ediyor', kod: 'IE-1036', baslik: 'Pnömatik hat onarımı' },
  { id: 5, durum: 'kapandi', kod: 'IE-1028', baslik: 'Sensör kalibrasyonu' },
];

const KANBAN_KOLON = [
  { anahtar: 'acik', baslik: 'Açık', renk: RENKLER.metinSoluk },
  { anahtar: 'atandi', baslik: 'Atandı', renk: RENKLER.cyan },
  { anahtar: 'devam_ediyor', baslik: 'Devam ediyor', renk: RENKLER.mavi },
  { anahtar: 'kapandi', baslik: 'Kapandı', renk: RENKLER.basari },
];

/** 24 saat × 7 gün sözde üretim yoğunluğu (ısı haritası demo verisi). */
function isiVerisi(): [number, number, number][] {
  const v: [number, number, number][] = [];
  for (let g = 0; g < 7; g += 1) {
    for (let s = 0; s < 24; s += 1) {
      const gunduz = s >= 7 && s <= 19 ? 1 : 0.25;
      v.push([s, g, Math.round((Math.sin(s / 3) + 1.2) * 40 * gunduz + g * 4)]);
    }
  }
  return v;
}

export function PrimitifVitrini() {
  const [gorunum, setGorunum] = useState<Gorunum>('pano');
  const [paletAcik, setPaletAcik] = useState(false);
  const [riskSecili, setRiskSecili] = useState<{ olasilik: number; siddet: number } | null>(null);

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik="Tasarım vitrini"
        alt="Kontrol Odası (Evrim) desen sözlüğü — primitifler, grafikler ve durum dili canlı katalog."
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} />
            <Button icon={<ThunderboltOutlined />} onClick={() => setPaletAcik(true)}>
              Komut paleti (⌘K)
            </Button>
          </Space>
        }
      />

      <OzetSerit
        renk={HAT}
        metrikler={[
          {
            anahtar: 'oee',
            baslik: 'Filo OEE',
            deger: '84',
            birim: '%',
            ikon: <ThunderboltOutlined />,
            seri: [78, 80, 79, 82, 81, 83, 84],
            deltaMetin: '%2.1',
            yon: 'yukari',
            olumlu: true,
          },
          { anahtar: 'uretim', baslik: 'Bugünkü üretim', deger: '12.480', altMetin: 'adet' },
          {
            anahtar: 'isemri',
            baslik: 'Açık iş emri',
            deger: '9',
            seri: [14, 12, 11, 13, 10, 9, 9],
          },
          {
            anahtar: 'kritik',
            baslik: 'Kritik stok',
            deger: '3',
            deltaMetin: '1',
            yon: 'yukari',
            olumlu: false,
          },
        ]}
      />

      <div style={{ height: 20 }} />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <PanelKart baslik="Üretim trendi (7 gün)" renk={HAT}>
            <EGrafik
              secenek={alanSecenek(GUNLER, [
                { ad: 'Gerçekleşen', veri: [980, 1120, 1040, 1210, 1180, 640, 720], renk: HAT },
                {
                  ad: 'Tahmin',
                  veri: [null, null, null, null, 1180, 700, 760],
                  renk: RENKLER.mor,
                  kesikli: true,
                },
              ])}
              yukseklik={240}
            />
          </PanelKart>
        </Col>
        <Col xs={24} lg={8}>
          <PanelKart baslik="Makine durum dağılımı" renk={HAT}>
            <EGrafik
              secenek={donutSecenek([
                { ad: 'Çalışıyor', deger: 4, renk: RENKLER.basari },
                { ad: 'Durdu', deger: 1, renk: RENKLER.metinSoluk },
                { ad: 'Bakımda', deger: 1, renk: RENKLER.uyari },
              ])}
              yukseklik={240}
            />
          </PanelKart>
        </Col>

        <Col xs={24} lg={12}>
          <PanelKart baslik="Stok hareketi (yığın)" renk={RENKLER.basari}>
            <EGrafik
              secenek={yiginCubukSecenek(GUNLER, [
                { ad: 'Giriş', veri: [12, 8, 15, 6, 9, 3, 0], renk: RENKLER.basari },
                { ad: 'Çıkış', veri: [7, 10, 5, 12, 8, 2, 1], renk: RENKLER.uyari },
              ])}
              yukseklik={220}
            />
          </PanelKart>
        </Col>
        <Col xs={24} lg={12}>
          <PanelKart baslik="Hata türü paretosu" renk={RENKLER.mor}>
            <EGrafik
              secenek={paretoSecenek([
                { ad: 'Çapak', deger: 42 },
                { ad: 'Ölçü', deger: 28 },
                { ad: 'Yüzey', deger: 18 },
                { ad: 'Renk', deger: 9 },
                { ad: 'Diğer', deger: 4 },
              ])}
              yukseklik={220}
            />
          </PanelKart>
        </Col>

        <Col xs={24}>
          <PanelKart baslik="Saatlik üretim ısı haritası" renk={HAT}>
            <EGrafik
              secenek={isiHaritaSecenek(
                Array.from({ length: 24 }, (_, i) => String(i).padStart(2, '0')),
                GUNLER,
                isiVerisi(),
                HAT,
              )}
              yukseklik={220}
            />
          </PanelKart>
        </Col>
      </Row>

      <div style={{ height: 20 }} />

      <PanelKart baslik="İş emirleri panosu (KanbanPano + VeriKart)" renk={HAT}>
        <KanbanPano<IsDemo>
          kolonlar={KANBAN_KOLON}
          ogeler={IS_DEMO}
          kolonAnahtar={(o) => o.durum}
          kartAnahtar={(o) => o.id}
          bosMetin="Kayıt yok"
          kartCiz={(o) => (
            <VeriKart
              ustSol={o.kod}
              ustSag={<DurumPim renk={RENKLER.uyari} etiket="Yüksek" />}
              baslik={o.baslik}
              meta={<span>MAK-A1 · 3g</span>}
              onClick={() => undefined}
            />
          )}
        />
      </PanelKart>

      <div style={{ height: 20 }} />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <PanelKart baslik="Uyarılar (UyariKarti)" renk={RENKLER.uyari}>
            <Space direction="vertical" style={{ width: '100%' }} size={12}>
              <UyariKarti
                onem="kritik"
                baslik="3 kalem kritik altında"
                aciklama="Rulman, conta, filtre."
              />
              <UyariKarti onem="uyari" baslik="Sözleşme 15 gün içinde bitiyor" />
              <UyariKarti onem="bilgi" baslik="Yeni duyuru yayınlandı" />
            </Space>
          </PanelKart>
        </Col>
        <Col xs={24} lg={8}>
          <PanelKart baslik="Risk matrisi (5×5)" renk={RENKLER.uyari}>
            <RiskMatrisi
              sayac={(o, s) => (o + s) % 4}
              renk={(o, s) => SEVIYE_RENK[riskSeviyesi(riskSkoru(o, s))] ?? RENKLER.metinSoluk}
              onHucre={(olasilik, siddet) => setRiskSecili({ olasilik, siddet })}
              secili={riskSecili}
            />
          </PanelKart>
        </Col>
        <Col xs={24} lg={8}>
          <PanelKart baslik="Aktivite akışı" renk={HAT}>
            <AktiviteAkisi
              ogeler={[
                { anahtar: '1', renk: RENKLER.basari, baslik: 'IE-1028 kapandı', zaman: '10:24' },
                {
                  anahtar: '2',
                  renk: RENKLER.uyari,
                  baslik: 'Kritik stok: Filtre',
                  aciklama: 'Bakiye kritik eşiğin altında.',
                  zaman: '09:58',
                },
                { anahtar: '3', renk: RENKLER.mavi, baslik: 'IE-1036 başlatıldı', zaman: '09:12' },
              ]}
            />
          </PanelKart>
        </Col>
      </Row>

      <div style={{ height: 20 }} />

      <PanelKart baslik="Satır-içi görselleştirme (MiniBar + DurumPim)" renk={HAT}>
        <Space direction="vertical" size={14} style={{ width: '100%' }}>
          {[
            {
              ad: 'MAK-A1',
              oee: 91,
              durum: 'calisiyor',
              renk: RENKLER.basari,
              etiket: 'Çalışıyor',
            },
            { ad: 'MAK-C1', oee: 64, durum: 'durdu', renk: RENKLER.metinSoluk, etiket: 'Durdu' },
            { ad: 'MAK-E2', oee: 72, durum: 'bakimda', renk: RENKLER.uyari, etiket: 'Bakımda' },
          ].map((m) => (
            <div key={m.ad} style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
              <span className="sayisal" style={{ width: 80, color: 'var(--metin)' }}>
                {m.ad}
              </span>
              <MiniBar
                deger={m.oee}
                renk={m.oee >= 85 ? RENKLER.basari : m.oee >= 60 ? RENKLER.uyari : RENKLER.hata}
              />
              <span className="sayisal" style={{ width: 48, color: 'var(--metin)' }}>
                %{m.oee}
              </span>
              <DurumPim renk={m.renk} etiket={m.etiket} />
            </div>
          ))}
        </Space>
      </PanelKart>

      <KomutPaleti acik={paletAcik} kapat={() => setPaletAcik(false)} />
    </SayfaKapsayici>
  );
}
