"""Mutasyon testi (S28, ADR-0047): kritik saf çekirdekte testlerin hatayı yakaladığını ölçer.

mutmut/cosmic-ray yerine küçük bir AST koşucusu: mutmut 3 ``fork`` ister ve Windows'ta çalışmaz;
bu araç hem geliştirici makinesinde hem CI'da aynı sonucu verir. Her hedef dosyada tek tek şu
mutasyonlar uygulanır ve hedefin birim testleri koşulur; test düşerse mutant "öldü":

- aritmetik: ``+ ↔ -``, ``* ↔ /``, ``// → /``
- karşılaştırma: ``< ↔ <=``, ``> ↔ >=``, ``== ↔ !=``, ``in ↔ not in``
- mantık: ``and ↔ or``, ``not x → x``
- sabit: ``True ↔ False``, sayı ``n → n + 1``

Kullanım (repo kökünden)::

    python backend/scripts/mutasyon.py                 # tüm hedefler, eşik denetimi
    python backend/scripts/mutasyon.py --hedef oee     # tek hedef
    python backend/scripts/mutasyon.py --isci 6 --esik 80

Her işçi ``backend``in geçici bir kopyasında çalışır (kaynak ağaç hiç değişmez). Çıkış kodu:
skor eşiğin altındaysa 1. Hayatta kalan mutantlar satır ve değişiklikle listelenir.
"""

from __future__ import annotations

import argparse
import ast
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue

BACKEND = Path(__file__).resolve().parents[1]

# hedef adı → (kaynak, testler)
HEDEFLER: dict[str, tuple[str, list[str]]] = {
    "oee": ("app/modules/uretim/oee.py", ["tests/test_oee.py", "tests/test_s28_cekirdek_derin.py"]),
    "isemri_durum": ("app/modules/isemri/durum.py", ["tests/test_s4_durum.py"]),
    "talep_durum": ("app/modules/stok/talep_durum.py", ["tests/test_s9_durum.py"]),
    "kalite_durum": ("app/modules/kalite/durum.py", ["tests/test_s10_durum.py"]),
    "izin_durum": ("app/modules/ik/izin_durum.py", ["tests/test_s11_birim.py"]),
    "spc": (
        "app/modules/kalite/spc.py",
        ["tests/test_s26_spc_birim.py", "tests/test_s28_cekirdek_derin.py"],
    ),
    "izin_hakedis": (
        "app/modules/ik/izin_hakedis.py",
        ["tests/test_s26b_birim.py", "tests/test_s28_cekirdek_derin.py"],
    ),
    "egitim_matrisi": (
        "app/modules/isg/egitim_matrisi.py",
        ["tests/test_s26b_birim.py", "tests/test_s28_cekirdek_derin.py"],
    ),
    "zaman": ("app/core/zaman.py", ["tests/test_s27_is_gunu.py"]),
}

_IKILI = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.Div,
    ast.Div: ast.Mult,
    ast.FloorDiv: ast.Div,
}
_KARSI = {
    ast.Lt: ast.LtE,
    ast.LtE: ast.Lt,
    ast.Gt: ast.GtE,
    ast.GtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}


@dataclass(frozen=True)
class Mutant:
    hedef: str
    sira: int
    satir: int
    aciklama: str


def _docstring_mi(dugum: ast.AST, ebeveyn: dict[int, ast.AST]) -> bool:
    e = ebeveyn.get(id(dugum))
    return (
        isinstance(e, ast.Expr) and isinstance(dugum, ast.Constant) and isinstance(dugum.value, str)
    )


def noktalar(agac: ast.AST) -> list[tuple[ast.AST, str]]:
    """Mutasyon uygulanabilecek düğümler (sıra kararlı: ast.walk)."""
    ebeveyn: dict[int, ast.AST] = {}
    for d in ast.walk(agac):
        for c in ast.iter_child_nodes(d):
            ebeveyn[id(c)] = d
    # Dekoratör argümanları (``@dataclass(frozen=True)``, ``@lru_cache(maxsize=1)``) davranışı
    # değiştirmeyen eşdeğer mutant üretir; ölçümü kirletmesin diye dışlanır.
    dekorator: set[int] = set()
    for d in ast.walk(agac):
        if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for dek in d.decorator_list:
                dekorator.update(id(x) for x in ast.walk(dek))
    sonuc: list[tuple[ast.AST, str]] = []
    for d in ast.walk(agac):
        if isinstance(d, ast.BinOp) and type(d.op) in _IKILI:
            sonuc.append((d, f"{type(d.op).__name__} → {_IKILI[type(d.op)].__name__}"))
        elif isinstance(d, ast.Compare):
            for i, op in enumerate(d.ops):
                if type(op) in _KARSI:
                    sonuc.append((d, f"{i}:{type(op).__name__} → {_KARSI[type(op)].__name__}"))
        elif isinstance(d, ast.BoolOp):
            sonuc.append(
                (d, f"{type(d.op).__name__} → {'Or' if isinstance(d.op, ast.And) else 'And'}")
            )
        elif isinstance(d, ast.UnaryOp) and isinstance(d.op, ast.Not):
            sonuc.append((d, "not x → x"))
        elif (
            isinstance(d, ast.Constant) and not _docstring_mi(d, ebeveyn) and id(d) not in dekorator
        ):
            if isinstance(d.value, bool):
                sonuc.append((d, f"{d.value} → {not d.value}"))
            elif isinstance(d.value, (int, float)) and not isinstance(d.value, bool):
                sonuc.append((d, f"{d.value} → {d.value + 1}"))
    return sonuc


