/**
 * İş emirleri ana ekranı — liste ↔ kanban görünüm geçişi + oluştur + detay çekmecesi.
 * "İş emri oluştur" yalnız ``isemri:yaz`` izniyle görünür (ekran ``isemri:oku`` ile korunur).
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AppstoreOutlined, PlusOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { Button, Card, Segmented, Space } from 'antd';

import { SayfaBaslik } from '@/components/SayfaBaslik';
import { useAuthStore } from '@/store/authStore';

import { IsEmriDetay } from './IsEmriDetay';
import { IsEmriFormu } from './IsEmriFormu';
import { IsEmriKanban } from './IsEmriKanban';
import { IsEmriListesi } from './IsEmriListesi';

type Gorunum = 'liste' | 'pano';

export function IsEmriEkrani() {
  const { t } = useTranslation();
  const yazabilir = useAuthStore((s) => s.izinVar('isemri:yaz'));
  const [gorunum, setGorunum] = useState<Gorunum>('liste');
  const [seciliId, setSeciliId] = useState<number | null>(null);
  const [formAcik, setFormAcik] = useState(false);

  return (
    <div style={{ maxWidth: 1320 }}>
      <SayfaBaslik
        baslik={t('menu.is_emirleri')}
        alt={t('isemri.alt')}
        sag={
          <Space wrap>
            <Segmented<Gorunum>
              value={gorunum}
              onChange={setGorunum}
              options={[
                { value: 'liste', icon: <UnorderedListOutlined />, label: t('isemri.liste') },
                { value: 'pano', icon: <AppstoreOutlined />, label: t('isemri.pano') },
              ]}
            />
            {yazabilir && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setFormAcik(true)}>
                {t('isemri.is_emri_olustur')}
              </Button>
            )}
          </Space>
        }
      />

      {gorunum === 'liste' ? (
        <Card styles={{ body: { padding: 18 } }}>
          <IsEmriListesi ac={setSeciliId} />
        </Card>
      ) : (
        <IsEmriKanban ac={setSeciliId} />
      )}

      <IsEmriDetay id={seciliId} kapat={() => setSeciliId(null)} />
      <IsEmriFormu acik={formAcik} kapat={() => setFormAcik(false)} />
    </div>
  );
}
