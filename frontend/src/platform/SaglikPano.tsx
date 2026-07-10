/**
 * Platform sağlık panosu — servis sondaları (LED dili: db/redis/nesne deposu) +
 * tenant sayıları + sürüm/ortam. 30 sn'de bir yoklanır (hooks.usePlatformSaglik).
 */

import { useTranslation } from 'react-i18next';
import { Card, Col, Row, Skeleton } from 'antd';

import { KpiKart } from '@/components/KpiKart';

import { usePlatformSaglik } from './hooks';

function SondaKarti({ ad, durum, detay }: { ad: string; durum: string; detay?: string | null }) {
  const { t } = useTranslation();
  const saglikli = durum === 'saglikli';
  return (
    <Card size="small">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span
          aria-hidden="true"
          style={{
            width: 10,
            height: 10,
            borderRadius: '50%',
            background: saglikli ? 'var(--basari)' : 'var(--hata)',
            boxShadow: saglikli ? '0 0 8px var(--basari)' : '0 0 8px var(--hata)',
          }}
        />
        <span style={{ fontWeight: 600 }}>{ad}</span>
        <span style={{ color: saglikli ? 'var(--basari)' : 'var(--hata)', fontSize: 13 }}>
          {saglikli ? t('platform.saglikli') : t('platform.hatali')}
        </span>
      </div>
      {!saglikli && detay && (
        <div
          style={{
            color: 'var(--metin-soluk)',
            fontSize: 12,
            marginTop: 8,
            wordBreak: 'break-all',
          }}
        >
          {detay}
        </div>
      )}
    </Card>
  );
}

export function SaglikPano() {
  const { t } = useTranslation();
  const { data, isLoading } = usePlatformSaglik();

  if (isLoading || data == null) return <Skeleton active paragraph={{ rows: 6 }} />;

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
        <h2 style={{ margin: 0, fontSize: 17 }}>{t('platform.saglik')}</h2>
        <span className="sayisal" style={{ color: 'var(--metin-soluk)', fontSize: 12 }}>
          {t('platform.surum')} {data.surum} · {t('platform.ortam')} {data.ortam}
        </span>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <SondaKarti
            ad={t('platform.veritabani')}
            durum={data.veritabani.durum}
            detay={data.veritabani.detay}
          />
        </Col>
        <Col xs={24} md={8}>
          <SondaKarti ad="Redis" durum={data.redis.durum} detay={data.redis.detay} />
        </Col>
        <Col xs={24} md={8}>
          <SondaKarti
            ad={t('platform.nesne_depo')}
            durum={data.nesne_depo.durum}
            detay={data.nesne_depo.detay}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <KpiKart
            baslik={t('platform.tenant_toplam')}
            deger={String(data.tenant_toplam)}
            renk="#f97316"
          />
        </Col>
        <Col xs={24} md={8}>
          <KpiKart
            baslik={t('platform.tenant_aktif')}
            deger={String(data.tenant_aktif)}
            renk="var(--basari)"
          />
        </Col>
        <Col xs={24} md={8}>
          <KpiKart
            baslik={t('platform.tenant_askida')}
            deger={String(data.tenant_askida)}
            renk="var(--uyari)"
          />
        </Col>
      </Row>
    </div>
  );
}
