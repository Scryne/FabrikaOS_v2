/**
 * Üretim planı (S30, ADR-0049) — sonlu kapasite çizelgesi.
 *
 * Açık iş emirleri makine başına vardiya pencerelerine teslim tarihine göre (EDD) yerleştirilir;
 * planlamacı süreyi ve sırayı elle düzeltebilir. Ekran üç katman: Gantt (makine satırları, vardiya
 * bantları, "şimdi" çizgisi, duruma göre renkli çubuklar), günlük yük ızgarası ve erişilebilir iş
 * sırası tablosu. Çubuk tıklanınca/Enter ile plan girdisi çekmecesi açılır.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
  AlertOutlined,
  ClockCircleOutlined,
  FieldTimeOutlined,
  ScheduleOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  DatePicker,
  Descriptions,
  Drawer,
  Empty,
  Form,
  InputNumber,
  Segmented,
  Select,
  Skeleton,
  Space,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { type Dayjs } from 'dayjs';

import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';
import { DurumEtiketi, OncelikRozet } from '@/modules/isemri/rozetler';
import { useSimdi } from '@/modules/ortak/useSimdi';
import { useMakineSecenekleri } from '@/modules/uretim/hooks';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI } from '@/tema/modulKimlik';

import { type CizelgeIsi, type MakineCizelgesi, useCizelge, usePlanGirdisi } from './hooks';
import { isDurumu, sureMetni, yerlestir, yukOrani, yukTonu, type IsDurumu } from './zamanCizelgesi';

const HAT = BOLUM_RENGI['menu.bolum_uretim'];
const UFUKLAR = [3, 7, 14] as const;
const DURUM_RENK: Record<IsDurumu, string> = {
  zamaninda: 'success',
  sira_gecikmesi: 'warning',
  kapasite_asimi: 'error',
  sigmadi: 'error',
};

type Satir = CizelgeIsi & { makine: MakineCizelgesi };

function anMetni(v: string | null | undefined): string {
  return v ? dayjs(v).format('DD.MM HH:mm') : '—';
}

export function UretimPlani() {
  const { t, i18n } = useTranslation();
  const simdi = useSimdi();
  const izinVar = useAuthStore((s) => s.izinVar);
  const yaz = izinVar('planlama:yaz');
  const [ilkGun, setIlkGun] = useState<Dayjs>(() => dayjs().startOf('day'));
  // Varsayılan 3 gün: vardiya içi işler (saatler) çubuk olarak okunur kalır; 7/14 gün yükü gösterir.
  const [gun, setGun] = useState<number>(3);
  const gunAdi = useMemo(
    () => new Intl.DateTimeFormat(i18n.language, { weekday: 'short' }),
    [i18n.language],
  );
  const [makineId, setMakineId] = useState<number | undefined>();
  const [secili, setSecili] = useState<Satir | null>(null);

  const cizelge = useCizelge({ baslangic: ilkGun.format('YYYY-MM-DD'), gun, makineId });
  const makineler = useMakineSecenekleri();
  const veri = cizelge.data;

  const eksen = useMemo(() => {
    const bas = ilkGun.valueOf();
    const bit = ilkGun.add(gun, 'day').valueOf();
    return { bas, bit, gunler: Array.from({ length: gun }, (_, i) => ilkGun.add(i, 'day')) };
  }, [ilkGun, gun]);

  const satirlar: Satir[] = useMemo(
    () => (veri?.makineler ?? []).flatMap((m) => m.isler.map((i) => ({ ...i, makine: m }))),
    [veri],
  );

  const durumMetni = (i: CizelgeIsi): string => {
    const d = isDurumu(i);
    if (d === 'zamaninda') return t('planlama.durum_zamaninda');
    if (d === 'sigmadi') return t('planlama.durum_sigmadi');
    const gecikme = sureMetni(i.gecikme_dk);
    return d === 'kapasite_asimi'
      ? t('planlama.durum_kapasite_asimi', { sure: gecikme })
      : t('planlama.durum_sira_gecikmesi', { sure: gecikme });
  };

  const simdiKonum = yerlestir(simdi, simdi + 1, eksen.bas, eksen.bit, 0);

  const kolonlar: ColumnsType<Satir> = [
    {
      title: t('planlama.makine'),
      key: 'makine',
      render: (_v, s) => <span className="sayisal">{s.makine.kod}</span>,
      width: 110,
    },
    {
      title: t('planlama.is_emri'),
      key: 'is',
      render: (_v, s) => (
        <span>
          <Link to={`/is-emirleri?kayit=${s.is_emri_id}`} className="sayisal">
            {s.kod}
          </Link>
          <span className="varlik-alt" style={{ display: 'block' }}>
            {s.baslik}
          </span>
        </span>
      ),
    },
    {
      title: t('isemri.oncelik'),
      dataIndex: 'oncelik',
      key: 'oncelik',
      render: (v: string) => <OncelikRozet oncelik={v} />,
      responsive: ['md'],
    },
    {
      title: t('planlama.sure'),
      key: 'sure',
      align: 'right',
      render: (_v, s) => (
        <span>
          <span className="sayisal">{sureMetni(s.sure_dk)}</span>
          {s.sure_kaynagi !== 'tahmin' && (
            <Tag
              variant="filled"
              color={s.sure_kaynagi === 'varsayilan' ? 'warning' : 'blue'}
              style={{ marginLeft: 6, marginRight: 0 }}
            >
              {t(`planlama.kaynak_${s.sure_kaynagi}`)}
            </Tag>
          )}
        </span>
      ),
    },
    {
      title: t('planlama.baslangic'),
      dataIndex: 'baslangic',
      key: 'baslangic',
      render: (v: string | null) => <span className="sayisal">{anMetni(v)}</span>,
    },
    {
      title: t('planlama.bitis'),
      dataIndex: 'bitis',
      key: 'bitis',
      render: (v: string | null) => <span className="sayisal">{anMetni(v)}</span>,
    },
    {
      title: t('planlama.hedef'),
      dataIndex: 'hedef_tarih',
      key: 'hedef',
      render: (v: string | null) => <span className="sayisal">{anMetni(v)}</span>,
      responsive: ['lg'],
    },
    {
      title: t('planlama.durum'),
      key: 'durum',
      render: (_v, s) => (
        <Tag color={DURUM_RENK[isDurumu(s)]} variant="filled">
          {durumMetni(s)}
        </Tag>
      ),
    },
  ];

  const o = veri?.ozet;

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('menu.uretim_plani')}
        alt={t('planlama.alt')}
        sag={
          <Space wrap size={8}>
            <DatePicker
              value={ilkGun}
              onChange={(d) => d && setIlkGun(d.startOf('day'))}
              allowClear={false}
              format="DD.MM.YYYY"
              aria-label={t('planlama.ilk_gun')}
            />
            <Segmented
              value={gun}
              onChange={(v) => setGun(Number(v))}
              options={UFUKLAR.map((u) => ({ value: u, label: t('planlama.gun_n', { n: u }) }))}
              aria-label={t('planlama.ufuk')}
            />
            <Select
              allowClear
              placeholder={t('planlama.tum_makineler')}
              value={makineId}
              onChange={(v) => setMakineId(v)}
              style={{ minWidth: 180 }}
              loading={makineler.isPending}
              aria-label={t('planlama.makine')}
              options={(makineler.data ?? []).map((m) => ({
                value: m.id,
                label: `${m.kod} · ${m.ad}`,
              }))}
            />
          </Space>
        }
      />
      <OzetSerit
        renk={HAT}
        yukleniyor={cizelge.isPending}
        metrikler={
          o
            ? [
                {
                  anahtar: 'is',
                  baslik: t('planlama.planlanan_is'),
                  deger: String(o.is_sayisi),
                  ikon: <ScheduleOutlined />,
                },
                {
                  anahtar: 'geciken',
                  baslik: t('planlama.geciken'),
                  deger: String(o.geciken),
                  ikon: <ClockCircleOutlined />,
                  olumlu: o.geciken === 0,
                },
                {
                  anahtar: 'asim',
                  baslik: t('planlama.kapasite_asimi'),
                  deger: String(o.kapasite_asimi),
                  ikon: <AlertOutlined />,
                  olumlu: o.kapasite_asimi === 0,
                },
                {
                  anahtar: 'varsayilan',
                  baslik: t('planlama.suresi_bilinmeyen'),
                  deger: String(o.varsayilan_sure),
                  ikon: <FieldTimeOutlined />,
                  olumlu: o.varsayilan_sure === 0,
                },
              ]
            : []
        }
      />
      <div style={{ height: 16 }} />
      {veri?.varsayilan_vardiya && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title={t('planlama.varsayilan_vardiya')}
          description={<Link to="/vardiyalar">{t('planlama.vardiya_tanimla')}</Link>}
        />
      )}
      {o && o.kapasite_asimi > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          title={t('planlama.asim_baslik', { n: o.kapasite_asimi })}
          description={t('planlama.asim_aciklama')}
        />
      )}

      <Card title={t('planlama.gantt')} styles={{ body: { padding: 0 } }} extra={<GanttLejant />}>
        {cizelge.isPending ? (
          <div style={{ padding: 20 }}>
            <Skeleton active />
          </div>
        ) : !veri || veri.makineler.length === 0 ? (
          <Empty style={{ padding: 32 }} description={t('planlama.bos')} />
        ) : (
          <div className="gantt-kaydir">
            <div className="gantt" style={{ minWidth: 200 + gun * (gun > 7 ? 90 : 130) }}>
              <div className="gantt-satir gantt-ust">
                <div className="gantt-sol">{t('planlama.makine')}</div>
                <div className="gantt-iz">
                  {eksen.gunler.map((g, i) => (
                    <div
                      key={g.valueOf()}
                      className={`gantt-gun${g.isSame(dayjs(), 'day') ? ' bugun' : ''}`}
                      style={{ left: `${(i / gun) * 100}%`, width: `${100 / gun}%` }}
                    >
                      <span>{gunAdi.format(g.toDate())}</span>
                      <span className="sayisal">{g.format('DD.MM')}</span>
                    </div>
                  ))}
                </div>
              </div>
              {veri.makineler.map((m) => {
                const plan = m.gunluk_yuk.reduce((a, g) => a + g.plan_dk, 0);
                const kap = m.gunluk_yuk.reduce((a, g) => a + g.kapasite_dk, 0);
                const oran = yukOrani(plan, kap);
                return (
                  <div key={m.makine_id} className="gantt-satir">
                    <div className="gantt-sol">
                      <span className="sayisal gantt-kod">{m.kod}</span>
                      <span className="gantt-ad">{m.ad}</span>
                      <span className={`gantt-yuk ton-${yukTonu(oran)}`}>
                        {oran === null
                          ? '—'
                          : t('planlama.yuk_yuzde', { n: Math.round(oran * 100) })}
                      </span>
                    </div>
                    <div
                      className="gantt-iz"
                      role="list"
                      aria-label={t('planlama.makine_isleri', { makine: `${m.kod} ${m.ad}` })}
                    >
                      {veri.pencereler.map((p) => {
                        const y = yerlestir(
                          Date.parse(p.baslangic),
                          Date.parse(p.bitis),
                          eksen.bas,
                          eksen.bit,
                          0,
                        );
                        return (
                          y && (
                            <div
                              key={p.baslangic}
                              className="gantt-vardiya"
                              style={{ left: `${y.sol}%`, width: `${y.genislik}%` }}
                            />
                          )
                        );
                      })}
                      {eksen.gunler.slice(1).map((g, i) => (
                        <div
                          key={g.valueOf()}
                          className="gantt-ayrac"
                          style={{ left: `${((i + 1) / gun) * 100}%` }}
                        />
                      ))}
                      {simdiKonum && (
                        <div className="gantt-simdi" style={{ left: `${simdiKonum.sol}%` }} />
                      )}
                      {m.isler.flatMap((i) => {
                        const d = isDurumu(i);
                        const satir = { ...i, makine: m };
                        return i.parcalar.map((p, pi) => {
                          const y = yerlestir(
                            Date.parse(p.baslangic),
                            Date.parse(p.bitis),
                            eksen.bas,
                            eksen.bit,
                          );
                          if (!y) return null;
                          const ozet = `${i.kod} · ${i.baslik} · ${anMetni(p.baslangic)}–${dayjs(p.bitis).format('HH:mm')} · ${durumMetni(i)}`;
                          return (
                            <Tooltip
                              key={`${i.is_emri_id}-${pi}`}
                              title={
                                <div className="gantt-ipucu">
                                  <strong>
                                    {i.kod} · {i.baslik}
                                  </strong>
                                  <span>
                                    {anMetni(i.baslangic)} → {anMetni(i.bitis)} ·{' '}
                                    {sureMetni(i.sure_dk)}
                                  </span>
                                  <span>
                                    {t('planlama.hedef')}: {anMetni(i.hedef_tarih)}
                                  </span>
                                  <span>{durumMetni(i)}</span>
                                </div>
                              }
                            >
                              <button
                                type="button"
                                role="listitem"
                                className={`gantt-cubuk durum-${d}${pi > 0 ? ' devam' : ''}`}
                                style={{ left: `${y.sol}%`, width: `${y.genislik}%` }}
                                aria-label={ozet}
                                onClick={() => setSecili(satir)}
                              >
                                <span>{i.kod}</span>
                              </button>
                            </Tooltip>
                          );
                        });
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </Card>

      {veri && veri.makineler.length > 0 && (
        <>
          <div style={{ height: 20 }} />
          <Card title={t('planlama.gunluk_yuk')} styles={{ body: { padding: 0 } }}>
            <div className="gantt-kaydir">
              <table className="yuk-izgara">
                <thead>
                  <tr>
                    <th scope="col">{t('planlama.makine')}</th>
                    {eksen.gunler.map((g) => (
                      <th key={g.valueOf()} scope="col" className="sayisal">
                        {gunAdi.format(g.toDate())} {g.format('DD.MM')}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {veri.makineler.map((m) => {
                    const gunluk = new Map(m.gunluk_yuk.map((g) => [g.gun, g]));
                    return (
                      <tr key={m.makine_id}>
                        <th scope="row" className="sayisal">
                          {m.kod}
                        </th>
                        {eksen.gunler.map((g) => {
                          const y = gunluk.get(g.format('YYYY-MM-DD'));
                          const oran = y ? yukOrani(y.plan_dk, y.kapasite_dk) : null;
                          return (
                            <td
                              key={g.valueOf()}
                              className={`ton-${yukTonu(oran)}`}
                              title={
                                y
                                  ? t('planlama.yuk_ipucu', {
                                      plan: sureMetni(y.plan_dk),
                                      kapasite: sureMetni(y.kapasite_dk),
                                    })
                                  : t('planlama.vardiya_yok')
                              }
                            >
                              <span className="sayisal">
                                {oran === null ? '—' : `%${Math.round(oran * 100)}`}
                              </span>
                            </td>
                          );
                        })}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
          <div style={{ height: 20 }} />
          <Card title={t('planlama.is_sirasi')} styles={{ body: { padding: 0 } }}>
            <Table<Satir>
              rowKey="is_emri_id"
              size="middle"
              columns={kolonlar}
              dataSource={satirlar}
              pagination={satirlar.length > 20 ? { pageSize: 20 } : false}
              scroll={{ x: 'max-content' }}
              onRow={(s) => ({
                onClick: () => setSecili(s),
                style: { cursor: 'pointer' },
              })}
            />
          </Card>
        </>
      )}

      <PlanCekmecesi
        satir={secili}
        yaz={yaz}
        durumMetni={durumMetni}
        kapat={() => setSecili(null)}
      />
    </SayfaKapsayici>
  );
}

function GanttLejant() {
  const { t } = useTranslation();
  return (
    <ul className="gantt-lejant" aria-label={t('planlama.lejant')}>
      {(['zamaninda', 'sira_gecikmesi', 'kapasite_asimi'] as const).map((d) => (
        <li key={d}>
          <span className={`gantt-lejant-renk durum-${d}`} aria-hidden />
          {t(`planlama.lejant_${d}`)}
        </li>
      ))}
      <li>
        <span className="gantt-lejant-renk vardiya" aria-hidden />
        {t('planlama.lejant_vardiya')}
      </li>
    </ul>
  );
}

function PlanCekmecesi({
  satir,
  yaz,
  durumMetni,
  kapat,
}: {
  satir: Satir | null;
  yaz: boolean;
  durumMetni: (i: CizelgeIsi) => string;
  kapat: () => void;
}) {
  const { t } = useTranslation();
  const [form] = Form.useForm<{ sure_dk: number | null; elle_sira: number | null }>();
  const kaydet = usePlanGirdisi();

  const gonder = (govde: { sure_dk?: number | null; elle_sira?: number | null }) => {
    if (!satir) return;
    kaydet.mutate(
      {
        isEmriId: satir.is_emri_id,
        govde: { sure_dk: govde.sure_dk ?? null, elle_sira: govde.elle_sira ?? null },
      },
      { onSuccess: kapat },
    );
  };

  return (
    <Drawer
      open={satir !== null}
      onClose={kapat}
      size={420}
      title={satir ? `${satir.kod} · ${satir.baslik}` : ''}
      destroyOnHidden
      afterOpenChange={(acik) => {
        if (acik && satir) {
          form.setFieldsValue({
            sure_dk: satir.sure_kaynagi === 'elle' ? satir.sure_dk : null,
            elle_sira: satir.elle_sira ?? null,
          });
        }
      }}
    >
      {satir && (
        <>
          <Descriptions column={1} size="small" bordered style={{ marginBottom: 20 }}>
            <Descriptions.Item label={t('planlama.makine')}>
              {satir.makine.kod} · {satir.makine.ad}
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.durum')}>
              <DurumEtiketi durum={satir.durum} />
            </Descriptions.Item>
            <Descriptions.Item label={t('isemri.oncelik')}>
              <OncelikRozet oncelik={satir.oncelik} />
            </Descriptions.Item>
            <Descriptions.Item label={t('planlama.plan')}>
              <span className="sayisal">
                {anMetni(satir.baslangic)} → {anMetni(satir.bitis)}
              </span>
              {satir.parcalar.length > 1 && (
                <span className="varlik-alt" style={{ display: 'block' }}>
                  {t('planlama.parcali', { n: satir.parcalar.length })}
                </span>
              )}
            </Descriptions.Item>
            <Descriptions.Item label={t('planlama.hedef')}>
              <span className="sayisal">{anMetni(satir.hedef_tarih)}</span>
            </Descriptions.Item>
            <Descriptions.Item label={t('planlama.sure')}>
              <span className="sayisal">{sureMetni(satir.sure_dk)}</span>{' '}
              <span className="varlik-alt">
                {t(`planlama.kaynak_aciklama_${satir.sure_kaynagi}`)}
              </span>
            </Descriptions.Item>
            <Descriptions.Item label={t('planlama.durum')}>
              <Tag color={DURUM_RENK[isDurumu(satir)]} variant="filled">
                {durumMetni(satir)}
              </Tag>
            </Descriptions.Item>
          </Descriptions>
          {yaz ? (
            <Form form={form} layout="vertical" onFinish={gonder} requiredMark={false}>
              <Form.Item
                name="sure_dk"
                label={t('planlama.elle_sure')}
                extra={t('planlama.elle_sure_ipucu')}
              >
                <InputNumber min={1} max={86400} step={15} suffix="dk" style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item
                name="elle_sira"
                label={t('planlama.elle_sira')}
                extra={t('planlama.elle_sira_ipucu')}
              >
                <InputNumber min={1} max={10000} style={{ width: '100%' }} />
              </Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={kaydet.isPending}>
                  {t('planlama.kaydet')}
                </Button>
                <Button
                  onClick={() => gonder({})}
                  disabled={satir.sure_kaynagi !== 'elle' && satir.elle_sira == null}
                  loading={kaydet.isPending}
                >
                  {t('planlama.sifirla')}
                </Button>
              </Space>
            </Form>
          ) : (
            <Alert type="info" showIcon title={t('planlama.yalniz_okuma')} />
          )}
        </>
      )}
    </Drawer>
  );
}
