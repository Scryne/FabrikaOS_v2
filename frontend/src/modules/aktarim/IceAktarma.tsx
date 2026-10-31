/**
 * Veri içe aktarma (S21, ADR-0042): onboarding için ana veri ve açılış stoğu.
 *
 * Akış: tür seç → (şablonu indir) → dosyayı bırak → önizleme otomatik → hatasızsa uygula.
 * Sıra önemlidir (firma → malzeme → açılış stoğu): soldaki liste bu sırayla numaralıdır.
 * Önizleme değer göstermez (anahtar, işlem, değişen alan adları, hata) — KVKK.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { DownloadOutlined, InboxOutlined, LockOutlined } from '@ant-design/icons';
import { Alert, App, Button, Card, Segmented, Table, Tag, Upload } from 'antd';
import type { ColumnsType } from 'antd/es/table';

import { ApiHata } from '@/api/client';
import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';

import {
  type AktarimTur,
  type Onizleme,
  type SatirIslem,
  type SatirSonucu,
  sablonIndir,
  useAktarimTurleri,
  useOnizle,
  useUygula,
} from './hooks';

const ISLEM_RENK: Record<SatirIslem, string> = {
  yeni: 'green',
  guncelle: 'blue',
  ayni: 'default',
  hata: 'red',
};

type Suzgec = 'tum' | SatirIslem;

export function IceAktarma() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const turler = useAktarimTurleri();
  const onizle = useOnizle();
  const uygula = useUygula();
  const [secili, setSecili] = useState<string | null>(null);
  const [dosya, setDosya] = useState<File | null>(null);
  const [onizleme, setOnizleme] = useState<Onizleme | null>(null);
  const [suzgec, setSuzgec] = useState<Suzgec>('tum');
  const [sonuc, setSonuc] = useState<Onizleme | null>(null);
  const sonucRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Uygulama sonrası önizleme kapanır; uzun tablodan aşağıda kalan görünüm sonuca taşınır.
    if (sonuc) sonucRef.current?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [sonuc]);

  const liste = turler.data ?? [];
  const tur: AktarimTur | undefined =
    liste.find((x) => x.kod === secili) ?? liste.find((x) => x.yetkili);

  const sifirla = () => {
    setDosya(null);
    setOnizleme(null);
    setSuzgec('tum');
  };

  const turSec = (kod: string) => {
    setSecili(kod);
    setSonuc(null);
    sifirla();
  };

  const dosyaSec = (f: File) => {
    if (!tur) return false;
    setDosya(f);
    setSonuc(null);
    setOnizleme(null);
    setSuzgec('tum');
    onizle.mutate(
      { tur: tur.kod, dosya: f },
      {
        onSuccess: (o) => {
          setOnizleme(o);
          if (o.hatali > 0) setSuzgec('hata');
        },
        onError: (e) => message.error(e instanceof ApiHata ? e.message : t('aktarim.okunamadi')),
      },
    );
    return false; // Upload kendi başına göndermez; dosya önizleme ucuna gider.
  };

  const uygulaTikla = () => {
    if (!tur || !dosya) return;
    uygula.mutate(
      { tur: tur.kod, dosya },
      {
        onSuccess: (o) => {
          setSonuc(o);
          sifirla();
        },
        onError: (e) => message.error(e instanceof ApiHata ? e.message : t('aktarim.uygulanamadi')),
      },
    );
  };

  const gorunen = useMemo(
    () => (onizleme?.satirlar ?? []).filter((s) => suzgec === 'tum' || s.islem === suzgec),
    [onizleme, suzgec],
  );

  const kolonlar: ColumnsType<SatirSonucu> = [
    { title: t('aktarim.satir'), dataIndex: 'satir', width: 72, className: 'sayisal' },
    {
      title: t('aktarim.anahtar'),
      dataIndex: 'anahtar',
      render: (v: string) => <span className="varlik-ad">{v || '—'}</span>,
    },
    {
      title: t('aktarim.islem'),
      dataIndex: 'islem',
      width: 130,
      render: (v: SatirIslem) => <Tag color={ISLEM_RENK[v]}>{t(`aktarim.islem_${v}`)}</Tag>,
    },
    {
      title: t('aktarim.ayrinti'),
      key: 'ayrinti',
      render: (_: unknown, s) =>
        s.hatalar.length > 0 ? (
          <ul className="aktarim-hatalar">
            {s.hatalar.map((h) => (
              <li key={`${h.alan}-${h.mesaj}`}>
                <code>{h.alan}</code> {h.mesaj}
              </li>
            ))}
          </ul>
        ) : s.degisen.length > 0 ? (
          <span className="varlik-alt">
            {t('aktarim.degisen')}: {s.degisen.join(', ')}
          </span>
        ) : null,
    },
  ];

  const uygulanabilir =
    onizleme !== null && onizleme.hatali === 0 && onizleme.yeni + onizleme.guncelle > 0;

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('aktarim.baslik')} alt={t('aktarim.aciklama')} />

      <div className="aktarim-duzen">
        <Card size="small" title={t('aktarim.turler')} className="aktarim-turler">
          <ol className="aktarim-tur-listesi">
            {liste.map((x) => (
              <li key={x.kod}>
                <button
                  type="button"
                  className={`aktarim-tur${tur?.kod === x.kod ? ' aktarim-tur--secili' : ''}`}
                  disabled={!x.yetkili}
                  aria-pressed={tur?.kod === x.kod}
                  onClick={() => turSec(x.kod)}
                >
                  <span>{x.baslik}</span>
                  {!x.yetkili && <LockOutlined aria-label={t('aktarim.yetki_yok')} />}
                </button>
              </li>
            ))}
          </ol>
          <p className="varlik-alt aktarim-sira-notu">{t('aktarim.sira_notu')}</p>
        </Card>

        {tur ? (
          <div className="aktarim-calisma">
            <Card
              size="small"
              title={tur.baslik}
              extra={
                <Button icon={<DownloadOutlined />} onClick={() => void sablonIndir(tur.kod)}>
                  {t('aktarim.sablon')}
                </Button>
              }
            >
              {tur.aciklama && <p className="aktarim-tur-aciklama">{tur.aciklama}</p>}
              <Table
                size="small"
                pagination={false}
                rowKey="ad"
                dataSource={tur.alanlar}
                scroll={{ x: 'max-content' }}
                columns={[
                  {
                    title: t('aktarim.kolon'),
                    dataIndex: 'ad',
                    render: (v: string, a) => (
                      <code>
                        {v}
                        {a.zorunlu && <span className="aktarim-zorunlu"> *</span>}
                      </code>
                    ),
                  },
                  { title: t('aktarim.kolon_aciklama'), dataIndex: 'aciklama' },
                  {
                    title: t('aktarim.ornek'),
                    dataIndex: 'ornek',
                    responsive: ['md'],
                    render: (v: string) => <span className="varlik-alt">{v}</span>,
                  },
                ]}
              />
              <p className="varlik-alt aktarim-eslesme">
                {t('aktarim.eslesme', { anahtar: tur.anahtar.join(' / ') })}
              </p>
            </Card>

            {sonuc && (
              <div ref={sonucRef}>
                <Alert
                  type="success"
                  showIcon
                  closable
                  onClose={() => setSonuc(null)}
                  message={t('aktarim.uygulandi', {
                    yeni: sonuc.yeni,
                    guncelle: sonuc.guncelle,
                    ayni: sonuc.ayni,
                  })}
                  description={t('aktarim.uygulandi_alt')}
                />
              </div>
            )}

            <Upload.Dragger
              accept=".csv,.xlsx"
              multiple={false}
              showUploadList={false}
              beforeUpload={dosyaSec}
              disabled={onizle.isPending || uygula.isPending}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">{dosya ? dosya.name : t('aktarim.dosya_birak')}</p>
              <p className="ant-upload-hint">{t('aktarim.dosya_ipucu')}</p>
            </Upload.Dragger>

            {onizleme && (
              <Card size="small" title={t('aktarim.onizleme')}>
                <OzetSerit
                  metrikler={[
                    {
                      anahtar: 'toplam',
                      baslik: t('aktarim.toplam'),
                      deger: String(onizleme.toplam),
                    },
                    {
                      anahtar: 'yeni',
                      baslik: t('aktarim.islem_yeni'),
                      deger: String(onizleme.yeni),
                    },
                    {
                      anahtar: 'guncelle',
                      baslik: t('aktarim.islem_guncelle'),
                      deger: String(onizleme.guncelle),
                    },
                    {
                      anahtar: 'ayni',
                      baslik: t('aktarim.islem_ayni'),
                      deger: String(onizleme.ayni),
                    },
                    {
                      anahtar: 'hata',
                      baslik: t('aktarim.islem_hata'),
                      deger: String(onizleme.hatali),
                      olumlu: onizleme.hatali === 0,
                    },
                  ]}
                />
                {onizleme.eksik_kolonlar.length > 0 && (
                  <Alert
                    type="error"
                    showIcon
                    className="aktarim-uyari"
                    message={t('aktarim.eksik_kolon', {
                      kolonlar: onizleme.eksik_kolonlar.join(', '),
                    })}
                  />
                )}
                {onizleme.bilinmeyen_kolonlar.length > 0 && (
                  <Alert
                    type="warning"
                    showIcon
                    className="aktarim-uyari"
                    message={t('aktarim.bilinmeyen_kolon', {
                      kolonlar: onizleme.bilinmeyen_kolonlar.join(', '),
                    })}
                  />
                )}
                <div className="aktarim-arac">
                  <Segmented<Suzgec>
                    value={suzgec}
                    onChange={setSuzgec}
                    options={[
                      { value: 'tum', label: t('aktarim.suzgec_tum') },
                      { value: 'hata', label: t('aktarim.islem_hata') },
                      { value: 'yeni', label: t('aktarim.islem_yeni') },
                      { value: 'guncelle', label: t('aktarim.islem_guncelle') },
                    ]}
                  />
                  <div className="aktarim-dugmeler">
                    <Button onClick={sifirla}>{t('ortak.vazgec')}</Button>
                    <Button
                      type="primary"
                      disabled={!uygulanabilir}
                      loading={uygula.isPending}
                      onClick={uygulaTikla}
                    >
                      {t('aktarim.uygula', { adet: onizleme.yeni + onizleme.guncelle })}
                    </Button>
                  </div>
                </div>
                {onizleme.hatali > 0 && (
                  <p className="aktarim-hata-notu">{t('aktarim.hata_notu')}</p>
                )}
                <Table<SatirSonucu>
                  size="small"
                  rowKey="satir"
                  dataSource={gorunen}
                  columns={kolonlar}
                  pagination={{ pageSize: 50, hideOnSinglePage: true }}
                  scroll={{ x: 'max-content' }}
                />
                {onizleme.toplam > onizleme.satirlar.length && (
                  <p className="varlik-alt">
                    {t('aktarim.kirpildi', { gosterilen: onizleme.satirlar.length })}
                  </p>
                )}
              </Card>
            )}
          </div>
        ) : (
          !turler.isLoading && <Alert type="info" showIcon message={t('aktarim.hic_yetki')} />
        )}
      </div>
    </SayfaKapsayici>
  );
}
