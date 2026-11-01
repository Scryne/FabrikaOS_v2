"""Sürüm notları (S28, ADR-0047): git geçmişinden CHANGELOG bloğu.

Commit başlıkları iki biçimde yazılır ve ikisi de tanınır:

- sprint: ``S27 platform deneyimi: …``, ``S26-B İSG + İK …`` → "Sprintler"
- Conventional Commits: ``fix(stok): …``, ``feat!: …`` → türüne göre (Yeni, Düzeltme, Güvenlik …)

Elle yazılan özet (CHANGELOG'un geri kalanı) korunur; betik yalnız işaretli bloğu yeniden üretir::

    <!-- surum-notlari:baslangic -->
    … üretilen liste …
    <!-- surum-notlari:bitis -->

Kullanım (repo kökünden)::

    python backend/scripts/surum_notlari.py                 # son etiketten bu yana, ekrana
    python backend/scripts/surum_notlari.py --yaz           # CHANGELOG.md bloğunu güncelle
    python backend/scripts/surum_notlari.py --surum v1.0.0  # "Yayımlanmamış"ı sürüme çevir

``--yaz`` sürüm hazırlığında elle koşulur (CI'da denetlenmez: blok HEAD'e kadar listeler, onu
commit'lemek HEAD'i değiştirir). ``--surum`` etiketi kendisi atmaz; sürüm commit'i ve ``git tag``
insan kararıdır.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
CHANGELOG = KOK / "CHANGELOG.md"
BAS, BIT = "<!-- surum-notlari:baslangic -->", "<!-- surum-notlari:bitis -->"
YAYIMLANMAMIS = "## Yayımlanmamış"

_SPRINT = re.compile(r"^(S\d+(?:-[A-Z])?)\b[:\s]+(.*)$")
_KONVANSIYON = re.compile(r"^(\w+)(?:\(([^)]*)\))?(!)?:\s*(.*)$")
TURLER = {
    "feat": "Yeni",
    "fix": "Düzeltme",
    "perf": "Performans",
    "security": "Güvenlik",
    "refactor": "Yeniden düzenleme",
    "docs": "Doküman",
    "test": "Test",
    "ci": "CI",
    "build": "Derleme",
    "chore": "Bakım",
}
# Türkçe öneklerle yazılmış eski commit'ler (ör. "Guvenlik: …", "CI: …", "Testler: …").
TR_ONEK = {
    "guvenlik": "Güvenlik",
    "güvenlik": "Güvenlik",
    "ci": "CI",
    "testler": "Test",
    "docs": "Doküman",
}
SIRA = ["Sprintler", "Kırıcı değişiklik", *TURLER.values(), "Diğer"]


def _git(*arg: str) -> str:
    return subprocess.run(
        ["git", *arg], cwd=KOK, capture_output=True, text=True, encoding="utf-8", check=True
    ).stdout


def son_etiket() -> str | None:
    try:
        return _git("describe", "--tags", "--abbrev=0").strip() or None
    except subprocess.CalledProcessError:
        return None


def commitler(baslangic: str | None) -> list[tuple[str, str]]:
    aralik = f"{baslangic}..HEAD" if baslangic else "HEAD"
    cikti = _git("log", aralik, "--no-merges", "--format=%h%x1f%s")
    return [tuple(s.split("\x1f", 1)) for s in cikti.splitlines() if s]  # type: ignore[misc]


def grupla(liste: list[tuple[str, str]]) -> dict[str, list[str]]:
    gruplar: dict[str, list[str]] = defaultdict(list)
    for kisa, baslik in liste:
        if m := _SPRINT.match(baslik):
            gruplar["Sprintler"].append(f"**{m.group(1)}** {m.group(2)} (`{kisa}`)")
            continue
        if (m := _KONVANSIYON.match(baslik)) and m.group(1).lower() in TURLER:
            tur, kapsam, kirici, metin = m.groups()
            satir = f"{f'**{kapsam}:** ' if kapsam else ''}{metin} (`{kisa}`)"
            gruplar["Kırıcı değişiklik" if kirici else TURLER[tur.lower()]].append(satir)
            continue
        onek, _, kalan = baslik.partition(":")
        if kalan and onek.strip().lower() in TR_ONEK:
            gruplar[TR_ONEK[onek.strip().lower()]].append(f"{kalan.strip()} (`{kisa}`)")
            continue
        gruplar["Diğer"].append(f"{baslik} (`{kisa}`)")
    return gruplar


def blok_uret(baslangic: str | None) -> str:
    gruplar = grupla(commitler(baslangic))
    kaynak = f"`{baslangic}`'ten bu yana" if baslangic else "ilk commit'ten bu yana"
    satirlar = [BAS, f"_Commit geçmişinden üretildi ({kaynak}); elle düzenlemeyin._", ""]
    for ad in SIRA:
        if gruplar.get(ad):
            satirlar += [f"#### {ad}", *(f"- {x}" for x in gruplar[ad]), ""]
    satirlar.append(BIT)
    return "\n".join(satirlar)


def blok_yerlestir(metin: str, blok: str) -> str:
    if BAS in metin and BIT in metin:
        bas, bit = metin.index(BAS), metin.index(BIT) + len(BIT)
        return metin[:bas] + blok + metin[bit:]
    if YAYIMLANMAMIS not in metin:
        raise SystemExit(f"CHANGELOG'da '{YAYIMLANMAMIS}' başlığı yok")
    i = metin.index(YAYIMLANMAMIS) + len(YAYIMLANMAMIS)
    return (
        metin[:i]
        + "\n\n<details><summary>Tüm commit'ler</summary>\n\n"
        + blok
        + ("\n\n</details>")
        + metin[i:]
    )


def surume_cevir(metin: str, surum: str) -> str:
    if YAYIMLANMAMIS not in metin:
        raise SystemExit(f"CHANGELOG'da '{YAYIMLANMAMIS}' başlığı yok")
    yeni = f"{YAYIMLANMAMIS}\n\n## [{surum}] — {date.today().isoformat()}"
    return metin.replace(YAYIMLANMAMIS, yeni, 1)


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS sürüm notları")
    p.add_argument("--baslangic", help="git referansı (varsayılan: son etiket)")
    p.add_argument("--yaz", action="store_true")
    p.add_argument("--surum", help="Yayımlanmamış bölümü bu sürüme çevir (ör. v1.0.0)")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    metin = CHANGELOG.read_text(encoding="utf-8")
    if a.surum:
        CHANGELOG.write_text(surume_cevir(metin, a.surum), encoding="utf-8", newline="\n")
        print(
            f"CHANGELOG: Yayımlanmamış → {a.surum}. Şimdi commit'le ve etiketle: git tag {a.surum}"
        )
        return 0
    blok = blok_uret(a.baslangic or son_etiket())
    yeni = blok_yerlestir(metin, blok)
    if a.yaz:
        CHANGELOG.write_text(yeni, encoding="utf-8", newline="\n")
        print("CHANGELOG.md güncellendi")
    else:
        print(blok)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
