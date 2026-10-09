"""Testa o modulo FTIR do PAT contra os 59 espectros reais do figshare.

Fonte: figshare 24593022 (CC-BY-4.0), FTIR de polímeros as-received.
Formato dos arquivos: linha 1 = comentario da amostra, linha 2 = header "cm-1,%T",
depois pares wavenumber (descendente, 4000 -> 400) e %T.

Ponto em teste: o PAT pede ABSORBANCIA, mas o instrumento exporta TRANSMITANCIA.
A conversao A = -log10(T/100) existe na docstring mas nao e feita pela ferramenta.
Este script mede as duas coisas -- quantos traços passam crus e quantos passam
apos a conversao -- para dimensionar o atrito real.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.structure import analyse_ftir  # noqa: E402

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/ftir")

rows = []
for f in sorted(DATA.glob("FTIR_*.csv")):
    text = f.read_text(errors="replace")
    lines = [ln for ln in text.replace("\r\n", "\n").split("\n") if ln.strip()]
    # skip the comment line and the "cm-1,%T" header
    data = []
    for ln in lines:
        parts = ln.split(",")
        if len(parts) < 2:
            continue
        try:
            data.append((float(parts[0]), float(parts[1])))
        except ValueError:
            continue
    if len(data) < 50:
        continue
    arr = np.array(data)
    wn, Tpct = arr[:, 0], arr[:, 1]

    raw_result = conv_result = None
    raw_err = conv_err = None
    try:
        raw_result = analyse_ftir(wn, Tpct)  # transmittance, as the file has it
    except Exception as exc:  # noqa: BLE001
        raw_err = f"{type(exc).__name__}: {exc}"

    # Convert to absorbance, the unit the tool documents.
    with np.errstate(divide="ignore", invalid="ignore"):
        A = -np.log10(np.clip(Tpct, 1e-6, None) / 100.0)
    try:
        conv_result = analyse_ftir(wn, A)
    except Exception as exc:  # noqa: BLE001
        conv_err = f"{type(exc).__name__}: {exc}"

    rows.append(
        {
            "file": f.name,
            "points": int(wn.size),
            "T_min_pct": round(float(Tpct.min()), 2),
            "raw_ok": raw_err is None,
            "raw_err": raw_err,
            "raw_peaks": None if raw_result is None else len(raw_result.detected_peaks),
            "conv_ok": conv_err is None,
            "conv_err": conv_err,
            "conv_peaks": None if conv_result is None else len(conv_result.detected_peaks),
        }
    )

total = len(rows)
raw_ok = sum(r["raw_ok"] for r in rows)
conv_ok = sum(r["conv_ok"] for r in rows)
print(f"espectros analisados: {total}")
print(f"  passaram como esta (transmitancia): {raw_ok}/{total}")
print(f"  passaram apos A = -log10(T/100)   : {conv_ok}/{total}")
print()
print(f"{'arquivo':<22} {'Tmin%':>7} {'cru':>5} {'conv':>5}  erro")
for r in rows:
    err = (r["raw_err"] or "")[:44]
    print(
        f"{r['file']:<22} {r['T_min_pct']:>7.2f} "
        f"{r['raw_peaks'] if r['raw_peaks'] is not None else '-':>5} "
        f"{r['conv_peaks'] if r['conv_peaks'] is not None else '-':>5}  {err}"
    )
