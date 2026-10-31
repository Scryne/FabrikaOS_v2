/**
 * Kaza tablosunun CAPA hücresi (S26-B, ADR-0044): bağlı vaka varsa koduna derin bağlantı, yoksa
 * "CAPA aç" (yalnız `isg:yaz` + `kalite:yaz`). Kaza başına tek vaka sunucuda UNIQUE ile korunur.
 */

import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { FileProtectOutlined } from '@ant-design/icons';
import { App, Button, Popconfirm } from 'antd';

import { useAuthStore } from '@/store/authStore';

import type { IsKazasi } from './hooks';
import { useKazadanCapa } from './olgunlukHooks';

export function KazaCapaHucre({ kaza }: { kaza: IsKazasi }) {
  const { t } = useTranslation();
  const { message } = App.useApp();
  const ac = useKazadanCapa();
  const izinVar = useAuthStore((s) => s.izinVar);

  if (kaza.capa_uygunsuzluk_id) {
    return (
      <Link
        to={`/uygunsuzluklar?uygunsuzluk=${kaza.capa_uygunsuzluk_id}`}
        className="sayisal"
        onClick={(e) => e.stopPropagation()}
      >
        {kaza.capa_kod}
      </Link>
    );
  }
  if (!izinVar('isg:yaz') || !izinVar('kalite:yaz')) return <span className="varlik-alt">—</span>;
  return (
    <Popconfirm
      title={t('isg26.capa_soru')}
      description={t('isg26.capa_aciklama')}
      okText={t('isg26.capa_ac')}
      cancelText={t('ortak.vazgec')}
      onConfirm={() =>
        ac.mutate(kaza.id, {
          onSuccess: (c) => message.success(t('isg26.capa_acildi', { kod: c.kod })),
        })
      }
    >
      <Button
        size="small"
        icon={<FileProtectOutlined />}
        loading={ac.isPending && ac.variables === kaza.id}
        onClick={(e) => e.stopPropagation()}
      >
        {t('isg26.capa_ac')}
      </Button>
    </Popconfirm>
  );
}
