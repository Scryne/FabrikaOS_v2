/**
 * Komut paleti (⌘K) — global gezinme. Menüden beslenir + RBAC süzgeçli (yalnız yetkili olduğun
 * sayfalar). Arama + klavye gezinmesi (↑/↓/Enter); satır başında modül hat rengi noktası. Kontrollü
 * (``acik``/``kapat``); ⌘K global kısayolu ve tetikleyici kabukta bağlanır. Faz 6/S27'de içerik
 * aramayla derinleşir (kayıt arama).
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, KeyboardEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { SearchOutlined } from '@ant-design/icons';
import { Input, Modal } from 'antd';
import type { InputRef } from 'antd';

import { gorunurMenu, MENU } from '@/layouts/menu';
import { useAuthStore } from '@/store/authStore';
import { BOLUM_RENGI, MENU_IKONLARI } from '@/tema/modulKimlik';

export function KomutPaleti({ acik, kapat }: { acik: boolean; kapat: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const izinler = useAuthStore((s) => s.izinler);
  const [sorgu, setSorgu] = useState('');
  const [aktif, setAktif] = useState(0);
  const girisRef = useRef<InputRef>(null);
  const aktifRef = useRef<HTMLDivElement>(null);

  const gorunur = useMemo(() => gorunurMenu(MENU, (izin) => izinler.has(izin)), [izinler]);

  const sonuclar = useMemo(() => {
    const q = sorgu.trim().toLocaleLowerCase('tr');
    return gorunur
      .map((o) => ({
        anahtar: o.anahtar,
        yol: o.yol,
        bolum: o.bolum,
        etiket: t(o.etiketAnahtari),
        bolumAd: t(o.bolum),
      }))
      .filter(
        (o) =>
          !q ||
          o.etiket.toLocaleLowerCase('tr').includes(q) ||
          o.bolumAd.toLocaleLowerCase('tr').includes(q),
      );
  }, [gorunur, sorgu, t]);

  // Palet her açılışta temizlenir + odak girişe düşer.
  useEffect(() => {
    if (acik) {
      setSorgu('');
      setAktif(0);
    }
  }, [acik]);

  // Arama değişince aktif seçim başa döner.
  useEffect(() => {
    setAktif(0);
  }, [sorgu]);

  // Klavye gezinmesinde aktif öğe görünür alanda kalır (liste 360px'te kaydırmalı).
  useEffect(() => {
    aktifRef.current?.scrollIntoView({ block: 'nearest' });
  }, [aktif]);

  const git = (yol: string) => {
    kapat();
    navigate(yol);
  };

  const tusIsle = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setAktif((a) => Math.min(a + 1, sonuclar.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setAktif((a) => Math.max(a - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const s = sonuclar[aktif];
      if (s) git(s.yol);
    }
  };

  return (
    <Modal
      open={acik}
      onCancel={kapat}
      footer={null}
      closable={false}
      width={560}
      styles={{ body: { padding: 0 } }}
      afterOpenChange={(o) => {
        if (o) girisRef.current?.focus();
      }}
      destroyOnHidden
    >
      <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--kenarlik)' }}>
        <Input
          ref={girisRef}
          variant="borderless"
          size="large"
          prefix={<SearchOutlined style={{ color: 'var(--metin-soluk)' }} />}
          placeholder={t('komut.yer')}
          value={sorgu}
          onChange={(e) => setSorgu(e.target.value)}
          onKeyDown={tusIsle}
          allowClear
          role="combobox"
          aria-expanded={acik}
          aria-controls="komut-liste"
          aria-activedescendant={sonuclar[aktif] ? `komut-secenek-${aktif}` : undefined}
        />
      </div>
      <div
        id="komut-liste"
        role="listbox"
        aria-label={t('komut.yer')}
        style={{ maxHeight: 360, overflowY: 'auto', padding: 8 }}
      >
        {sonuclar.map((s, i) => (
          <div
            key={s.yol}
            id={`komut-secenek-${i}`}
            ref={i === aktif ? aktifRef : undefined}
            role="option"
            aria-selected={i === aktif}
            className="komut-oge"
            style={{ '--hat': BOLUM_RENGI[s.bolum] } as CSSProperties}
            onMouseEnter={() => setAktif(i)}
            onClick={() => git(s.yol)}
          >
            <span className="komut-hat" aria-hidden="true" />
            <span style={{ display: 'inline-flex', width: 18, justifyContent: 'center' }}>
              {MENU_IKONLARI[s.anahtar]}
            </span>
            <span style={{ color: 'var(--metin)' }}>{s.etiket}</span>
            <span style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--metin-soluk)' }}>
              {s.bolumAd}
            </span>
          </div>
        ))}
        {sonuclar.length === 0 && (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--metin-soluk)' }}>
            {t('komut.bos')}
          </div>
        )}
      </div>
    </Modal>
  );
}
