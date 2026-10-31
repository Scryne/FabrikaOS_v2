/**
 * Satınalma siparişleri (S25-B): KPI şeridi (açık, kısmi, gecikmiş, eşleşmemiş hızlı kabul) +
 * durum süzgeci + teslim ilerlemesi. Sipariş onaylı talepten açılır (talep çekmecesinde);
 * eşleşmemiş hızlı kabuller ayrı kartta birikir (ADR-0024 §4b), resmî teslimde kendiliğinden düşer.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import {
  ClockCircleOutlined,
  InboxOutlined,
  ShoppingCartOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { Card, Progress, Segmented, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { BosDurum } from '@/components/BosDurum';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';
import { RENKLER } from '@/tema/tema';

import {
  type EslesmemisKabul,
  gecikmis,
  type SiparisDurum,
  type SiparisOzet,
  SiparisPim,
  useEslesmemisKabuller,
  useSiparisler,
} from './siparisHooks';

const HAT = BOLUM_RENGI['menu.bolum_stok'];

type Suzgec = 'tum' | SiparisDurum;
const SUZGECLER: Suzgec[] = ['tum', 'acik', 'kismi_teslim', 'tamamlandi', 'kapatildi', 'iptal'];

function tarih(v: string | null): string {
  return v ? new Date(v).toLocaleDateString('tr-TR') : '—';
}

export function SiparisListesi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const stokOkur = useAuthStore((s) => s.izinVar('stok:oku'));
  const [suzgec, setSuzgec] = useState<Suzgec>('tum');
  const tumu = useSiparisler();
  const eslesmemis = useEslesmemisKabuller(stokOkur);

  const liste = useMemo(
    () => (tumu.data ?? []).filter((s) => suzgec === 'tum' || s.durum === suzgec),
    [tumu.data, suzgec],
  );
  const sayi = (d: SiparisDurum) => (tumu.data ?? []).filter((s) => s.durum === d).length;
  const gecikenSayi = (tumu.data ?? []).filter(gecikmis).length;

  const kolonlar: ColumnsType<SiparisOzet> = [
    {
      title: t('siparis.kod'),
      dataIndex: 'kod',
      render: (v: string, s) => (
        <Link to={`/satinalma-siparisleri/${s.id}`} className="varlik-ad sayisal">
          {v}
          <span className="varlik-alt siparis-alt-tedarikci">{s.tedarikci_ad}</span>
        </Link>
      ),
    },
    {
      title: t('siparis.tedarikci'),
      dataIndex: 'tedarikci_ad',
      responsive: ['md'],
      ellipsis: true,
    },
    {
      title: t('siparis.durum'),
      dataIndex: 'durum',
      render: (d: SiparisDurum) => <SiparisPim durum={d} />,
    },
    {
      title: t('siparis.teslim'),
      dataIndex: 'teslim_orani',
      width: 150,
      render: (v: number, s) => (
        <Progress
          percent={Math.round(v * 100)}
          size="small"
          strokeColor={s.durum === 'tamamlandi' ? RENKLER.basari : RENKLER.mavi}
          aria-label={t('siparis.teslim')}
        />
      ),
    },
    {
      title: t('siparis.beklenen'),
      dataIndex: 'beklenen_teslim_tarihi',
      responsive: ['sm'],
      render: (v: string | null, s) =>
        gecikmis(s) ? (
          <span style={{ color: 'var(--hata)', fontWeight: 600 }}>
            {tarih(v)} · {t('siparis.gecikti')}
          </span>
        ) : (
          tarih(v)
        ),
    },
    {
      title: t('siparis.tutar'),
      dataIndex: 'toplam_tutar',
      align: 'right',
      responsive: ['lg'],
      render: (v: number, s) => (
        <span className="sayisal">
          {v.toLocaleString('tr-TR', { maximumFractionDigits: 2 })} {s.para_birimi}
        </span>
      ),
    },
  ];

  const kabulKolonlar: ColumnsType<EslesmemisKabul> = [
    {
      title: t('siparis.irsaliye'),
      dataIndex: 'irsaliye_no',
      render: (v: string, k) => (
        <span>
          <span className="sayisal">{v}</span>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {k.malzeme_kod} · {k.malzeme_ad}
          </span>
        </span>
      ),
    },
    {
      title: t('siparis.miktar'),
      dataIndex: 'miktar',
      align: 'right',
      render: (v: number, k) => (
        <span className="sayisal">
          {v} {k.birim}
        </span>
      ),
    },
    {
      title: t('siparis.bekliyor'),
      dataIndex: 'bekleyen_gun',
      align: 'right',
      render: (v: number) => (
        <span style={{ color: v >= 3 ? 'var(--uyari)' : undefined }}>
          {t('siparis.gun', { n: v })}
        </span>
      ),
    },
  ];

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('siparis.baslik')} alt={t('siparis.alt')} />
      <OzetSerit
        renk={HAT}
        yukleniyor={tumu.isPending}
        metrikler={[
          {
            anahtar: 'acik',
            baslik: t('siparis.ozet_acik'),
            deger: String(sayi('acik')),
            ikon: <ShoppingCartOutlined />,
          },
          {
            anahtar: 'kismi',
            baslik: t('siparis.ozet_kismi'),
            deger: String(sayi('kismi_teslim')),
            ikon: <InboxOutlined />,
          },
          {
            anahtar: 'gecikmis',
            baslik: t('siparis.ozet_gecikmis'),
            deger: String(gecikenSayi),
            ikon: <ClockCircleOutlined />,
            olumlu: gecikenSayi === 0,
          },
          {
            anahtar: 'eslesmemis',
            baslik: t('siparis.ozet_eslesmemis'),
            deger: stokOkur ? String((eslesmemis.data ?? []).length) : '—',
            ikon: <WarningOutlined />,
          },
        ]}
      />
      <div style={{ height: 20 }} />
      <Card styles={{ body: { padding: 18 } }}>
        <div className="siparis-suzgec">
          <Segmented<Suzgec>
            value={suzgec}
            onChange={setSuzgec}
            options={SUZGECLER.map((s) => ({
              value: s,
              label: s === 'tum' ? t('siparis.tumu') : t(`siparis.durum_${s}`),
            }))}
          />
        </div>
        <Table<SiparisOzet>
          rowKey="id"
          columns={kolonlar}
          dataSource={liste}
          loading={tumu.isPending}
          pagination={{ pageSize: 20, hideOnSinglePage: true }}
          onRow={(s) => ({
            onClick: () => navigate(`/satinalma-siparisleri/${s.id}`),
            style: { cursor: 'pointer' },
          })}
          locale={{
            emptyText: (
              <BosDurum baslik={t('siparis.bos_baslik')} aciklama={t('siparis.bos_aciklama')} />
            ),
          }}
        />
      </Card>

      {stokOkur && (eslesmemis.data ?? []).length > 0 && (
        <Card
          title={t('siparis.eslesmemis_baslik')}
          style={{ marginTop: 20 }}
          styles={{ body: { padding: 18 } }}
        >
          <p className="varlik-alt" style={{ marginTop: 0 }}>
            {t('siparis.eslesmemis_aciklama')}
          </p>
          <Table<EslesmemisKabul>
            rowKey="hareket_id"
            size="small"
            columns={kabulKolonlar}
            dataSource={eslesmemis.data ?? []}
            pagination={{ pageSize: 10, hideOnSinglePage: true }}
          />
        </Card>
      )}
    </SayfaKapsayici>
  );
}
