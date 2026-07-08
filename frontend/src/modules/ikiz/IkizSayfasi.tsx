/**
 * Dijital ikiz — tesis şeması (SVG) üzerinde canlı makine durumu.
 *
 * Görünüm modu: düğüme tıkla → yan panelde detay (durum, pencere OEE'si, üretim, bölge).
 * Düzenleme modu (`uretim:yaz`): düğümleri sürükle-taşı, paletten yerleştir, × ile kaldır,
 * Kaydet → `PUT /ikiz/yerlesim` (replace-all). Canlılık: WS olayları `['ikiz']` sorgusunu
 * geçersizleştirir (olayIsle), sürükleme matematiği saf `sunum.ts`'tedir.
 */

import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useNavigate } from 'react-router-dom';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { ApartmentOutlined, CloseOutlined, DesktopOutlined, EditOutlined } from '@ant-design/icons';
import { Button, Card, Col, Descriptions, Row, Space, Spin, Tag, Typography } from 'antd';

import { BosDurum } from '@/components/BosDurum';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { useAuthStore } from '@/store/authStore';

import { useIkizDurum, useYerlesimKaydet } from './hooks';
import {
  DURUM_RENGI,
  durumRengi,
  konumdanYuzde,
  oeeEtiket,
  svgKonum,
  taslakDugumler,
  TUVAL,
  type IkizDugumGiris,
} from './sunum';

/** Yeni yerleştirilen düğümler üst üste binmesin diye kademeli başlangıç konumu. */
function yeniKonum(sira: number): { x: number; y: number } {
  return { x: 30 + (sira % 5) * 10, y: 30 + (Math.floor(sira / 5) % 4) * 15 };
}

