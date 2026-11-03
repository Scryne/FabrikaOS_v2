/**
 * Personel detayının S26-B parçaları (ADR-0044): yıllık izin bakiyesi sekmesi, yönetici seçici,
 * işe giriş / çıkış kontrol listeleri. Bakiye yalnız işe giriş tarihi varsa hesaplanır; yoksa
 * ekran bunu söyler (onayda kapı da uygulanmaz).
 */

import { useTranslation } from 'react-i18next';
import { CheckCircleFilled, LoginOutlined, LogoutOutlined } from '@ant-design/icons';
import { Alert, Button, Checkbox, Empty, Progress, Select, Space, Table, Tag } from 'antd';

import { useAuthStore } from '@/store/authStore';

import type { Personel } from './hooks';
import {
  type KontrolListesi,
  useIzinBakiyesi,
  useKontrolListeleri,
  useKontrolListesiAc,
  useMaddeIsaretle,
  usePersonelSecenekleri,
  useYoneticiAta,
} from './olgunlukHooks';

const tarih = (v: string | null | undefined) => (v ? new Date(v).toLocaleDateString('tr-TR') : '—');

export function IzinBakiyesiSekmesi({ personel }: { personel: Personel }) {
  const { t } = useTranslation();
  const { data: b, isPending } = useIzinBakiyesi(personel.id);

  if (!personel.ise_giris_tarihi) {
    return <Alert type="info" showIcon title={t('ik26.bakiye_tarihsiz')} />;
  }
  return (
    <div className="ik26-bakiye">
      <div className="ik26-bakiye-ozet">
        <div>
          <span className="varlik-alt">{t('ik26.kalan')}</span>
          <strong className="sayisal ik26-bakiye-sayi">
            {isPending ? '…' : (b?.bakiye ?? 0)} <small>{t('ik.birim_gun')}</small>
          </strong>
        </div>
        <div>
          <span className="varlik-alt">{t('ik26.hakedilen')}</span>
          <span className="sayisal">{b?.hakedilen ?? '—'}</span>
        </div>
        <div>
          <span className="varlik-alt">{t('ik26.kullanilan')}</span>
          <span className="sayisal">{b?.kullanilan ?? '—'}</span>
        </div>
        <div>
          <span className="varlik-alt">{t('ik26.kidem')}</span>
          <span className="sayisal">{t('ik26.yil', { yil: b?.kidem_yili ?? 0 })}</span>
        </div>
        <div>
          <span className="varlik-alt">{t('ik26.sonraki_hak')}</span>
          <span className="sayisal">
            {b?.sonraki_hak_tarihi ? `${tarih(b.sonraki_hak_tarihi)} · +${b.sonraki_hak_gun}` : '—'}
          </span>
        </div>
      </div>
      <Table
        size="small"
        rowKey="hizmet_yili"
        loading={isPending}
        pagination={false}
        dataSource={[...(b?.satirlar ?? [])].reverse()}
        locale={{ emptyText: t('ik26.henuz_hak_yok') }}
        columns={[
          {
            title: t('ik26.hizmet_yili'),
            dataIndex: 'hizmet_yili',
            render: (v: number) => <span className="sayisal">{v}</span>,
          },
          {
            title: t('ik26.dogdugu_tarih'),
            dataIndex: 'dogdugu_tarih',
            render: (v: string) => <span className="sayisal">{tarih(v)}</span>,
          },
          {
            title: t('ik26.hak_gun'),
            dataIndex: 'gun',
            align: 'right',
            render: (v: number) => <span className="sayisal">{v}</span>,
          },
        ]}
      />
      <p className="varlik-alt" style={{ marginTop: 12 }}>
        {t('ik26.bakiye_kurali')}
      </p>
    </div>
  );
}

