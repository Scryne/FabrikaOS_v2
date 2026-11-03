/**
 * Form alanı: kayıt adıyla seçim. Listeyi okuma izni yoksa eskisi gibi kayıt numarası girilir,
 * çünkü form izni ile liste izni ayrıdır (ör. isg:yaz var, ik:oku yok) ve kayıt açılabilmelidir.
 */

import { InputNumber, Select } from 'antd';

type Secenek = { value: number; label: string };

type Props = {
  izinli: boolean;
  yukleniyor?: boolean;
  secenekler: Secenek[];
  value?: number;
  onChange?: (deger: number | null | undefined) => void;
};

export function KayitSecici({ izinli, yukleniyor, secenekler, value, onChange }: Props) {
  if (!izinli) {
    return <InputNumber min={1} style={{ width: '100%' }} value={value} onChange={onChange} />;
  }
  return (
    <Select
      allowClear
      showSearch
      optionFilterProp="label"
      loading={yukleniyor}
      options={secenekler}
      value={value}
      onChange={onChange}
    />
  );
}