export function IkizSayfasi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const izinVar = useAuthStore((s) => s.izinVar);
  const yazabilir = izinVar('uretim:yaz');

  const { data, isPending } = useIkizDurum();
  const kaydet = useYerlesimKaydet();

  const [duzenleme, setDuzenleme] = useState(false);
  const [taslak, setTaslak] = useState<IkizDugumGiris[]>([]);
  const [suruklenen, setSuruklenen] = useState<number | null>(null);
  const [secili, setSecili] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  // Makine kimlik haritası (kod/ad/durum): düğümler + yerleşmemişler tek sözlükte.
  const makineler = useMemo(() => {
    const harita = new Map<
      number,
      { kod: string; ad: string; durum: string; oee?: number | null }
    >();
    for (const d of data?.dugumler ?? [])
      harita.set(d.makine_id, { kod: d.makine_kod, ad: d.makine_ad, durum: d.durum, oee: d.oee });
    for (const m of data?.yerlesmemis ?? [])
      harita.set(m.makine_id, { kod: m.makine_kod, ad: m.makine_ad, durum: m.durum });
    return harita;
  }, [data]);

  // Çizilecek düğümler: düzenlemede taslak, görünümde sunucu verisi.
  const cizilecek: IkizDugumGiris[] = duzenleme ? taslak : taslakDugumler(data?.dugumler ?? []);
  const paletteki = [...makineler.keys()].filter(
    (id) => !cizilecek.some((d) => d.makine_id === id),
  );

  const duzenlemeBaslat = () => {
    setTaslak(taslakDugumler(data?.dugumler ?? []));
    setSecili(null);
    setDuzenleme(true);
  };
  const vazgec = () => {
    setDuzenleme(false);
    setSuruklenen(null);
  };
  const kaydetVeCik = () => {
    kaydet.mutate(taslak, { onSuccess: () => setDuzenleme(false) });
  };
  const dugumEkle = (makineId: number) => {
    setTaslak((eski) => [...eski, { makine_id: makineId, bolge: '', ...yeniKonum(eski.length) }]);
  };
  const dugumKaldir = (makineId: number) => {
    setTaslak((eski) => eski.filter((d) => d.makine_id !== makineId));
    if (secili === makineId) setSecili(null);
  };

  const tasi = (e: ReactPointerEvent<SVGSVGElement>) => {
    if (!duzenleme || suruklenen === null || !svgRef.current) return;
    const konum = konumdanYuzde(e.clientX, e.clientY, svgRef.current.getBoundingClientRect());
    setTaslak((eski) => eski.map((d) => (d.makine_id === suruklenen ? { ...d, ...konum } : d)));
  };

  const seciliDugum = (data?.dugumler ?? []).find((d) => d.makine_id === secili);

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.ikiz')}
        alt={t('ikiz.alt')}
        sag={
          duzenleme ? (
            <Space>
              <Button onClick={vazgec}>{t('ortak.iptal')}</Button>
              <Button type="primary" loading={kaydet.isPending} onClick={kaydetVeCik}>
                {t('ortak.kaydet')}
              </Button>
            </Space>
          ) : (
            <Space>
              <Button icon={<DesktopOutlined />} onClick={() => navigate('/kiosk')}>
                {t('ikiz.kiosk_modu')}
              </Button>
              {yazabilir && (
                <Button icon={<EditOutlined />} onClick={duzenlemeBaslat} disabled={isPending}>
                  {t('ikiz.duzenle')}
                </Button>
              )}
            </Space>
          )
        }
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={17}>
          <Card
            size="small"
            styles={{ body: { padding: 8 } }}
            title={
              <Space size={14} wrap>
                {Object.entries(DURUM_RENGI).map(([durum, renk]) => (
                  <span
                    key={durum}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6,
                      fontSize: 12,
                      color: 'var(--metin-soluk)',
                      fontWeight: 400,
                    }}
                  >
                    <span
                      aria-hidden="true"
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: renk,
                        display: 'inline-block',
                      }}
                    />
                    {t(`uretim.durum_${durum}`)}
                  </span>
                ))}
              </Space>
            }
          >
            {isPending ? (
              <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
                <Spin />
              </div>
            ) : !duzenleme && cizilecek.length === 0 ? (
              <BosDurum
                ikon={<ApartmentOutlined />}
                baslik={t('ikiz.bos')}
                aciklama={yazabilir ? t('ikiz.bos_ipucu') : undefined}
                aksiyon={
                  yazabilir ? (
                    <Button type="primary" icon={<EditOutlined />} onClick={duzenlemeBaslat}>
                      {t('ikiz.duzenle')}
                    </Button>
                  ) : undefined
                }
              />
            ) : (
              <svg
                ref={svgRef}
                role="img"
                aria-label={t('ikiz.sema_etiketi')}
                viewBox={`0 0 ${TUVAL.genislik} ${TUVAL.yukseklik}`}
                style={{
                  width: '100%',
                  display: 'block',
                  background: 'var(--zemin)',
                  borderRadius: 8,
                  touchAction: 'none',
                }}
                onPointerMove={tasi}
                onPointerUp={() => setSuruklenen(null)}
                onPointerLeave={() => setSuruklenen(null)}
              >
                <defs>
                  <pattern id="ikiz-izgara" width="8" height="9" patternUnits="userSpaceOnUse">
                    <path
                      d="M 8 0 L 0 0 0 9"
                      fill="none"
                      stroke="var(--kenarlik)"
                      strokeWidth="0.15"
                    />
                  </pattern>
                </defs>
                <rect width={TUVAL.genislik} height={TUVAL.yukseklik} fill="url(#ikiz-izgara)" />
                {cizilecek.map((d) => {
                  const bilgi = makineler.get(d.makine_id);
                  if (!bilgi) return null;
                  const { sx, sy } = svgKonum(d.x, d.y);
                  const renk = durumRengi(bilgi.durum);
                  const canliOee = duzenleme
                    ? undefined
                    : (data?.dugumler ?? []).find((n) => n.makine_id === d.makine_id)?.oee;
                  return (
                    <g
                      key={d.makine_id}
                      transform={`translate(${sx}, ${sy})`}
                      style={{ cursor: duzenleme ? 'grab' : 'pointer' }}
                      onPointerDown={duzenleme ? () => setSuruklenen(d.makine_id) : undefined}
                      onClick={duzenleme ? undefined : () => setSecili(d.makine_id)}
                    >
                      <title>{`${bilgi.kod} — ${bilgi.ad}`}</title>
                      <rect
                        x={-9}
                        y={-5}
                        width={18}
                        height={10}
                        rx={1.2}
                        fill="var(--yuzey-ust)"
                        stroke={secili === d.makine_id && !duzenleme ? 'var(--mavi)' : renk}
                        strokeWidth={secili === d.makine_id && !duzenleme ? 0.6 : 0.35}
                      />
                      <circle cx={-6.6} cy={-2.2} r={0.9} fill={renk} />
                      <text
                        x={-4.9}
                        y={-1.3}
                        fontSize={2.7}
                        fontFamily="var(--font-mono)"
                        fill="var(--metin)"
                      >
                        {bilgi.kod}
                      </text>
                      {!duzenleme && canliOee != null && (
                        <>
                          <rect
                            x={-6.6}
                            y={1.4}
                            width={13.2}
                            height={1.1}
                            rx={0.55}
                            fill="var(--kenarlik)"
                          />
                          <rect
                            x={-6.6}
                            y={1.4}
                            width={13.2 * Math.min(1, Math.max(0, canliOee))}
                            height={1.1}
                            rx={0.55}
                            fill={renk}
                          />
                        </>
                      )}
                      {duzenleme && (
                        <g
                          onClick={(e) => {
                            e.stopPropagation();
                            dugumKaldir(d.makine_id);
                          }}
                          onPointerDown={(e) => e.stopPropagation()}
                          style={{ cursor: 'pointer' }}
                        >
                          <circle cx={8} cy={-4.2} r={1.6} fill="var(--hata)" />
                          <path
                            d="M -0.7 -0.7 L 0.7 0.7 M 0.7 -0.7 L -0.7 0.7"
                            transform="translate(8, -4.2)"
                            stroke="#fff"
                            strokeWidth={0.35}
                          />
                        </g>
                      )}
                    </g>
                  );
                })}
              </svg>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={7}>
          {duzenleme ? (
            <Card size="small" title={t('ikiz.yerlesmemis')}>
              {paletteki.length === 0 ? (
                <Typography.Text type="secondary">{t('ikiz.yerlesmemis_bos')}</Typography.Text>
              ) : (
                <Space size={[6, 6]} wrap>
                  {paletteki.map((id) => {
                    const bilgi = makineler.get(id);
                    if (!bilgi) return null;
                    return (
                      <Tag
                        key={id}
                        style={{ cursor: 'pointer', userSelect: 'none' }}
                        onClick={() => dugumEkle(id)}
                      >
                        + {bilgi.kod}
                      </Tag>
                    );
                  })}
                </Space>
              )}
              <Typography.Paragraph
                type="secondary"
                style={{ fontSize: 12, marginTop: 12, marginBottom: 0 }}
              >
                {t('ikiz.duzenleme_ipucu')}
              </Typography.Paragraph>
            </Card>
          ) : seciliDugum ? (
            <Card
              size="small"
              title={
                <Space>
                  <span
                    aria-hidden="true"
                    style={{
                      width: 9,
                      height: 9,
                      borderRadius: '50%',
                      background: durumRengi(seciliDugum.durum),
                      display: 'inline-block',
                    }}
                  />
                  <span className="sayisal">{seciliDugum.makine_kod}</span>
                </Space>
              }
              extra={
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  aria-label={t('ortak.kapat')}
                  onClick={() => setSecili(null)}
                />
              }
            >
              <Descriptions column={1} size="small" colon={false}>
                <Descriptions.Item label={t('uretim.ad')}>
                  {seciliDugum.makine_ad}
                </Descriptions.Item>
                <Descriptions.Item label={t('uretim.durum')}>
                  {t(`uretim.durum_${seciliDugum.durum}`, { defaultValue: seciliDugum.durum })}
                </Descriptions.Item>
                <Descriptions.Item label={t('ikiz.pencere_oee')}>
                  <span className="sayisal">{oeeEtiket(seciliDugum.oee)}</span>
                </Descriptions.Item>
                <Descriptions.Item label={t('ikiz.pencere_uretim')}>
                  <span className="sayisal">{seciliDugum.toplam_adet.toLocaleString('tr-TR')}</span>
                </Descriptions.Item>
                <Descriptions.Item label={t('ikiz.son_veri')}>
                  {seciliDugum.son_veri_zamani
                    ? new Date(seciliDugum.son_veri_zamani).toLocaleString('tr-TR')
                    : '—'}
                </Descriptions.Item>
                {seciliDugum.bolge && (
                  <Descriptions.Item label={t('ikiz.bolge')}>{seciliDugum.bolge}</Descriptions.Item>
                )}
              </Descriptions>
              <Link to={`/makineler/${seciliDugum.makine_id}`}>{t('ikiz.makine_sayfasi')}</Link>
            </Card>
          ) : (
            <Card size="small">
              <BosDurum ikon={<ApartmentOutlined />} baslik={t('ikiz.detay_ipucu')} />
            </Card>
          )}
        </Col>
      </Row>
    </div>
  );
}
