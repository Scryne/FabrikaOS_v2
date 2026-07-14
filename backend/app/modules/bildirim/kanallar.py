"""Bildirim kanalları — uygulama-içi otoritedir; e-posta iskelet, SMS stub.

Kanal hatası bildirimi asla düşürmez: uygulama-içi satır DB'ye yazıldıktan sonra
kanal gönderimi best-effort'tur (S-VB bilinçli kararı; gerçek sağlayıcı S27).

``EPostaKanali`` stdlib ``smtplib`` ile çalışır (ek bağımlılık yok) ve event loop'u
bloklamamak için ``asyncio.to_thread`` kullanır. ``smtp_host`` yapılandırılmamışsa
gönderim sessizce atlanır (dev/test varsayılanı).
"""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("app.bildirim.kanallar")


def _eposta_metni(baslik: str, govde: str) -> str:
    """Düz-metin e-posta şablonu (TR referans)."""
    return f"{govde}\n\n—\nBu ileti FabrikaOS bildirim merkezi tarafından gönderildi."


def _smtp_gonder(host: str, port: int, gonderen: str, alici: str, msg: EmailMessage) -> None:
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        ayar = get_settings()
        if ayar.smtp_kullanici:
            smtp.starttls()
            smtp.login(ayar.smtp_kullanici, ayar.smtp_parola)
        smtp.send_message(msg)


class EPostaKanali:
    """SMTP üzerinden bildirim e-postası (iskelet; şablon düz metin)."""

    async def gonder(self, *, alici_eposta: str, baslik: str, govde: str) -> bool:
        ayar = get_settings()
        if not ayar.smtp_host:
            logger.debug("SMTP yapılandırılmamış; e-posta atlandı (alici=%s)", alici_eposta)
            return False
        msg = EmailMessage()
        msg["From"] = ayar.smtp_gonderen
        msg["To"] = alici_eposta
        msg["Subject"] = f"[FabrikaOS] {baslik}"
        msg.set_content(_eposta_metni(baslik, govde))
        try:
            await asyncio.to_thread(
                _smtp_gonder, ayar.smtp_host, ayar.smtp_port, ayar.smtp_gonderen, alici_eposta, msg
            )
            return True
        except Exception:  # noqa: BLE001 — kanal hatası bildirimi düşürmez
            logger.warning("bildirim e-postası gönderilemedi (alici=%s)", alici_eposta)
            return False


class SmsKanali:
    """SMS kanalı stub'ı — yalnız loglar (gerçek sağlayıcı S27)."""

    async def gonder(self, *, alici_telefon: str, baslik: str) -> bool:
        logger.info("SMS stub: %s → %s", baslik, alici_telefon)
        return False
