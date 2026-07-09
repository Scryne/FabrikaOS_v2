/**
 * Abonelik & Modüller ekranı (S16 / ADR-0018, uiplani §11.1).
 *
 * Plan kartı (ad + dönem) + koltuk kullanımı progress (eşik renkli) + hat renkli
 * modül entitlement matrisi + "deneysel" özellik bayrağı rozetleri. Salt-okunur:
 * entitlement değişikliği platform tarafındadır (S17).
 */

import type { CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircleOutlined, LockOutlined, TeamOutlined } from '@ant-design/icons';
import { Card, Col, Progress, Row, Skeleton, Tag } from 'antd';

import { KpiKart } from '@/components/KpiKart';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { BOLUM_RENGI, MENU_IKONLARI, MODUL_KIMLIK } from '@/tema/modulKimlik';

import { type ModulDurum, type OzellikDurum, useAbonelik } from './hooks';

function tarih(iso: string | null | undefined): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('tr-TR');
}

/** Koltuk doluluk rengi: %90+ kırmızı, %70+ amber, altı mavi (eşik sinyali). */
function koltukRengi(oran: number): string {
  if (oran >= 0.9) return 'var(--hata)';
  if (oran >= 0.7) return 'var(--uyari)';
  return 'var(--mavi)';
}

function ModulKarti({ modul }: { modul: ModulDurum }) {
  const { t } = useTranslation();
  const kimlik = MODUL_KIMLIK[modul.kod];
  const renk = kimlik ? BOLUM_RENGI[kimlik.bolum] : 'var(--mavi)';
  const ikon = kimlik ? MENU_IKONLARI[kimlik.anahtar] : undefined;
  return (
    <div className="modul-kart" style={{ opacity: modul.acik ? 1 : 0.55 }}>
      <span
        className="ikon-plaka kucuk"
        style={{ '--plaka-renk': renk } as CSSProperties}
        aria-hidden="true"
      >
        {ikon}
      </span>
      <div style={{ minWidth: 0, flex: 1 }}>
        <div className="modul-kart-ad">{modul.ad}</div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 4 }}>
          {modul.acik ? (
            <Tag icon={<CheckCircleOutlined />} color="success">
              {t('abonelik.modul_acik')}
            </Tag>
          ) : (
            <Tag icon={<LockOutlined />}>{t('abonelik.modul_kapali_rozet')}</Tag>
          )}
          {modul.kaynak === 'hak' && <Tag color="processing">{t('abonelik.kaynak_hak')}</Tag>}
        </div>
      </div>
    </div>
  );
}

export function AbonelikSayfasi() {
  const { t } = useTranslation();
  const { data, isLoading } = useAbonelik();

  const koltukMetni =
    data == null
      ? '—'
      : data.koltuk.limit == null
        ? t('abonelik.koltuk_sinirsiz')
        : t('abonelik.koltuk_deger', {
            kullanilan: data.koltuk.kullanilan,
            limit: data.koltuk.limit,
          });
  const koltukOran =
    data?.koltuk.limit != null && data.koltuk.limit > 0
      ? data.koltuk.kullanilan / data.koltuk.limit
      : null;

  return (
    <SayfaKapsayici>
      <SayfaBaslik baslik={t('menu.abonelik')} alt={t('abonelik.alt')} />

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <KpiKart
            baslik={t('abonelik.plan')}
            renk="var(--hat-yonetim)"
            deger={data?.plan.ad ?? '—'}
            ikon={MENU_IKONLARI['abonelik']}
            altMetin={t(`abonelik.durum_${data?.durum ?? 'deneme'}`, {
              defaultValue: data?.durum ?? '—',
            })}
          />
        </Col>
        <Col xs={24} md={8}>
          <KpiKart
            baslik={t('abonelik.baslangic')}
            renk="var(--hat-yonetim)"
            deger={tarih(data?.baslangic_tarihi)}
            altMetin={`${t('abonelik.bitis')}: ${
              data?.bitis_tarihi ? tarih(data.bitis_tarihi) : t('abonelik.bitis_yok')
            }`}
          />
        </Col>
        <Col xs={24} md={8}>
          <Card styles={{ body: { padding: 16 } }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <TeamOutlined aria-hidden="true" style={{ color: 'var(--metin-soluk)' }} />
              <span style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>
                {t('abonelik.koltuk')}
              </span>
            </div>
            <div className="sayisal" style={{ fontSize: 20, marginTop: 6 }}>
              {koltukMetni}
            </div>
            {koltukOran != null && (
              <Progress
                percent={Math.min(100, Math.round(koltukOran * 100))}
                showInfo={false}
                strokeColor={koltukRengi(koltukOran)}
                size="small"
              />
            )}
          </Card>
        </Col>
      </Row>

      <Card title={t('abonelik.moduller')} style={{ marginTop: 16 }}>
        {isLoading ? (
          <Skeleton active paragraph={{ rows: 4 }} />
        ) : (
          <Row gutter={[12, 12]}>
            {(data?.moduller ?? []).map((m) => (
              <Col xs={24} sm={12} lg={8} xl={6} key={m.kod}>
                <ModulKarti modul={m} />
              </Col>
            ))}
          </Row>
        )}
      </Card>

      <Card title={t('abonelik.ozellikler')} style={{ marginTop: 16 }}>
        <Row gutter={[12, 12]}>
          {(data?.ozellikler ?? []).map((o: OzellikDurum) => (
            <Col xs={24} sm={12} key={o.kod}>
              <div className="modul-kart" style={{ opacity: o.acik ? 1 : 0.55 }}>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div className="modul-kart-ad">{o.ad}</div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    {o.acik ? (
                      <Tag icon={<CheckCircleOutlined />} color="success">
                        {t('abonelik.modul_acik')}
                      </Tag>
                    ) : (
                      <Tag icon={<LockOutlined />}>{t('abonelik.modul_kapali_rozet')}</Tag>
                    )}
                    {o.deneysel && <Tag color="warning">{t('abonelik.deneysel')}</Tag>}
                  </div>
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </Card>
    </SayfaKapsayici>
  );
}
