/**
 * TOTP 2FA kurulum sihirbazı (S23 / ADR-0022) — iki yerde kullanılır:
 * 1. Giriş ekranında, tenant 2FA'yı **zorunlu** kılmışsa (henüz tam oturum yok → geçici token),
 * 2. Güvenlik ekranında, kullanıcı kendi isteğiyle açarken (normal oturum).
 *
 * Üç adım: QR/sır göster → authenticator kodunu doğrula → **kurtarma kodlarını bir kez göster**.
 * Kurtarma kodları yalnız etkinleştirme yanıtında döner; kapatılınca bir daha gösterilemez —
 * kullanıcı "kaydettim" onayı vermeden sihirbaz kapanmaz.
 */

import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { CheckCircleOutlined, CopyOutlined, SafetyOutlined } from '@ant-design/icons';
import { Alert, Button, Checkbox, Input, QRCode, Space, Spin, Steps, Typography } from 'antd';

import { ApiHata } from '@/api/client';
import { ikiAsamaEtkinlestir, ikiAsamaKur } from '@/api/kimlik';

export function IkiAsamaKurulum({
  geciciToken,
  onTamamlandi,
  onIptal,
}: {
  /** Zorunlu-2FA ilk girişinde kurulum token'ı; normal oturumda verilmez. */
  geciciToken?: string;
  onTamamlandi: () => void;
  onIptal?: () => void;
}) {
  const { t } = useTranslation();
  const [adim, setAdim] = useState(0);
  const [sir, setSir] = useState('');
  const [uri, setUri] = useState('');
  const [kod, setKod] = useState('');
  const [kurtarmaKodlari, setKurtarmaKodlari] = useState<string[]>([]);
  const [kaydettim, setKaydettim] = useState(false);
  const [yukleniyor, setYukleniyor] = useState(true);
  const [hata, setHata] = useState<string | null>(null);

  const kurulumBaslat = useCallback(async () => {
    setYukleniyor(true);
    setHata(null);
    try {
      const cevap = await ikiAsamaKur(geciciToken);
      setSir(cevap.sir);
      setUri(cevap.otpauth_uri);
    } catch (e) {
      setHata(e instanceof ApiHata ? e.message : t('guvenlik.kurulum_hatasi'));
    } finally {
      setYukleniyor(false);
    }
  }, [geciciToken, t]);

  useEffect(() => {
    void kurulumBaslat();
  }, [kurulumBaslat]);

  async function etkinlestir() {
    setHata(null);
    setYukleniyor(true);
    try {
      const kodlar = await ikiAsamaEtkinlestir(kod.trim(), geciciToken);
      setKurtarmaKodlari(kodlar);
      setAdim(2);
    } catch (e) {
      setHata(e instanceof ApiHata ? e.message : t('guvenlik.kod_hatali'));
    } finally {
      setYukleniyor(false);
    }
  }

  function kodlariKopyala() {
    void navigator.clipboard?.writeText(kurtarmaKodlari.join('\n'));
  }

  return (
    <div>
      <Steps
        size="small"
        current={adim}
        style={{ marginBottom: 20 }}
        items={[
          { title: t('guvenlik.adim_tara') },
          { title: t('guvenlik.adim_dogrula') },
          { title: t('guvenlik.adim_kurtarma') },
        ]}
      />

      {hata && <Alert type="error" showIcon message={hata} style={{ marginBottom: 16 }} />}

      {adim === 0 && (
        <Spin spinning={yukleniyor}>
          <Space direction="vertical" size={16} style={{ width: '100%' }}>
            <Typography.Paragraph style={{ marginBottom: 0 }}>
              {t('guvenlik.qr_aciklama')}
            </Typography.Paragraph>
            {uri && (
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <QRCode value={uri} size={188} bgColor="#ffffff" />
              </div>
            )}
            <div>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                {t('guvenlik.el_ile_giris')}
              </Typography.Text>
              <Typography.Paragraph copyable={{ text: sir }} className="sayisal">
                {sir}
              </Typography.Paragraph>
            </div>
            <Space>
              <Button type="primary" onClick={() => setAdim(1)} disabled={!uri}>
                {t('ortak.devam')}
              </Button>
              {onIptal && <Button onClick={onIptal}>{t('ortak.iptal')}</Button>}
            </Space>
          </Space>
        </Spin>
      )}

      {adim === 1 && (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Typography.Paragraph style={{ marginBottom: 0 }}>
            {t('guvenlik.kod_gir_aciklama')}
          </Typography.Paragraph>
          <Input
            value={kod}
            onChange={(e) => setKod(e.target.value)}
            onPressEnter={() => void etkinlestir()}
            placeholder="123456"
            inputMode="numeric"
            autoComplete="one-time-code"
            maxLength={8}
            size="large"
            className="sayisal"
            aria-label={t('guvenlik.dogrulama_kodu')}
          />
          <Space>
            <Button
              type="primary"
              loading={yukleniyor}
              disabled={kod.trim().length < 6}
              onClick={() => void etkinlestir()}
              icon={<SafetyOutlined />}
            >
              {t('guvenlik.etkinlestir')}
            </Button>
            <Button onClick={() => setAdim(0)}>{t('ortak.geri')}</Button>
          </Space>
        </Space>
      )}

      {adim === 2 && (
        <Space direction="vertical" size={16} style={{ width: '100%' }}>
          <Alert
            type="warning"
            showIcon
            message={t('guvenlik.kurtarma_baslik')}
            description={t('guvenlik.kurtarma_aciklama')}
          />
          <div
            className="sayisal"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
              gap: 8,
              padding: 16,
              border: '1px solid var(--kenarlik)',
              borderRadius: 8,
              background: 'var(--yuzey-ust)',
            }}
          >
            {kurtarmaKodlari.map((k) => (
              <span key={k}>{k}</span>
            ))}
          </div>
          <Button icon={<CopyOutlined />} onClick={kodlariKopyala}>
            {t('guvenlik.kodlari_kopyala')}
          </Button>
          <Checkbox checked={kaydettim} onChange={(e) => setKaydettim(e.target.checked)}>
            {t('guvenlik.kodlari_kaydettim')}
          </Checkbox>
          <Button
            type="primary"
            disabled={!kaydettim}
            icon={<CheckCircleOutlined />}
            onClick={onTamamlandi}
          >
            {t('ortak.tamam')}
          </Button>
        </Space>
      )}
    </div>
  );
}
