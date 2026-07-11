/**
 * Ticari & Doküman & Zekâ bölümü domain panelleri (persona panosu) — Ticari (sayaçlar + yaklaşan
 * sözleşmeler), Dokümanlar (DYS özeti), Zekâ (analitik/tahmin/rapor kısayolları; RBAC süzgeçli).
 */

import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { ArrowRightOutlined } from '@ant-design/icons';

import { useDysOzet } from '@/modules/dys/hooks';
import { useTicariOzet } from '@/modules/ticari/hooks';
import { useAuthStore } from '@/store/authStore';

import { AltBaslik, IstatSira, WidgetKabuk } from './ortak';

function boyutBicim(bayt: number): string {
  if (bayt < 1024) return `${bayt} B`;
  const kb = bayt / 1024;
  if (kb < 1024) return `${Math.round(kb)} KB`;
  const mb = kb / 1024;
  if (mb < 1024) return `${mb.toFixed(1)} MB`;
  return `${(mb / 1024).toFixed(2)} GB`;
}

function kalanRenk(gun: number): string {
  if (gun <= 7) return 'var(--hata)';
  if (gun <= 15) return 'var(--uyari)';
  return 'var(--metin-soluk)';
}

export function TicariPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useTicariOzet();
  const yaklasan = (data?.yaklasan_sozlesmeler ?? []).slice(0, 4);
  const s = data?.sayaclar;

  return (
    <WidgetKabuk
      bolum="menu.bolum_ticari"
      ikonAnahtar="ticari-pano"
      baslikAnahtari="pano.widget_ticari"
      yol="/ticari"
      yukleniyor={isPending}
      bos={s ? s.firma_sayisi === 0 && s.aktif_sozlesme === 0 : false}
      bosMetin={t('pano.ticari_bos')}
      genis
    >
      {s && (
        <>
          <IstatSira
            ogeler={[
              { anahtar: 'firma', deger: s.aktif_firma, etiket: t('pano.st_aktif_firma') },
              { anahtar: 'sozlesme', deger: s.aktif_sozlesme, etiket: t('pano.st_aktif_sozlesme') },
              {
                anahtar: 'yaklasan',
                deger: s.yaklasan_sozlesme,
                etiket: t('pano.st_yaklasan_sozlesme'),
                ton: s.yaklasan_sozlesme > 0 ? 'var(--uyari)' : undefined,
              },
              { anahtar: 'talep', deger: s.acik_talep, etiket: t('pano.st_acik_talep') },
            ]}
          />
          {yaklasan.length > 0 && (
            <div style={{ marginTop: 18 }}>
              <AltBaslik>{t('pano.yaklasan_sozlesmeler')}</AltBaslik>
              {yaklasan.map((y) => (
                <div key={y.id} className="widget-satir">
                  <div style={{ minWidth: 0 }}>
                    <div className="widget-satir-ad">{y.baslik}</div>
                    <div className="sayisal" style={{ fontSize: 12, color: 'var(--metin-soluk)' }}>
                      {y.kod}
                    </div>
                  </div>
                  <span
                    className="sayisal"
                    style={{
                      fontSize: 12.5,
                      color: kalanRenk(y.kalan_gun),
                      flexShrink: 0,
                      fontWeight: 600,
                    }}
                  >
                    {t('pano.kalan_gun', { gun: y.kalan_gun })}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </WidgetKabuk>
  );
}

export function DokumanPaneli() {
  const { t } = useTranslation();
  const { data, isPending } = useDysOzet();

  return (
    <WidgetKabuk
      bolum="menu.bolum_dokuman"
      ikonAnahtar="belgeler"
      baslikAnahtari="pano.widget_dokuman"
      yol="/belgeler"
      yukleniyor={isPending}
      bos={data ? data.toplam_belge === 0 : false}
      bosMetin={t('pano.dokuman_bos')}
    >
      {data && (
        <IstatSira
          ogeler={[
            { anahtar: 'belge', deger: data.toplam_belge, etiket: t('pano.st_toplam_belge') },
            {
              anahtar: 'surum',
              deger: data.bu_ay_surum,
              etiket: t('pano.st_bu_ay_surum'),
              ton: 'var(--hat-dokuman)',
            },
            { anahtar: 'boyut', deger: boyutBicim(data.toplam_boyut), etiket: t('pano.st_boyut') },
          ]}
        />
      )}
    </WidgetKabuk>
  );
}

export function ZekaPaneli() {
  const { t } = useTranslation();
  const izinler = useAuthStore((s) => s.izinler);

  const linkler = [
    izinler.has('analitik:oku') && {
      yol: '/analitik',
      ad: t('menu.analitik'),
      aciklama: t('pano.zeka_analitik'),
    },
    izinler.has('ai:oku') && {
      yol: '/tahminler',
      ad: t('menu.tahminler'),
      aciklama: t('pano.zeka_tahmin'),
    },
    izinler.has('rapor:oku') && {
      yol: '/raporlar',
      ad: t('menu.raporlar'),
      aciklama: t('pano.zeka_rapor'),
    },
  ].filter((x): x is { yol: string; ad: string; aciklama: string } => Boolean(x));

  return (
    <WidgetKabuk
      bolum="menu.bolum_zeka"
      ikonAnahtar="analitik"
      baslikAnahtari="pano.widget_zeka"
      yol={linkler[0]?.yol ?? '/analitik'}
      bos={linkler.length === 0}
      bosMetin={t('pano.zeka_bos')}
    >
      <div>
        {linkler.map((l) => (
          <Link key={l.yol} to={l.yol} className="widget-satir" style={{ textDecoration: 'none' }}>
            <div style={{ minWidth: 0 }}>
              <div className="widget-satir-ad">{l.ad}</div>
              <div style={{ fontSize: 12, color: 'var(--metin-soluk)' }}>{l.aciklama}</div>
            </div>
            <ArrowRightOutlined
              style={{ fontSize: 12, color: 'var(--metin-soluk)', flexShrink: 0 }}
            />
          </Link>
        ))}
      </div>
    </WidgetKabuk>
  );
}
