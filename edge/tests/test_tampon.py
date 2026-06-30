"""Edge store-and-forward tamponu: kayıpsız replay + restart dayanıklılığı."""

from __future__ import annotations

from pathlib import Path

from edge.tampon import Tampon


def test_ekle_bekleyen_onayla(tmp_path: Path) -> None:
    t = Tampon(str(tmp_path / "t.sqlite"))
    t.ekle("a", '{"x":1}')
    t.ekle("b", '{"x":2}')
    assert t.bekleyen_sayisi() == 2
    assert [oid for oid, _ in t.bekleyenler()] == ["a", "b"]
    t.onayla("a")
    assert [oid for oid, _ in t.bekleyenler()] == ["b"]


def test_cift_ekle_yok_sayilir(tmp_path: Path) -> None:
    t = Tampon(str(tmp_path / "t.sqlite"))
    t.ekle("a", '{"x":1}')
    t.ekle("a", '{"x":1}')
    assert t.bekleyen_sayisi() == 1


def test_restart_dayanikli(tmp_path: Path) -> None:
    yol = str(tmp_path / "t.sqlite")
    t1 = Tampon(yol)
    t1.ekle("a", "{}")
    t1.ekle("b", "{}")
    t1.onayla("a")
    t1.kapat()
    # süreç yeniden başladı: yeni Tampon aynı dosyayı açar
    t2 = Tampon(yol)
    assert [oid for oid, _ in t2.bekleyenler()] == ["b"]


def test_kesinti_sonrasi_kayipsiz_replay(tmp_path: Path) -> None:
    """Broker düşükken eklenenler kalır; reconnect'te hepsi 'gönderilir' (kayıpsız, çift yok)."""
    t = Tampon(str(tmp_path / "t.sqlite"))
    for i in range(5):
        t.ekle(str(i), "{}")
    gonderilen: list[str] = []
    # simüle: ilk 2 başarılı (onaylanır), sonra broker düşer
    for oid, _ in t.bekleyenler()[:2]:
        gonderilen.append(oid)
        t.onayla(oid)
    # reconnect: kalanları gönder
    for oid, _ in t.bekleyenler():
        gonderilen.append(oid)
        t.onayla(oid)
    assert sorted(gonderilen) == ["0", "1", "2", "3", "4"]
    assert len(gonderilen) == len(set(gonderilen))  # çift yok
    assert t.bekleyen_sayisi() == 0