def mutasyonlu_kaynak(kaynak: str, sira: int) -> tuple[str, int, str]:
    agac = ast.parse(kaynak)
    d, aciklama = noktalar(agac)[sira]
    if isinstance(d, ast.BinOp):
        d.op = _IKILI[type(d.op)]()
    elif isinstance(d, ast.Compare):
        i = int(aciklama.split(":", 1)[0])
        d.ops[i] = _KARSI[type(d.ops[i])]()
    elif isinstance(d, ast.BoolOp):
        d.op = ast.Or() if isinstance(d.op, ast.And) else ast.And()
    elif isinstance(d, ast.UnaryOp):
        d.op = ast.UAdd()  # ``+x``: bool için x'in kendisi gibi davranır (not kaldırılır)
        d.operand = ast.Call(ast.Name("bool", ast.Load()), [d.operand], [])
    elif isinstance(d, ast.Constant):
        assert isinstance(d.value, (bool, int, float))  # noktalar() yalnız bunları seçer
        d.value = (not d.value) if isinstance(d.value, bool) else d.value + 1
    satir = getattr(d, "lineno", 0)
    return ast.unparse(ast.fix_missing_locations(agac)), satir, aciklama


def _pytest(kok: Path, testler: list[str]) -> int:
    ortam = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *testler,
            "-x",
            "-q",
            "-p",
            "no:cacheprovider",
            "-W",
            "ignore",
        ],
        cwd=kok,
        env=ortam,
        capture_output=True,
        timeout=300,
    )
    return r.returncode


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS mutasyon testi")
    p.add_argument("--hedef", action="append", choices=sorted(HEDEFLER))
    p.add_argument("--isci", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--esik", type=float, default=80.0, help="asgari öldürme yüzdesi")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    secim = a.hedef or sorted(HEDEFLER)

    gorevler: list[Mutant] = []
    kaynaklar: dict[str, str] = {}
    for h in secim:
        kaynak = (BACKEND / HEDEFLER[h][0]).read_text(encoding="utf-8")
        kaynaklar[h] = kaynak
        for i in range(len(noktalar(ast.parse(kaynak)))):
            gorevler.append(Mutant(h, i, 0, ""))

    # Önce temiz koşu: testler mutantsız geçmeli, yoksa ölçüm anlamsız.
    for h in secim:
        if _pytest(BACKEND, HEDEFLER[h][1]) != 0:
            print(f"HATA: {h} testleri mutantsız da düşüyor; önce onları düzeltin.")
            return 2

    kopyalar: Queue[Path] = Queue()
    gecici = Path(tempfile.mkdtemp(prefix="mutasyon-"))
    for n in range(a.isci):
        hedef = gecici / f"isci{n}"
        shutil.copytree(
            BACKEND, hedef, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache")
        )
        kopyalar.put(hedef)

    def koş(m: Mutant) -> tuple[Mutant, bool]:
        kok = kopyalar.get()
        try:
            kaynak_yolu = kok / HEDEFLER[m.hedef][0]
            yeni, satir, aciklama = mutasyonlu_kaynak(kaynaklar[m.hedef], m.sira)
            kaynak_yolu.write_text(yeni, encoding="utf-8")
            try:
                oldu = _pytest(kok, HEDEFLER[m.hedef][1]) != 0
            except subprocess.TimeoutExpired:
                oldu = True  # sonsuz döngü de testin yakaladığı sayılır
            finally:
                kaynak_yolu.write_text(kaynaklar[m.hedef], encoding="utf-8")
            return Mutant(m.hedef, m.sira, satir, aciklama), oldu
        finally:
            kopyalar.put(kok)

    try:
        with ThreadPoolExecutor(max_workers=a.isci) as ex:
            sonuclar = list(ex.map(koş, gorevler))
    finally:
        shutil.rmtree(gecici, ignore_errors=True)

    toplam_olen = sum(1 for _, o in sonuclar if o)
    print(f"\n{'hedef':16s} {'mutant':>6s} {'ölen':>5s} {'skor':>6s}")
    for h in secim:
        hs = [(m, o) for m, o in sonuclar if m.hedef == h]
        olen = sum(1 for _, o in hs if o)
        print(f"{h:16s} {len(hs):6d} {olen:5d} {100 * olen / max(len(hs), 1):5.1f}%")
    skor = 100 * toplam_olen / max(len(sonuclar), 1)
    print(f"{'TOPLAM':16s} {len(sonuclar):6d} {toplam_olen:5d} {skor:5.1f}%  (eşik {a.esik:.0f}%)")
    kalan = [m for m, o in sonuclar if not o]
    if kalan:
        print("\nHayatta kalan mutantlar:")
        for m in sorted(kalan, key=lambda x: (x.hedef, x.satir)):
            print(f"  {HEDEFLER[m.hedef][0]}:{m.satir}  {m.aciklama}")
    return 0 if skor >= a.esik else 1


if __name__ == "__main__":
    raise SystemExit(main())
