/**
 * Tehlikeli aksiyon onay modalı — GitHub deseni: kullanıcı tenant slug'ını birebir
 * yazmadan onay butonu etkinleşmez (silme/askıya alma gibi geri dönüşü zor işlemler).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert, Input, Modal } from 'antd';

export function TehlikeOnayModal({
  acik,
  baslik,
  aciklama,
  slug,
  yukleniyor,
  onayla,
  kapat,
}: {
  acik: boolean;
  baslik: string;
  aciklama: string;
  slug: string;
  yukleniyor?: boolean;
  onayla: () => void;
  kapat: () => void;
}) {
  const { t } = useTranslation();
  const [metin, setMetin] = useState('');
  const eslesti = metin === slug;

  return (
    <Modal
      open={acik}
      title={baslik}
      okText={baslik}
      okButtonProps={{ danger: true, disabled: !eslesti, loading: yukleniyor }}
      onOk={onayla}
      onCancel={() => {
        setMetin('');
        kapat();
      }}
      afterClose={() => setMetin('')}
      destroyOnHidden
    >
      <Alert type="warning" showIcon message={aciklama} style={{ marginBottom: 16 }} />
      <p style={{ color: 'var(--metin-soluk)', fontSize: 13, marginBottom: 8 }}>
        {t('platform.onay_yaz', { slug })}
      </p>
      <Input
        value={metin}
        onChange={(e) => setMetin(e.target.value)}
        placeholder={slug}
        autoFocus
        status={metin && !eslesti ? 'error' : undefined}
        className="sayisal"
      />
    </Modal>
  );
}
