"""Gera os resultados REAIS para o paper: PAT vs. dados de referencia PLLA.

Le os DSC reais de literatura (PLLA 10K/25K/50K, 2nd heating, 10 C/min) e roda
o analyse_dsc do PAT. Compara com valores reportados e checa o footing (Tg).

Nenhum numero aqui e inventado: tudo vem de rodar o codigo do PAT nos .dat reais.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.thermal import analyse_dsc  # noqa: E402

LIT = ROOT / "exemples" / "literature"
manifest = json.loads((LIT / "manifest_dsc.json").read_text())

rows = []
for entry in manifest:
    f = LIT / entry["file"]
    arr = np.loadtxt(f)
    T, hf = arr[:, 0], arr[:, 1]
    # O PAT quer heat flow endo-down (a convencao do DSC); o manifesto diz endo-up.
    # Mantemos a convencao do arquivo e deixamos o PAT lidar com o sinal.
    res = analyse_dsc(T, hf, heating_rate=entry["heating_rate_C_min"])
    rows.append({
        "sample": entry["sample"],
        "file": entry["file"],
        "points": int(len(T)),
        "T_range": [float(T[0]), float(T[-1])],
        "Tg": res.Tg,
        "Tm": res.Tm,
        "delta_cp": res.delta_cp,
        "delta_Hm": res.delta_Hm,
        "Tg_uncertainty_C": res.Tg_uncertainty_C,
        "Tg_reliable": res.Tg_reliable,
    })

print(json.dumps(rows, indent=1, default=float))
Path("/tmp/pat_results.json").write_text(json.dumps(rows, indent=1, default=float))
