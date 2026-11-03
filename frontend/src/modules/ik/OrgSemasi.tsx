/**
 * Organizasyon şeması (S26-B, ADR-0044): aktif personel, doğrudan yönetici ilişkisiyle ağaç.
 * Ağaç istemcide kurulur; departman süzgecinde yöneticisi dışarıda kalan kişi kök olur (sunucu).
 * Yönetici ataması personel detayındadır; döngü sunucuda 409 ile reddedilir.
 */

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { ApartmentOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons';
import { Card, Empty, Select, Skeleton, Tag, Tree } from 'antd';
import type { DataNode } from 'antd/es/tree';

import { OzetSerit } from '@/components/OzetSerit';
import { SayfaBaslik } from '@/components/SayfaBaslik';
import { SayfaKapsayici } from '@/components/SayfaKapsayici';

import { type OrgDugum, useOrgSemasi } from './olgunlukHooks';

function agacKur(dugumler: OrgDugum[]): DataNode[] {
  const cocuklar = new Map<number | null, OrgDugum[]>();
  for (const d of dugumler) {
    const ust = d.yonetici_id ?? null;
    cocuklar.set(ust, [...(cocuklar.get(ust) ?? []), d]);
  }
  const kur = (ust: number | null): DataNode[] =>
    (cocuklar.get(ust) ?? []).map((d) => ({
      key: d.id,
      title: (
        <span className="org-dugum">
          <span className="varlik-ad">{d.ad_soyad}</span>
          {d.unvan && <span className="varlik-alt">{d.unvan}</span>}
          {d.departman && (
            <Tag variant="filled" className="org-dep">
              {d.departman}
            </Tag>
          )}
          {d.ast_sayisi > 0 && (
            <span className="varlik-alt sayisal">
              <TeamOutlined /> {d.ast_sayisi}
            </span>
          )}
        </span>
      ),
      icon: <UserOutlined />,
      children: kur(d.id),
    }));
  return kur(null);
}

export function OrgSemasi() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [departman, setDepartman] = useState<string | undefined>();
  const tum = useOrgSemasi();
  const secili = useOrgSemasi(departman);
  const veri = useMemo(
    () => (departman ? secili.data : tum.data) ?? [],
    [departman, secili.data, tum.data],
  );
  const yukleniyor = departman ? secili.isPending : tum.isPending;

  const departmanlar = useMemo(
    () => [...new Set((tum.data ?? []).map((d) => d.departman).filter(Boolean))].sort(),
    [tum.data],
  );
  const agac = useMemo(() => agacKur(veri), [veri]);
  const kokSayisi = veri.filter((d) => d.yonetici_id === null).length;
  const yoneticiSayisi = veri.filter((d) => d.ast_sayisi > 0).length;

  return (
    <SayfaKapsayici>
      <SayfaBaslik
        baslik={t('ik26.org_baslik')}
        alt={t('ik26.org_alt')}
        sag={
          <Select
            allowClear
            placeholder={t('ik26.tum_departmanlar')}
            style={{ minWidth: 200 }}
            value={departman}
            onChange={setDepartman}
            options={departmanlar.map((d) => ({ value: d, label: d }))}
            aria-label={t('ik.departman')}
          />
        }
      />
      <OzetSerit
        yukleniyor={yukleniyor}
        metrikler={[
          { anahtar: 'kisi', baslik: t('ik26.kisi'), deger: String(veri.length) },
          { anahtar: 'yonetici', baslik: t('ik26.yonetici_sayisi'), deger: String(yoneticiSayisi) },
          {
            anahtar: 'kok',
            baslik: t('ik26.yoneticisiz'),
            deger: String(kokSayisi),
            ikon: <ApartmentOutlined />,
          },
        ]}
      />
      <Card style={{ marginTop: 16 }}>
        {yukleniyor ? (
          <Skeleton active paragraph={{ rows: 6 }} />
        ) : agac.length === 0 ? (
          <Empty description={t('ik26.org_bos')} />
        ) : (
          <Tree
            className="org-agac"
            showLine
            showIcon
            defaultExpandAll
            blockNode
            treeData={agac}
            onSelect={(anahtarlar) => {
              if (anahtarlar[0] !== undefined) navigate(`/personeller/${String(anahtarlar[0])}`);
            }}
          />
        )}
        <p className="varlik-alt" style={{ marginTop: 12 }}>
          {t('ik26.org_ipucu')}
        </p>
      </Card>
    </SayfaKapsayici>
  );
}
