/**
 * Modül entitlement kapısı (S16 / ADR-0018): modül tenant aboneliğinde kapalıysa
 * içerik yerine "modül kapalı" upsell boş durumu gösterir (`abonelik:oku` iznine
 * sahip kullanıcıya /abonelik CTA'sı). Veri yüklenmemişken fail-open — backend zorlar.
 */

import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import { LockOutlined } from '@ant-design/icons';
import { Button } from 'antd';

import { BosDurum } from '@/components/BosDurum';
import { useModuller } from '@/modules/abonelik/hooks';
import { useAuthStore } from '@/store/authStore';

export function ModulKapisi({ modul, children }: { modul: string; children: ReactNode }) {
  const { t } = useTranslation();
  const { data } = useModuller();
  const izinVar = useAuthStore((s) => s.izinVar);

  const acik = !data || (data.moduller.find((m) => m.kod === modul)?.acik ?? true);
  if (acik) return <>{children}</>;

  return (
    <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 64 }}>
      <BosDurum
        ikon={<LockOutlined />}
        baslik={t('abonelik.modul_kapali')}
        aciklama={t('abonelik.modul_kapali_aciklama')}
        aksiyon={
          izinVar('abonelik:oku') ? (
            <Link to="/abonelik">
              <Button type="primary">{t('abonelik.plani_goruntule')}</Button>
            </Link>
          ) : undefined
        }
      />
    </div>
  );
}