export function YoneticiSecici({ personel }: { personel: Personel }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const secenekler = usePersonelSecenekleri();
  const ata = useYoneticiAta(personel.id);
  const liste = (secenekler.data ?? []).filter((p) => p.id !== personel.id && p.aktif);
  const yonetici = (secenekler.data ?? []).find((p) => p.id === personel.yonetici_id);

  if (!yazabilir) {
    return <span>{yonetici ? `${yonetici.ad} ${yonetici.soyad}` : '—'}</span>;
  }
  return (
    <Select
      size="small"
      allowClear
      showSearch
      optionFilterProp="label"
      style={{ minWidth: 200, maxWidth: '100%' }}
      placeholder={t('ik26.yonetici_sec')}
      loading={secenekler.isPending || ata.isPending}
      value={personel.yonetici_id ?? undefined}
      onChange={(v?: number) => ata.mutate(v ?? null)}
      options={liste.map((p) => ({
        value: p.id,
        label: `${p.ad} ${p.soyad}${p.unvan ? ` · ${p.unvan}` : ''}`,
      }))}
      aria-label={t('ik26.yonetici')}
    />
  );
}

function ListeKarti({ liste, personelId }: { liste: KontrolListesi; personelId: number }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const isaretle = useMaddeIsaretle(personelId);
  const kilitli = liste.durum === 'tamamlandi' || !yazabilir;

  return (
    <div className="ik26-liste">
      <div className="ik26-liste-baslik">
        <Space size={8}>
          {liste.tur === 'giris' ? <LoginOutlined /> : <LogoutOutlined />}
          <strong>{t(`ik26.liste_${liste.tur}`)}</strong>
          {liste.durum === 'tamamlandi' && (
            <Tag color="green" icon={<CheckCircleFilled />}>
              {t('ik26.tamamlandi')} · {tarih(liste.tamamlanma_tarihi)}
            </Tag>
          )}
        </Space>
        <Progress
          percent={Math.round((liste.tamamlanan / Math.max(liste.toplam, 1)) * 100)}
          size="small"
          style={{ width: 140, margin: 0 }}
          aria-label={t('ik26.ilerleme')}
        />
      </div>
      {liste.tur === 'cikis' && liste.acik_zimmet > 0 && liste.durum !== 'tamamlandi' && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 8 }}
          title={t('ik26.acik_zimmet_uyari', { adet: liste.acik_zimmet })}
        />
      )}
      <ul className="ik26-maddeler">
        {liste.maddeler.map((m) => (
          <li key={m.anahtar}>
            <Checkbox
              checked={m.tamam}
              disabled={kilitli || isaretle.isPending}
              onChange={(e) =>
                isaretle.mutate({ listeId: liste.id, anahtar: m.anahtar, tamam: e.target.checked })
              }
            >
              {m.ad}
            </Checkbox>
            {m.tamam && m.zaman && <span className="varlik-alt sayisal">{tarih(m.zaman)}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function KontrolListesiSekmesi({ personelId }: { personelId: number }) {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('ik:yaz'));
  const { data, isPending } = useKontrolListeleri(personelId);
  const ac = useKontrolListesiAc(personelId);
  const listeler = data ?? [];
  const var_ = (tur: string) => listeler.some((l) => l.tur === tur);

  return (
    <div>
      {yazabilir && (
        <Space wrap style={{ marginBottom: 12 }}>
          {!var_('giris') && (
            <Button
              icon={<LoginOutlined />}
              loading={ac.isPending}
              onClick={() => ac.mutate('giris')}
            >
              {t('ik26.giris_ac')}
            </Button>
          )}
          {!var_('cikis') && (
            <Button
              danger
              icon={<LogoutOutlined />}
              loading={ac.isPending}
              onClick={() => ac.mutate('cikis')}
            >
              {t('ik26.cikis_ac')}
            </Button>
          )}
        </Space>
      )}
      {!isPending && listeler.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('ik26.liste_yok')} />
      ) : (
        <div className="ik26-listeler">
          {listeler.map((l) => (
            <ListeKarti key={l.id} liste={l} personelId={personelId} />
          ))}
        </div>
      )}
    </div>
  );
}
