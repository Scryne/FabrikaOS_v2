/**
 * İş emri detay çekmecesi — künye (Descriptions) + durum geçiş aksiyonları + yorum/aktivite
 * akışı + AI operatör önerisi (S-VB). ``isemri:yaz`` ile yorum eklenir ve durum ilerletilir;
 * öneri ``ai:oku`` + açık iş emrinde görünür. Makine/atanan adları sözlüklerden çözülür.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ThunderboltOutlined } from '@ant-design/icons';
import {
  Button,
  Descriptions,
  Divider,
  Drawer,
  Empty,
  Input,
  Skeleton,
  Space,
  Tag,
  Tooltip,
  Typography,
} from 'antd';
import dayjs from 'dayjs';

import { DurumZamanCizelgesi } from '@/components/DetayOgeleri';
import { MiniBar } from '@/components/MiniBar';
import { useOperatorOner } from '@/modules/ai/hooks';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useUrunSecenekleri } from '@/modules/urun/hooks';
import { useAuthStore } from '@/store/authStore';

import { DurumGecis } from './DurumGecis';
import { useIsEmri, useKullaniciSecenekleri, useYorumEkle } from './hooks';
import { DurumEtiketi, OncelikRozet } from './rozetler';

const CIZELGE = ['acik', 'atandi', 'devam_ediyor', 'kapandi'];

function tarih(v?: string | null): string {
  return v ? dayjs(v).format('DD.MM.YYYY HH:mm') : '—';
}

export function IsEmriDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isemri:yaz'));
  const kullaniciOku = useAuthStore((s) => s.izinVar('kullanici:oku'));
  const aiOku = useAuthStore((s) => s.izinVar('ai:oku'));
  const acik = id != null;
  const { data: isEmri, isPending } = useIsEmri(id ?? 0);
  const { data: makineler } = useMakineSecenekleri();
  const { data: kullanicilar } = useKullaniciSecenekleri(kullaniciOku);
  const uretimOku = useAuthStore((s) => s.izinVar('uretim:oku'));
  const { data: urunler } = useUrunSecenekleri(uretimOku && isEmri?.urun_id != null);
  const yorumEkle = useYorumEkle();
  const operatorOner = useOperatorOner();
  const [yorum, setYorum] = useState('');

  const makineHarita = useMemo(() => new Map((makineler ?? []).map((m) => [m.id, m])), [makineler]);
  const kullaniciHarita = useMemo(
    () => new Map((kullanicilar ?? []).map((k) => [k.id, k])),
    [kullanicilar],
  );

  const atananAd = (kid?: number | null) => {
    if (kid == null) return t('isemri.atanmamis');
    return kullaniciHarita.get(kid)?.ad_soyad || `#${kid}`;
  };

  const yorumGonder = () => {
    if (!id || !yorum.trim()) return;
    yorumEkle.mutate({ id, metin: yorum.trim() }, { onSuccess: () => setYorum('') });
  };

  return (
    <Drawer
      open={acik}
      onClose={kapat}
      width={520}
      destroyOnHidden
      title={
        isEmri ? (
          <Space size={10} wrap>
            <span className="sayisal">{isEmri.kod}</span>
            <DurumEtiketi durum={isEmri.durum} />
            {isEmri.bakim_plani_id != null && (
              <Tag color="cyan" style={{ marginInlineEnd: 0 }}>
                {t('isemri.otomatik_bakim')}
              </Tag>
            )}
          </Space>
        ) : (
          t('menu.is_emirleri')
        )
      }
    >
      {isPending || !isEmri ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : (
        <>
          <Typography.Title level={4} style={{ marginTop: 0 }}>
            {isEmri.baslik}
          </Typography.Title>

          {yazabilir && (
            <div style={{ marginBottom: 16 }}>
              <DurumGecis isEmri={isEmri} boyut="middle" />
            </div>
          )}

          <Descriptions column={1} size="small" styles={{ label: { width: 130 } }}>
            <Descriptions.Item label={t('isemri.makine')}>
              {makineHarita.get(isEmri.makine_id)?.kod ?? `#${isEmri.makine_id}`}
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.oncelik')}>
              <OncelikRozet oncelik={isEmri.oncelik} />
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.atanan')}>
              {atananAd(isEmri.atanan_kullanici_id)}
            </Descriptions.Item>
            {isEmri.urun_id != null && (
              <Descriptions.Item label={t('isemri.urun')}>
                <span className="sayisal">
                  {(urunler ?? []).find((u) => u.id === isEmri.urun_id)?.kod ??
                    `#${isEmri.urun_id}`}
                  {isEmri.miktar != null ? ` × ${isEmri.miktar}` : ''}
                </span>
              </Descriptions.Item>
            )}
            {isEmri.lot_no && (
              <Descriptions.Item label={t('isemri.lot_no')}>
                <span className="sayisal">{isEmri.lot_no}</span>
              </Descriptions.Item>
            )}
            <Descriptions.Item label={t('isemri.hedef_tarih')}>
              {isEmri.hedef_tarih ? (
                <Space size={8}>
                  <span className="sayisal">{tarih(isEmri.hedef_tarih)}</span>
                  {dayjs(isEmri.hedef_tarih).isBefore(dayjs()) &&
                    isEmri.durum !== 'kapandi' &&
                    isEmri.durum !== 'iptal' && (
                      <Tag color="error" style={{ marginInlineEnd: 0 }}>
                        {t('isemri.sla_asildi')}
                      </Tag>
                    )}
                </Space>
              ) : (
                '—'
              )}
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.olusturma')}>
              {tarih(isEmri.olusturma_tarihi)}
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.kapanis')}>
              {tarih(isEmri.kapanis_tarihi)}
            </Descriptions.Item>
          </Descriptions>

          {isEmri.aciklama && (
            <Typography.Paragraph style={{ color: 'var(--metin-soluk)', marginTop: 4 }}>
              {isEmri.aciklama}
            </Typography.Paragraph>
          )}

          {aiOku && isEmri.durum !== 'kapandi' && isEmri.durum !== 'iptal' && (
            <>
              <div className="detay-bolum-baslik">
                {t('isemri.operator_oneri')}
                <Button
                  size="small"
                  icon={<ThunderboltOutlined />}
                  style={{ marginLeft: 10 }}
                  loading={operatorOner.isPending}
                  onClick={() => operatorOner.mutate({ is_emri_id: isEmri.id })}
                >
                  {t('isemri.operator_oner')}
                </Button>
              </div>
              {operatorOner.data && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 8 }}>
                  {operatorOner.data.length === 0 ? (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={t('isemri.operator_yok')}
                    />
                  ) : (
                    operatorOner.data.slice(0, 5).map((o) => (
                      <Tooltip key={o.personel_id} title={o.gerekce}>
                        <div
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 10,
                            padding: '7px 10px',
                            background: 'var(--yuzey-ust)',
                            border: '1px solid var(--kenarlik)',
                            borderRadius: 10,
                          }}
                        >
                          <span style={{ flex: 1, minWidth: 0, fontSize: 13, fontWeight: 600 }}>
                            {o.ad_soyad}
                            <span
                              style={{
                                marginLeft: 8,
                                fontWeight: 400,
                                fontSize: 12,
                                color: 'var(--metin-soluk)',
                              }}
                            >
                              {[o.departman, o.unvan].filter(Boolean).join(' · ')}
                            </span>
                          </span>
                          <MiniBar deger={o.skor} enBuyuk={1} renk="var(--mavi)" />
                          <span className="sayisal" style={{ fontSize: 12, width: 34 }}>
                            {(o.skor * 100).toFixed(0)}
                          </span>
                        </div>
                      </Tooltip>
                    ))
                  )}
                </div>
              )}
            </>
          )}

          <div className="detay-bolum-baslik">{t('ortak.durum_akisi')}</div>
          <DurumZamanCizelgesi
            adimlar={CIZELGE.map((d) => ({ anahtar: d, baslik: t(`isemri.durum_${d}`) }))}
            mevcut={isEmri.durum}
            olumsuz={{ anahtar: 'iptal', baslik: t('isemri.durum_iptal') }}
          />

          <Divider orientation="left" plain>
            {t('isemri.yorumlar')}
          </Divider>

          {isEmri.yorumlar && isEmri.yorumlar.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {isEmri.yorumlar.map((y) => (
                <div
                  key={y.id}
                  style={{
                    background: 'var(--yuzey-ust)',
                    border: '1px solid var(--kenarlik)',
                    borderRadius: 10,
                    padding: '10px 12px',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 8,
                      marginBottom: 4,
                    }}
                  >
                    <span style={{ fontSize: 12, fontWeight: 600 }}>{y.yazan_eposta ?? '—'}</span>
                    <span className="sayisal" style={{ fontSize: 11, color: 'var(--metin-soluk)' }}>
                      {tarih(y.olusturma_tarihi)}
                    </span>
                  </div>
                  <div style={{ color: 'var(--metin)' }}>{y.metin}</div>
                </div>
              ))}
            </div>
          ) : (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('isemri.yorum_yok')} />
          )}

          {yazabilir && (
            <div style={{ marginTop: 16 }}>
              <Input.TextArea
                rows={2}
                value={yorum}
                onChange={(e) => setYorum(e.target.value)}
                maxLength={2000}
                placeholder={t('isemri.yorum_yaz')}
              />
              <Button
                type="primary"
                style={{ marginTop: 10 }}
                loading={yorumEkle.isPending}
                disabled={!yorum.trim()}
                onClick={yorumGonder}
              >
                {t('isemri.yorum_ekle')}
              </Button>
            </div>
          )}
        </>
      )}
    </Drawer>
  );
}
