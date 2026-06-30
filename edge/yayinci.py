"""MQTT yayıncı — tampondaki bekleyen ölçümleri yayınlar, PUBACK'te onaylar (QoS 1)."""

from __future__ import annotations

import aiomqtt

from edge.tampon import Tampon


def topic_adi(slug: str, cihaz_kod: str) -> str:
    return f"fabrikaos/{slug}/{cihaz_kod}/olcum"


async def yayinla_bekleyenler(
    client: aiomqtt.Client, tampon: Tampon, *, slug: str, cihaz_kod: str
) -> int:
    """Bekleyenleri sırayla yayınlar; her başarılı PUBACK sonrası tampondan siler. Sayı döner."""
    konu = topic_adi(slug, cihaz_kod)
    gonderilen = 0
    for olcum_id, paket_json in tampon.bekleyenler():
        await client.publish(konu, payload=paket_json.encode(), qos=1)
        tampon.onayla(olcum_id)
        gonderilen += 1
    return gonderilen
