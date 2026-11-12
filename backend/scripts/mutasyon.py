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
import signal
import subprocess
import sys
import tempfile
import time
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
    "zaman": (
        "app/core/zaman.py",
        ["tests/test_s27_is_gunu.py", "tests/test_zaman_gun_araligi.py"],
    ),
    "finans_hesap": ("app/modules/finans/hesap.py", ["tests/test_s29_finans_birim.py"]),
    "fatura_durum": ("app/modules/finans/durum.py", ["tests/test_s29_finans_birim.py"]),
    "cizelge": ("app/modules/planlama/cizelge.py", ["tests/test_s30_cizelge_birim.py"]),
    "mrp": ("app/modules/satis/mrp.py", ["tests/test_s31_mrp_birim.py"]),
    "satis_durum": ("app/modules/satis/durum.py", ["tests/test_s31_mrp_birim.py"]),
    "esg_hesap": ("app/modules/esg/hesap.py", ["tests/test_s32_esg_birim.py"]),
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


# Bir mutant döngü koşulunu bozup sınırsız bellek ayırabilir: ``cizelge`` L121 ``and → or``
# biten işi pencereye sıfır uzunluklu parça ekleyerek sonsuza dek döndürür (yerelde ~55 MB/sn).
# Eskiden tek sınır 300 sn'lik süreydi; o sürede alt süreç runner'ın 16 GB belleğini doldurup
# işi 5-6. dakikada SIGTERM (143) ya da "runner lost communication" ile düşürüyordu (2026-11-13
# teşhisi). Artık her pytest alt sürecinin belleği tavanlı (aşınca MemoryError / ölüm = test
# düştü = mutant öldü) ve süre sınırı hedefin temiz koşusundan türetiliyor.
BELLEK_TAVANI = 4 * 1024**3  # POSIX'te sanal adres alanı (RLIMIT_AS), Windows'ta süreç belleği
SURE_KATSAYI = 10
SURE_TABAN = 60.0


def _posix_bellek_tavani() -> None:  # pragma: no cover - yalnız POSIX alt süreçte koşar
    if sys.platform != "win32":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (BELLEK_TAVANI, BELLEK_TAVANI))


def _windows_tutamac_kapat(tutamac: int | None) -> None:  # pragma: no cover - yalnız Windows
    if tutamac:
        import ctypes

        ctypes.WinDLL("kernel32").CloseHandle(ctypes.c_void_p(tutamac))


def _windows_bellek_tavani(pid: int) -> int | None:  # pragma: no cover - yalnız Windows
    """Süreci bellek sınırlı bir Job Object'e koyar; dönen iş tutamacı sonra kapatılır."""
    import ctypes
    from ctypes import wintypes

    class Temel(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class Genis(ctypes.Structure):
        _fields_ = [
            ("Temel", Temel),
            ("IoSayac", ctypes.c_uint64 * 6),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.OpenProcess.restype = wintypes.HANDLE
    is_ = k32.CreateJobObjectW(None, None)
    bilgi = Genis()
    bilgi.Temel.LimitFlags = 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
    bilgi.ProcessMemoryLimit = BELLEK_TAVANI
    if not is_ or not k32.SetInformationJobObject(
        wintypes.HANDLE(is_), 9, ctypes.byref(bilgi), ctypes.sizeof(bilgi)
    ):
        _windows_tutamac_kapat(is_)
        return None
    surec = k32.OpenProcess(0x0100 | 0x0001, False, pid)  # SET_QUOTA | TERMINATE
    atandi = bool(surec) and k32.AssignProcessToJobObject(
        wintypes.HANDLE(is_), wintypes.HANDLE(surec)
    )
    _windows_tutamac_kapat(surec)
    if not atandi:
        _windows_tutamac_kapat(is_)
        return None
    return int(is_)


def _pytest(kok: Path, testler: list[str], sure: float = 300.0) -> int:
    """Testleri koşar; çıkış kodu. Süre aşımında ``subprocess.TimeoutExpired`` yükselir."""
    ortam = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    komut = [
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
    ]
    posix = os.name == "posix"
    with subprocess.Popen(
        komut,
        cwd=kok,
        env=ortam,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=_posix_bellek_tavani if posix else None,
    ) as p:
        is_tutamaci = None if posix else _windows_bellek_tavani(p.pid)
        try:
            return p.wait(timeout=sure)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            raise
        finally:
            _windows_tutamac_kapat(is_tutamaci)


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

    # Önce temiz koşu: testler mutantsız geçmeli, yoksa ölçüm anlamsız. Süresi, o hedefin
    # mutantlarına tanınan süreyi belirler (sonsuz döngü 300 sn yerine bu sürede kesilir).
    sure_siniri: dict[str, float] = {}
    for h in secim:
        bas = time.monotonic()
        if _pytest(BACKEND, HEDEFLER[h][1]) != 0:
            print(f"HATA: {h} testleri mutantsız da düşüyor; önce onları düzeltin.")
            return 2
        sure_siniri[h] = max(SURE_TABAN, SURE_KATSAYI * (time.monotonic() - bas))

    kopyalar: Queue[Path] = Queue()
    gecici = Path(tempfile.mkdtemp(prefix="mutasyon-"))
    for n in range(a.isci):
        hedef = gecici / f"isci{n}"
        shutil.copytree(
            BACKEND, hedef, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache")
        )
        kopyalar.put(hedef)

    # Dış sinyalle kesilirse hangi mutantların koştuğu görünsün (bkz. BELLEK_TAVANI notu).
    suren: dict[tuple[str, int], float] = {}
    biten = [0]

    def kesildi(numara: int, _kare: object) -> None:
        simdi = time.monotonic()
        print(f"\nSİNYAL {numara}: {biten[0]}/{len(gorevler)} bitti; koşanlar:", flush=True)
        for (h, sira), bas in list(suren.items()):
            print(f"  {h}#{sira} {simdi - bas:.0f} sn", flush=True)
        raise SystemExit(128 + numara)

    signal.signal(signal.SIGTERM, kesildi)

    def koş(m: Mutant) -> tuple[Mutant, bool]:
        kok = kopyalar.get()
        suren[(m.hedef, m.sira)] = time.monotonic()
        try:
            kaynak_yolu = kok / HEDEFLER[m.hedef][0]
            yeni, satir, aciklama = mutasyonlu_kaynak(kaynaklar[m.hedef], m.sira)
            kaynak_yolu.write_text(yeni, encoding="utf-8")
            try:
                kod = _pytest(kok, HEDEFLER[m.hedef][1], sure_siniri[m.hedef])
                oldu = kod != 0
            except subprocess.TimeoutExpired:
                oldu = True  # sonsuz döngü de testin yakaladığı sayılır
                print(f"  süre aşımı: {m.hedef}#{m.sira} {aciklama} (satır {satir})", flush=True)
            finally:
                kaynak_yolu.write_text(kaynaklar[m.hedef], encoding="utf-8")
            return Mutant(m.hedef, m.sira, satir, aciklama), oldu
        finally:
            suren.pop((m.hedef, m.sira), None)
            biten[0] += 1
            if biten[0] % 25 == 0:
                print(f"{biten[0]}/{len(gorevler)} mutant", flush=True)
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
