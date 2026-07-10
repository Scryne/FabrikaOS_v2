/**
 * "Bir kez göster" modalı — webhook gizli anahtarı / API anahtarı yalnız oluşturma
 * anında tam döner; kullanıcı kopyalamadan kapatmasın diye belirgin uyarı taşır.
 */

import { useTranslation } from 'react-i18next';
import { CopyOutlined, KeyOutlined } from '@ant-design/icons';
import { Alert, App, Button, Input, Modal, Space } from 'antd';

export function BirKezModal({
  deger,
  kapat,
}: {
  /** Gösterilecek gizli değer; null iken modal kapalıdır. */
  deger: string | null;
  kapat: () => void;
}) {
  const { t } = useTranslation();
  const { message } = App.useApp();

  const kopyala = async () => {
    await navigator.clipboard.writeText(deger ?? '');
    message.success(t('entegrasyon.kopyalandi'));
  };

  return (
    <Modal
      open={deger !== null}
      onCancel={kapat}
      onOk={kapat}
      title={
        <span>
          <KeyOutlined style={{ marginRight: 8 }} />
          {t('entegrasyon.bir_kez_baslik')}
        </span>
      }
      okText={t('ortak.tamam')}
      cancelButtonProps={{ style: { display: 'none' } }}
      maskClosable={false}
      destroyOnHidden
    >
      <Space direction="vertical" size={14} style={{ width: '100%' }}>
        <Alert type="warning" showIcon message={t('entegrasyon.bir_kez_aciklama')} />
        <Space.Compact style={{ width: '100%' }}>
          <Input readOnly value={deger ?? ''} className="sayisal" />
          <Button icon={<CopyOutlined />} onClick={() => void kopyala()}>
            {t('entegrasyon.kopyala')}
          </Button>
        </Space.Compact>
      </Space>
    </Modal>
  );
}
