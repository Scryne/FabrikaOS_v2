/**
 * Talep detayı (Drawer) — KPI şeridi (öncelik / tür / atanan) + künye (Descriptions) +
 * **durum zaman çizelgesi** (açık→inceleniyor→çözüldü→kapandı; iptal olumsuz terminal) +
 * atama (``talep:yaz``) + durum geçiş butonları (``gecerliHedefler`` ∩ ``talep:yaz``).
 *
 * Okunur adlar mevcut izin kapılarından çözülür (yeni yetki açılmaz): atanan kişi
 * ``kullanici:oku`` ile kullanıcı listesinden, firma ``crm:oku`` ile firma kaydından. İzin yoksa
 * kayıt numarası gösterilir ve atama sayısal kullanıcı numarasıyla yapılır (önceki davranış).
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Descriptions, Drawer, InputNumber, Select, Space } from 'antd';

import { DetayIstatSira, DurumZamanCizelgesi } from '@/components/DetayOgeleri';
import { useFirma } from '@/modules/crm/hooks';
import { useKullaniciSecenekleri } from '@/modules/isemri/hooks';
import { useAuthStore } from '@/store/authStore';
import { RENKLER } from '@/tema/tema';

import { gecerliHedefler } from './durum';
import { useTalep, useTalepDurum, useTalepGuncelle } from './hooks';
import { TalepDurumEtiketi } from './rozetler';

const CIZELGE = ['acik', 'inceleniyor', 'cozuldu', 'kapandi'];
const ONCELIK_RENK: Record<string, string> = {
  dusuk: RENKLER.metinSoluk,
  orta: RENKLER.mavi,
  yuksek: RENKLER.uyari,
};

export function TalepDetay({ id, kapat }: { id: number | null; kapat: () => void }) {
  const { t } = useTranslation();
  const { data: talep } = useTalep(id ?? 0);
  const durumMut = useTalepDurum();
  const guncelle = useTalepGuncelle();
  const yazabilir = useAuthStore((s) => s.izinVar('talep:yaz'));
  const kullaniciOku = useAuthStore((s) => s.izinVar('kullanici:oku'));
  const crmOku = useAuthStore((s) => s.izinVar('crm:oku'));
  const kullaniciSorgu = useKullaniciSecenekleri(kullaniciOku && id != null);
  const kullanicilar = kullaniciSorgu.data;
  const firmaSorgu = useFirma(crmOku ? (talep?.firma_id ?? 0) : 0);
  const [atanan, setAtanan] = useState<number | null>(null);

  const kullaniciHarita = useMemo(
    () => new Map((kullanicilar ?? []).map((k) => [k.id, k])),
    [kullanicilar],
  );
  const kullaniciAdi = (kid: number) => {
    const k = kullaniciHarita.get(kid);
    // Ad çözülürken numara yanıp sönmesin; çözülemezse (izin yok/kayıt yok) kayıt numarası.
    if (!k && kullaniciSorgu.isFetching) return '…';
    return k?.ad_soyad || k?.eposta || `#${kid}`;
  };

  const hedefler = talep && yazabilir ? gecerliHedefler(talep.durum) : [];

  const ata = async () => {
    if (!talep || atanan == null) return;
    await guncelle.mutateAsync({ id: talep.id, govde: { atanan_kullanici_id: atanan } });
    setAtanan(null);
  };

  return (
    <Drawer
      open={id != null}
      onClose={kapat}
      size={620}
      destroyOnHidden
      title={<span className="sayisal">{talep?.kod}</span>}
      extra={talep && <TalepDurumEtiketi durum={talep.durum} />}
    >
      {talep && (
        <>
          <h3 style={{ margin: '0 0 16px', fontWeight: 600 }}>{talep.baslik}</h3>

          <DetayIstatSira
            ogeler={[
              {
                anahtar: 'oncelik',
                deger: t(`talep.oncelik_${talep.oncelik}`),
                etiket: t('talep.oncelik'),
                ton: ONCELIK_RENK[talep.oncelik],
              },
              { anahtar: 'tur', deger: t(`talep.tur_${talep.tur}`), etiket: t('talep.tur') },
              {
                anahtar: 'atanan',
                deger: talep.atanan_kullanici_id ? kullaniciAdi(talep.atanan_kullanici_id) : '—',
                etiket: t('talep.atanan'),
              },
            ]}
          />

          {(talep.firma_id || talep.aciklama) && (
            <>
              <div className="detay-bolum-baslik">{t('ortak.kunye')}</div>
              <Descriptions column={1} size="small" styles={{ label: { width: 130 } }}>
                {talep.firma_id && (
                  <Descriptions.Item label={t('talep.firma')}>
                    {firmaSorgu.data?.ad ?? (firmaSorgu.isFetching ? '…' : `#${talep.firma_id}`)}
                  </Descriptions.Item>
                )}
                {talep.aciklama && (
                  <Descriptions.Item label={t('talep.aciklama')}>
                    {talep.aciklama}
                  </Descriptions.Item>
                )}
              </Descriptions>
            </>
          )}

          <div className="detay-bolum-baslik">{t('ortak.durum_akisi')}</div>
          <DurumZamanCizelgesi
            adimlar={CIZELGE.map((d) => ({ anahtar: d, baslik: t(`talep.asama_${d}`) }))}
            mevcut={talep.durum}
            olumsuz={{ anahtar: 'iptal', baslik: t('talep.asama_iptal') }}
          />

          {yazabilir && (
            <Space style={{ marginTop: 20 }} wrap>
              {kullaniciOku ? (
                <Select
                  showSearch
                  optionFilterProp="label"
                  style={{ minWidth: 220 }}
                  value={atanan ?? undefined}
                  onChange={(v: number) => setAtanan(v)}
                  placeholder={t('talep.atanan')}
                  aria-label={t('talep.atanan')}
                  options={(kullanicilar ?? [])
                    .filter((k) => k.aktif)
                    .map((k) => ({ value: k.id, label: k.ad_soyad || k.eposta }))}
                />
              ) : (
                <InputNumber
                  min={1}
                  value={atanan ?? undefined}
                  onChange={(v) => setAtanan(v)}
                  placeholder={t('talep.atanan_id')}
                />
              )}
              <Button
                loading={guncelle.isPending}
                onClick={() => void ata()}
                disabled={atanan == null}
              >
                {t('talep.ata')}
              </Button>
            </Space>
          )}

          {hedefler.length > 0 && (
            <Space style={{ marginTop: 12 }} wrap>
              {hedefler.map((h) => (
                <Button
                  key={h}
                  type={h === 'cozuldu' || h === 'kapandi' ? 'primary' : 'default'}
                  danger={h === 'iptal'}
                  loading={durumMut.isPending}
                  onClick={() => void durumMut.mutateAsync({ id: talep.id, durum: h })}
                >
                  {t(`talep.durum_${h}`)}
                </Button>
              ))}
            </Space>
          )}
        </>
      )}
    </Drawer>
  );
}
