"""Roda o PAT contra TODOS os traços DSC reais disponíveis e compara com o esperado.

Fonte: Zenodo 10.5281/zenodo.17288962 (CC-BY-4.0) -- DSC de PLA com diferentes
taticidades e massas molares. 16 traços: PLLA/PDLA/PDLLA x 10K/25K/50K x
{convencional, MDSC}. Os traços usados antes eram só 3 (PLLA x 3), o que é base
estreita demais para dizer qualquer coisa sobre o método.

O lote traz as três taticidades, o que dá um contraste que os 3 traços de PLLA
não davam: PLLA e PDLA são semicristalinos (têm Tm), PDLLA é amorfo (não tem).
Um detector que funcione nos dois casos é outra coisa de um que só acerta no
caso fácil.

Cada .txt é UTF-16LE com cabeçalho de metadados e depois:
    Time (min) \t Temperature (C) \t Heat Flow (mW) \t purge flow

Heat flow em mW precisa da massa para virar W/g -- e a massa está declarada no
próprio header ("Size\t3.90000\tmg"), então é lida, não assumida.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.thermal import analyse_dsc  # noqa: E402

DATA = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/dsc_all")


def parse(path: Path):
    raw = path.read_bytes().decode("utf-16-le", errors="replace")
    lines = raw.split("\r\n")

    mass_mg = None
    rate = None
    # The method block lists several ramps. Only the last one applies to the
    # segment the file's data actually holds: a modulated run heats to 190 C at
    # 10 C/min first (to erase thermal history) and *then* holds at 2 C/min for
    # the Cp measurement, and the file records only that 2 C/min segment.
    # Taking the first match gave 10 C/min for a trace driven at 2, which put
    # PLLA_50K's Tg at 51 C against 88 C from the conventional run.
    ramps = []
    for ln in lines[:80]:
        m = re.match(r"Size\t([\d.]+)\tmg", ln)
        if m:
            mass_mg = float(m.group(1))
        m = re.match(r"OrgMethod\t\d+: Ramp ([\d.]+) .C/min to ([\d.]+) .C", ln)
        if m:
            ramps.append((float(m.group(1)), float(m.group(2))))
    if ramps:
        # The last listed ramp is the one the recorded segment belongs to.
        rate = ramps[-1][0]

    # Data rows start after the signal-name block. Two layouts are present:
    # the conventional runs carry 4 signals (time, T, heat flow, purge) and the
    # modulated ones carry 13. Column 1 (Temperature) and column 2 (Heat Flow)
    # are the same signal in both, so the parser keys off the count rather than
    # assuming one shape.
    rows = []
    for ln in lines:
        parts = ln.split()
        if len(parts) in (4, 13):
            try:
                rows.append([float(p) for p in parts])
            except ValueError:
                continue
    arr = np.array(rows)
    return arr, mass_mg, rate


results = []
for f in sorted(DATA.rglob("*.txt")):
    arr, mass_mg, rate = parse(f)
    if arr.size == 0 or mass_mg is None:
        continue
    t_min, T_C, hf_mW = arr[:, 0], arr[:, 1], arr[:, 2]

    # mW -> W/g
    hf_Wg = hf_mW / 1000.0 / (mass_mg / 1000.0)

    # Isolate the LAST heating ramp: the protocol is heat-cool-heat, and the
    # second heating is the one that erases thermal history. Temperature rises
    # during a heating segment, so split on the descending parts.
    rising = np.diff(T_C) > 0
    # find the last long contiguous rising run
    runs, start = [], None
    for i, r in enumerate(rising):
        if r and start is None:
            start = i
        elif not r and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(rising)))
    runs = [r for r in runs if r[1] - r[0] > 200]
    if not runs:
        continue
    a, b = runs[-1]
    T_seg = T_C[a : b + 1]
    hf_seg = hf_Wg[a : b + 1]

    # Instrument convention here is exotherm-UP, so an endotherm (melting) points
    # down; the analyser expects endothermic events pointing up.
    hf_seg = -hf_seg

    r = analyse_dsc(T_seg, hf_seg, heating_rate=rate or 10.0)

    sample = f.stem.replace("_DSC_standard", "").replace("_MDSC", " (MDSC)")
    is_amorphous = "PDLLA" in f.stem
    results.append(
        {
            "sample": sample,
            "file": f.name,
            "points": int(T_seg.size),
            "mass_mg": mass_mg,
            "rate": rate,
            "T_range": [round(float(T_seg[0]), 1), round(float(T_seg[-1]), 1)],
            "expects_melting": not is_amorphous,
            "Tg": None if r.Tg is None else round(float(r.Tg), 2),
            "Tm": None if r.Tm is None else round(float(r.Tm), 2),
            "dHm": None if r.delta_Hm is None else round(float(r.delta_Hm), 2),
            "Tg_unc": None if r.Tg_uncertainty_C is None else round(float(r.Tg_uncertainty_C), 2),
            "Tg_rel": r.Tg_reliable,
        }
    )

print(json.dumps(results, indent=1))
Path("/tmp/pat_all16.json").write_text(json.dumps(results, indent=1))
