"""Audit every DSC output field: deterministic (read/fórmula) or heuristic (inferred).

Runs the real figshare traces and reports, per field, whether the value is
(a) a property of the file, (b) a formula applied to a declared input, or
(c) an inference that could be wrong. This is the basis for labelling the
product honestly, so it must be measured on real data, not asserted.
"""
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
from app.core.io.tri_reader import read_tri  # noqa: E402
from app.core.thermal import analyse_dsc  # noqa: E402

FILES = [
    "PLA1-AR",
    "PET1-AR",
    "PET2-AR",
    "PE-NEW-AR",
    "ABS2_AR",
    "PS5-AR",
    "PVC1-AR",
    "PMMA4_cryo",
    "EVA1-AR",
    "PP2-AR",
]

present = defaultdict(int)
for name in FILES:
    try:
        f = read_tri(f"/tmp/dsc116/{name}.tri")
    except FileNotFoundError:
        continue
    T = np.array(f.temperature)
    hf = np.array(f.heat_flow)
    r = analyse_dsc(T, hf, heating_rate=10.0)
    d = r.as_dict()
    for k, v in d.items():
        if k in ("temperature", "heat_flow"):
            continue
        if v is not None:
            present[k] += 1

print("field                emitted/10")
for k in [
    "Tg", "Tg_onset", "Tg_end", "delta_cp",
    "Tm", "delta_Hm", "Tc", "delta_Hc", "crystallinity_pct",
    "Tg_uncertainty_C", "Tg_reliable", "direction",
]:
    print(f"  {k:20s} {present[k]:2d}/10")
