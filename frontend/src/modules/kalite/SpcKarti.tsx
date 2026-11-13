/**
 * SPC kontrol kartı (S26-A): X̄ ve R kartları, Western Electric ihlalleri, Cp/Cpk, ölçüm girişi.
 *
 * Kontrol limiti (sürecin sesi) ile tolerans (müşterinin isteği) aynı grafikte ayrı renktedir;
 * ikisi karıştırılmasın. Limitler sabitlenmemişse her ölçümle yeniden hesaplanır — ekran bunu
 * açıkça söyler ve faz-I bitince "limitleri sabitle" önerir.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';
import { LockOutlined } from '@ant-design/icons';
import { Alert, App, Button, Card, Form, InputNumber, Popconfirm, Table, Tag } from 'antd';

import { EGrafik } from '@/components/grafik/EGrafik';
import { kontrolKartiSecenek } from '@/components/grafik/grafikSecenek';
import { OzetSerit } from '@/components/OzetSerit';
import { sayiSabit } from '@/i18n/sayi';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { useAuthStore } from '@/store/authStore';

import { type SpcIhlal, useLimitSabitle, useOlcumGir, useSpcKart } from './spcHooks';

const f = (v: number | null | undefined, d = 3) =>
  v === null || v === undefined ? '—' : sayiSabit(v, d);

export function SpcKarti() {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const id = Number(useParams().id);
  const yazabilir = useAuthStore((s) => s.izinVar('kalite:yaz'));
  const kart = useSpcKart(id);
  const k = kart.data;
  const olc = useOlcumGir(id, k?.plan_id);
  const sabitle = useLimitSabitle(id);
  const [form] = Form.useForm<{ degerler: (number | null)[] }>();
  const [formAnahtari, setFormAnahtari] = useState(0);

  const ihlalIndeksleri = useMemo(() => {
    const x = new Set<number>();
    const r = new Set<number>();
    for (const i of k?.ihlaller ?? []) (i.kart === 'xbar' ? x : r).add(i.indeks);
    return { x, r };
  }, [k]);

  const secenekler = useMemo(() => {
    if (!k?.limitler) return null;
    const siralar = k.noktalar.map((n) => n.sira);
    return {
      xbar: kontrolKartiSecenek({
        siralar,
        degerler: k.noktalar.map((n) => n.xbar),
        cl: k.limitler.xbar_cl,
        ucl: k.limitler.xbar_ucl,
        lcl: k.limitler.xbar_lcl,
        ihlalIndeksleri: ihlalIndeksleri.x,
        tolerans: { alt: k.alt_tolerans, ust: k.ust_tolerans },
        etiketler: { cl: 'X̿', ucl: 'ÜKL', lcl: 'AKL', alt: 'ASL', ust: 'ÜSL' },
      }),
      r: kontrolKartiSecenek({
        siralar,
        degerler: k.noktalar.map((n) => n.r),
        cl: k.limitler.r_cl,
        ucl: k.limitler.r_ucl,
        lcl: k.limitler.r_lcl,
        ihlalIndeksleri: ihlalIndeksleri.r,
        etiketler: { cl: 'R̄', ucl: 'ÜKL', lcl: 'AKL' },
      }),
    };
  }, [k, ihlalIndeksleri]);

  const ihlalSatirlari = (k?.ihlaller ?? [])
    .map((i) => ({ ...i, sira: k?.noktalar[i.indeks]?.sira ?? i.indeks + 1 }))
    .sort((a, b) => b.sira - a.sira);

  const gonder = (v: { degerler: (number | null)[] }) => {
    const degerler = v.degerler.map(Number);
    olc.mutate(
      { degerler },
      {
        onSuccess: (s) => {
          if (s.ihlaller.length)
            message.warning(t('spc.olcum_ihlalli', { sira: s.sira, adet: s.ihlaller.length }));
          else message.success(t('spc.olcum_kaydedildi', { sira: s.sira }));
          form.resetFields();
          setFormAnahtari((x) => x + 1);
        },
      },
    );
  };

  const cpkRenk = (v: number | null | undefined) =>
    v === null || v === undefined ? undefined : v >= 1.33;

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={k ? `${k.ad}` : t('spc.kart')}
        alt={
          k ? (
            <span>
              <Link to={`/kontrol-planlari/${k.plan_id}`}>{t('spc.plana_don')}</Link>
              <span className="sayisal">
                {' · '}
                {t('spc.tolerans')} {f(k.alt_tolerans)} – {f(k.ust_tolerans)} {k.birim} · n ={' '}
                {k.alt_grup_boyutu}
              </span>
            </span>
          ) : undefined
        }
        sag={
          yazabilir && k && !k.limitler_sabit && k.noktalar.length >= 2 ? (
            <Popconfirm
              title={t('spc.sabitle_soru', { adet: k.noktalar.length })}
              okText={t('spc.sabitle')}
              cancelText={t('ortak.vazgec')}
              onConfirm={() =>
                sabitle.mutate(undefined, { onSuccess: () => message.success(t('spc.sabitlendi')) })
              }
            >
              <Button icon={<LockOutlined />} loading={sabitle.isPending}>
                {t('spc.sabitle')}
              </Button>
            </Popconfirm>
          ) : k?.limitler_sabit ? (
            <Tag color="green" icon={<LockOutlined />}>
              {t('spc.limitler_sabit')}
            </Tag>
          ) : null
        }
      />

      {k && (
        <OzetSerit
          metrikler={[
            { anahtar: 'n', baslik: t('spc.alt_grup_sayisi'), deger: String(k.noktalar.length) },
            { anahtar: 'xbar', baslik: 'X̿', deger: f(k.limitler?.xbar_cl), birim: k.birim },
            {
              anahtar: 'cp',
              baslik: 'Cp',
              deger: f(k.yetenek?.cp, 2),
              olumlu: cpkRenk(k.yetenek?.cp),
            },
            {
              anahtar: 'cpk',
              baslik: 'Cpk',
              deger: f(k.yetenek?.cpk, 2),
              olumlu: cpkRenk(k.yetenek?.cpk),
            },
            {
              anahtar: 'ihlal',
              baslik: t('spc.ihlal_sayisi'),
              deger: String(k.ihlaller.length),
              olumlu: k.ihlaller.length === 0,
            },
          ]}
        />
      )}

      {(k?.uyarilar ?? []).map((u) => (
        <Alert key={u} type="info" showIcon className="aktarim-uyari" title={u} />
      ))}

      <div className="spc-duzen">
        <div className="spc-kartlar">
          <Card title={t('spc.xbar_karti')} loading={kart.isPending}>
            {secenekler ? (
              <EGrafik secenek={secenekler.xbar} yukseklik={260} etiket={t('spc.xbar_karti')} />
            ) : (
              <p className="varlik-alt">{t('spc.veri_yetersiz')}</p>
            )}
          </Card>
          <Card title={t('spc.r_karti')} loading={kart.isPending}>
            {secenekler ? (
              <EGrafik secenek={secenekler.r} yukseklik={200} etiket={t('spc.r_karti')} />
            ) : (
              <p className="varlik-alt">{t('spc.veri_yetersiz')}</p>
            )}
          </Card>
        </div>
        <div className="spc-yan">
          {yazabilir && k && (
            <Card title={t('spc.olcum_gir')}>
              <Form key={formAnahtari} form={form} layout="vertical" onFinish={gonder}>
                <div className="spc-olcum-girdileri">
                  {Array.from({ length: k.alt_grup_boyutu }, (_, i) => (
                    <Form.Item
                      key={i}
                      name={['degerler', i]}
                      label={`${i + 1}.`}
                      rules={[{ required: true, message: t('spc.deger_gerekli') }]}
                    >
                      <InputNumber
                        style={{ width: '100%' }}
                        step={0.001}
                        decimalSeparator=","
                        aria-label={t('spc.olcum_n', { n: i + 1 })}
                      />
                    </Form.Item>
                  ))}
                </div>
                <Button type="primary" htmlType="submit" loading={olc.isPending} block>
                  {t('spc.kaydet_alt_grup')}
                </Button>
              </Form>
            </Card>
          )}
          <Card title={t('spc.ihlaller')}>
            {ihlalSatirlari.length === 0 ? (
              <p className="varlik-alt">{t('spc.ihlal_yok')}</p>
            ) : (
              <Table<SpcIhlal & { sira: number }>
                size="small"
                rowKey={(i) => `${i.kart}-${i.kural}-${i.indeks}`}
                pagination={{ pageSize: 8, hideOnSinglePage: true }}
                dataSource={ihlalSatirlari}
                columns={[
                  { title: '#', dataIndex: 'sira', width: 48, className: 'sayisal' },
                  {
                    title: t('spc.kural'),
                    key: 'kural',
                    render: (_v, i) => (
                      <span>
                        <Tag color={i.kart === 'xbar' ? 'red' : 'orange'}>
                          {i.kart === 'xbar' ? 'X̄' : 'R'} · {i.kural}
                        </Tag>
                        <span className="varlik-alt">{t(`spc.kural_${i.kural}`)}</span>
                      </span>
                    ),
                  },
                ]}
              />
            )}
          </Card>
        </div>
      </div>
    </SayfaKapsayici>
  );
}
