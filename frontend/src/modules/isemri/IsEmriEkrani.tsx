/**
 * İş emirleri çalışma alanı — KPI şeridi + Liste / Pano (kanban) / Analiz görünüm geçişi +
 * oluştur + detay çekmecesi. "İş emri oluştur" yalnız ``isemri:yaz`` izniyle görünür
 * (ekran ``isemri:oku`` ile korunur). KPI/analiz tek çekimden (useIsEmriPano) beslenir.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  CheckCircleOutlined,
  FileDoneOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { Button, Card, Col, Row, Space } from 'antd';

import { EGrafik } from '@/components/grafik/EGrafik';
import { donutSecenek } from '@/components/grafik/grafikSecenek';
import { GorunumGecis, type Gorunum } from '@/components/GorunumGecis';
import { OzetSerit, type OzetMetrik } from '@/components/OzetSerit';
import { PanelKart } from '@/components/PanelKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import { DURUMLAR, ONCELIKLER } from './durum';
import { useIsEmriPano } from './hooks';
import { IsEmriDetay } from './IsEmriDetay';
import { IsEmriFormu } from './IsEmriFormu';
import { IsEmriKanban } from './IsEmriKanban';
import { IsEmriListesi } from './IsEmriListesi';

const HAT = BOLUM_RENGI['menu.bolum_uretim'];

const DURUM_RENK: Record<string, string> = {
  acik: RENKLER.metinSoluk,
  atandi: RENKLER.cyan,
  devam_ediyor: RENKLER.mavi,
  kapandi: RENKLER.basari,
  iptal: '#4b4b52',
};
const ONCELIK_RENK: Record<string, string> = {
  dusuk: RENKLER.metinSoluk,
  orta: RENKLER.mavi,
  yuksek: RENKLER.uyari,
  kritik: RENKLER.hata,
};

export function IsEmriEkrani() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isemri:yaz'));
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [seciliId, setSeciliId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);
  const { data: pano } = useIsEmriPano();

  const sayac = useMemo(() => {
    const s = new Map<string, number>();
    for (const e of pano ?? []) s.set(e.durum, (s.get(e.durum) ?? 0) + 1);
    return s;
  }, [pano]);
  const say = (d: string) => sayac.get(d) ?? 0;

  const metrikler: OzetMetrik[] = pano
    ? [
        {
          anahtar: 'acik',
          baslik: t('isemri.kpi_acik'),
          deger: String(say('acik')),
          ikon: <FileDoneOutlined />,
        },
        {
          anahtar: 'aktif',
          baslik: t('isemri.kpi_aktif'),
          deger: String(say('atandi') + say('devam_ediyor')),
          ikon: <PlayCircleOutlined />,
        },
        {
          anahtar: 'kapandi',
          baslik: t('isemri.kpi_kapandi'),
          deger: String(say('kapandi')),
          ikon: <CheckCircleOutlined />,
        },
        {
          anahtar: 'toplam',
          baslik: t('isemri.kpi_toplam'),
          deger: String((pano ?? []).length),
          ikon: <SyncOutlined />,
        },
      ]
    : [];

  const durumDonut = DURUMLAR.filter((d) => say(d) > 0).map((d) => ({
    ad: t(`isemri.durum_${d}`),
    deger: say(d),
    renk: DURUM_RENK[d] ?? RENKLER.metinSoluk,
  }));
  const oncelikSayac = useMemo(() => {
    const s = new Map<string, number>();
    for (const e of pano ?? []) s.set(e.oncelik, (s.get(e.oncelik) ?? 0) + 1);
    return s;
  }, [pano]);
  const oncelikDonut = ONCELIKLER.filter((o) => (oncelikSayac.get(o) ?? 0) > 0).map((o) => ({
    ad: t(`isemri.oncelik_${o}`),
    deger: oncelikSayac.get(o) ?? 0,
    renk: ONCELIK_RENK[o] ?? RENKLER.metinSoluk,
  }));

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.is_emirleri')}
        alt={t('isemri.alt')}
        sag={
          <Space wrap>
            <GorunumGecis deger={gorunum} degisti={setGorunum} />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('isemri.is_emri_olustur')}
              </Button>
            )}
          </Space>
        }
      />

      <OzetSerit renk={HAT} metrikler={metrikler} yukleniyor={!pano} />

      <div style={{ height: 20 }} />

      {gorunum === 'liste' && (
        <Card styles={{ body: { padding: 18 } }}>
          <IsEmriListesi ac={setSeciliId} />
        </Card>
      )}
      {gorunum === 'pano' && <IsEmriKanban ac={setSeciliId} />}
      {gorunum === 'analiz' && (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <PanelKart baslik={t('isemri.analiz_durum')} renk={HAT}>
              <EGrafik secenek={donutSecenek(durumDonut)} yukseklik={300} />
            </PanelKart>
          </Col>
          <Col xs={24} lg={12}>
            <PanelKart baslik={t('isemri.analiz_oncelik')} renk={HAT}>
              <EGrafik secenek={donutSecenek(oncelikDonut)} yukseklik={300} />
            </PanelKart>
          </Col>
        </Row>
      )}

      <IsEmriDetay id={seciliId} kapat={() => setSeciliId(null)} />
      <IsEmriFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </SayfaKapsayici>
  );
}
