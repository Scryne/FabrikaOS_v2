/**
 * Sunucu-taraflı standart tablo — ``meta`` uyumlu sayfalama + sıralama + arama + filtre.
 *
 * Tek sorumluluk: AntD Table'ın etkileşimlerini (sayfa/boyut/sıralama) ``SayfaParam``a çevirip
 * ``paramDegistir`` ile yukarı bildirmek. Veri çekme TanStack Query hook'unda (useSayfaliSorgu)
 * yapılır; bu bileşen sunum + parametre köprüsüdür. Sıralama **kontrollüdür** (aktif ok param'dan).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Key, ReactNode } from 'react';
import { SearchOutlined } from '@ant-design/icons';
import { Input, Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import type { SortOrder } from 'antd/es/table/interface';

import type { SayfaMeta } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import { BosDurum } from '@/components/BosDurum';

function kolonAnahtari<T>(k: ColumnsType<T>[number]): string {
  if ('key' in k && k.key !== undefined) return String(k.key);
  if ('dataIndex' in k && k.dataIndex !== undefined) return String(k.dataIndex);
  return '';
}

function AramaKutusu({
  baslangic,
  yer,
  araDegisti,
}: {
  baslangic: string;
  yer: string;
  araDegisti: (q: string) => void;
}) {
  const [metin, setMetin] = useState(baslangic);
  const ilk = useRef(true);
  useEffect(() => {
    if (ilk.current) {
      ilk.current = false;
      return;
    }
    const zaman = setTimeout(() => araDegisti(metin), 350);
    return () => clearTimeout(zaman);
  }, [metin, araDegisti]);

  return (
    <Input
      allowClear
      variant="filled"
      prefix={<SearchOutlined style={{ color: 'var(--metin-soluk)' }} />}
      placeholder={yer}
      value={metin}
      onChange={(e) => setMetin(e.target.value)}
      style={{ maxWidth: 260 }}
    />
  );
}

export function SunucuTablo<T extends object>({
  kolonlar,
  veri,
  meta,
  yukleniyor = false,
  param,
  paramDegistir,
  rowKey,
  onRow,
  baslik,
  araclar,
  aramaYer,
  bosMetin,
}: {
  kolonlar: ColumnsType<T>;
  veri: T[];
  meta?: SayfaMeta;
  yukleniyor?: boolean;
  param: SayfaParam;
  paramDegistir: (yama: Partial<SayfaParam>) => void;
  rowKey: string | ((kayit: T) => Key);
  onRow?: (kayit: T) => React.HTMLAttributes<HTMLElement>;
  baslik?: ReactNode;
  araclar?: ReactNode;
  aramaYer?: string;
  bosMetin?: ReactNode;
}) {
  const { t } = useTranslation();

  const araDegisti = useCallback((q: string) => paramDegistir({ arama: q }), [paramDegistir]);

  // Aktif sıralama okunu param'dan kontrol et (sunucu sıralamasının görsel yansıması).
  const kolonlarKontrollu: ColumnsType<T> = kolonlar.map((k) => {
    if (!('sorter' in k) || !k.sorter) return k;
    const anahtar = kolonAnahtari(k);
    const sortOrder: SortOrder =
      anahtar === param.siralama ? (param.yon === 'asc' ? 'ascend' : 'descend') : null;
    return { ...k, sortOrder };
  });

  const aracCubuguVar = Boolean(baslik || aramaYer || araclar);

  // Boş durum: düz metin sakin öğretici bloğa sarılır; hazır ReactNode ise aynen kullanılır.
  const bosGovde =
    bosMetin == null || typeof bosMetin === 'string' || typeof bosMetin === 'number' ? (
      <BosDurum baslik={bosMetin ?? t('tablo.bos')} />
    ) : (
      bosMetin
    );

  return (
    <div>
      {aracCubuguVar && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            flexWrap: 'wrap',
            marginBottom: 16,
          }}
        >
          <div style={{ marginRight: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
            {baslik}
            {meta != null && (
              <span className="kayit-sayaci">
                <strong className="sayisal">{meta.toplam.toLocaleString('tr-TR')}</strong>
                {t('tablo.kayit')}
              </span>
            )}
          </div>
          {aramaYer && (
            <AramaKutusu baslangic={param.arama ?? ''} yer={aramaYer} araDegisti={araDegisti} />
          )}
          {araclar}
        </div>
      )}

      <Table<T>
        rowKey={rowKey}
        columns={kolonlarKontrollu}
        dataSource={veri}
        loading={yukleniyor}
        onRow={onRow}
        size="middle"
        scroll={{ x: 'max-content' }}
        locale={{ emptyText: bosGovde }}
        pagination={{
          current: param.sayfa,
          pageSize: param.adet,
          total: meta?.toplam ?? 0,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50, 100],
          showTotal: (toplam, [bas, son]) => t('tablo.toplam', { aralik: `${bas}-${son}`, toplam }),
        }}
        onChange={(sayfalama, _filtreler, siralayici) => {
          const s = Array.isArray(siralayici) ? siralayici[0] : siralayici;
          const yeniSiralama = s && s.order ? String(s.columnKey ?? s.field) : undefined;
          const yeniYon = s && s.order ? (s.order === 'ascend' ? 'asc' : 'desc') : undefined;
          const siralamaDegisti = yeniSiralama !== param.siralama || yeniYon !== param.yon;
          paramDegistir({
            sayfa: siralamaDegisti ? 1 : (sayfalama.current ?? 1),
            adet: sayfalama.pageSize ?? param.adet,
            siralama: yeniSiralama,
            yon: yeniYon,
          });
        }}
      />
    </div>
  );
}
