"""Sağlık uçları + standart zarf/hata davranışı testleri."""

from __future__ import annotations

from httpx import AsyncClient

from app.api import saglik


async def test_saglik_200_ve_zarf(istemci: AsyncClient) -> None:
    yanit = await istemci.get("/saglik")
    assert yanit.status_code == 200
    govde = yanit.json()
    assert govde["success"] is True
    assert govde["data"]["durum"] == "ayakta"
    # request_id yanıt başlığına eklenmiş olmalı
    basliklar = {k.lower(): v for k, v in yanit.headers.items()}
    assert "x-request-id" in basliklar


async def test_saglik_hazir(istemci: AsyncClient, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    # Bu dosya DB'siz; bağımlılık yoklamaları S19'dan beri gerçek (bkz. test_s19_gozlem).
    async def _tamam() -> None:
        return None

    monkeypatch.setattr(saglik, "_db_yokla", _tamam)
    monkeypatch.setattr(saglik, "_redis_yokla", _tamam)
    yanit = await istemci.get("/saglik/hazir")
    assert yanit.status_code == 200
    assert yanit.json()["data"]["hazir"] is True


async def test_bilinmeyen_uc_404_hata_zarfi(istemci: AsyncClient) -> None:
    yanit = await istemci.get("/boyle-bir-uc-yok")
    assert yanit.status_code == 404
    govde = yanit.json()
    assert govde["success"] is False
    assert "hata_kodu" in govde
    assert "detaylar" in govde


async def test_gelen_request_id_korunur(istemci: AsyncClient) -> None:
    yanit = await istemci.get("/saglik", headers={"X-Request-Id": "test-123"})
    assert yanit.headers.get("x-request-id") == "test-123"
