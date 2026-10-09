#!/usr/bin/env python3
"""Le cada CSV de exemples/datasets/ e passa pela API real do PAT.

Prova que os arquivos carregam e produzem numero — nao basta existirem.
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

DATA = ROOT / "exemples" / "datasets"
client = TestClient(app)


def read_cols(path: Path, skip_comments: bool = True):
    with path.open(encoding="utf-8") as fh:
        lines = [ln for ln in fh if not (skip_comments and ln.startswith("#"))]
    rows = list(csv.reader(lines))
    header, body = rows[0], rows[1:]
    return header, body


def col(header, body, name):
    i = header.index(name)
    out = []
    for r in body:
        try:
            out.append(float(r[i]))
        except (ValueError, IndexError):
            pass
    return out


def check(label, ok, detail):
    mark = "OK  " if ok else "FALHA"
    print(f"  [{mark}] {label}: {detail}")
    return ok


results = []

# --- Massa molar -----------------------------------------------------------
fp = DATA / "molar_mass_gpc_pla.csv"
h, b = read_cols(fp)
masses = col(h, b, "molar_mass_g_per_mol")
# O modulo pede massas + fracoes. A tabela do ASTRA so da a massa de cada
# slice; sem as fracoes, uma distribuicao uniforme e a unica leitura
# defensavel. Normalise=true deixa o modulo fechar a soma.
r = client.post(
    "/api/v1/molecular/calc",
    json={
        "masses": masses,
        "weight_fractions": [1.0] * len(masses),
        "normalise": True,
    },
)
body = r.json() if r.status_code == 200 else {}
ok = r.status_code == 200 and body.get("Mn") is not None
results.append(
    check(
        "massa molar",
        ok,
        f"HTTP {r.status_code}  Mn={body.get('Mn'):.0f}  Mw={body.get('Mw'):.0f}  D={body.get('dispersity'):.3f}"
        if ok
        else f"HTTP {r.status_code} {r.text[:120]}",
    )
)

# --- DSC -------------------------------------------------------------------
fp = DATA / "dsc_plla_second_heating.csv"
h, b = read_cols(fp)
r = client.post(
    "/api/v1/thermal/dsc",
    json={
        "temperature": col(h, b, "temperature_C"),
        "heat_flow": col(h, b, "heat_flow_W_per_g"),
        "heating_rate": 10.0,
        "ref_enthalpy_J_g": 93.0,
        "sample_name": "PLLA_50K",
    },
)
body = r.json() if r.status_code == 200 else {}
ok = r.status_code == 200 and (body.get("Tg") is not None or body.get("Tm") is not None)
results.append(
    check(
        "DSC",
        ok,
        f"HTTP {r.status_code}  Tg={body.get('Tg')}  Tm={body.get('Tm')}  verdict={body.get('comparison', {}).get('Tm', {}).get('verdict')}"
        if ok
        else f"HTTP {r.status_code} {r.text[:120]}",
    )
)

# --- TGA -------------------------------------------------------------------
fp = DATA / "tga_eva_nitrogen.csv"
h, b = read_cols(fp)
r = client.post(
    "/api/v1/thermal/tga",
    json={"temperature": col(h, b, "temperature_C"), "mass_pct": col(h, b, "mass_pct")},
)
body = r.json() if r.status_code == 200 else {}
ok = r.status_code == 200 and body.get("Td_5pct") is not None
results.append(
    check(
        "TGA",
        ok,
        f"HTTP {r.status_code}  Td5%={body.get('Td_5pct')}  Td10%={body.get('Td_10pct')}  residual={body.get('residue_pct')}"
        if ok
        else f"HTTP {r.status_code} {r.text[:120]}",
    )
)

# --- FTIR ------------------------------------------------------------------
# O arquivo cru e transmitancia (o instrumento exporta %T). O modulo pede
# absorbancia e recusa %T com uma mensagem explicita — o guard funcionando.
# A conversao A = -log10(T/100) e feita aqui, pelo usuario, nao escondida.
fp = DATA / "ftir_pet_transmittance.csv"
h, b = read_cols(fp)
trans = col(h, b, "transmittance_pct")
absor = [max(-math.log10(t / 100.0), 0.0) for t in trans if 0 < t <= 100]
wn = col(h, b, "wavenumber_cm-1")[: len(absor)]
r = client.post(
    "/api/v1/structure/ftir",
    json={"wavenumber": wn, "absorbance": absor},
)
body = r.json() if r.status_code == 200 else {}
peaks = body.get("detected_peaks") or []
ok = r.status_code == 200 and len(peaks) > 0
results.append(
    check(
        "FTIR",
        ok,
        f"HTTP {r.status_code}  {len(peaks)} picos  {len(body.get('matches') or [])} atribuicoes  primeiros={peaks[:4]}" if ok else f"HTTP {r.status_code} {r.text[:120]}",
    )
)

# --- XRD -------------------------------------------------------------------
fp = DATA / "xrd_plla_waxs.csv"
h, b = read_cols(fp)
r = client.post(
    "/api/v1/structure/xrd",
    json={
        "two_theta": col(h, b, "two_theta_deg"),
        "intensity": col(h, b, "intensity_counts"),
    },
)
body = r.json() if r.status_code == 200 else {}
peaks = body.get("peaks_two_theta") or []
ok = r.status_code == 200 and len(peaks) > 0
results.append(
    check(
        "XRD",
        ok,
        f"HTTP {r.status_code}  {len(peaks)} picos  d={body.get('d_spacing_angstrom', [])[:3]}" if ok else f"HTTP {r.status_code} {r.text[:120]}",
    )
)

# --- Mecanica --------------------------------------------------------------
fp = DATA / "mechanical_tensile_SYNTHETIC.csv"
h, b = read_cols(fp)
r = client.post(
    "/api/v1/mechanical/tensile",
    json={"strain_pct": col(h, b, "strain_pct"), "stress_MPa": col(h, b, "stress_MPa")},
)
body = r.json() if r.status_code == 200 else {}
ok = r.status_code == 200 and body.get("E_MPa") is not None
results.append(
    check(
        "mecanica",
        ok,
        f"HTTP {r.status_code}  E={body.get('E_MPa'):.1f} MPa  sigma_max={body.get('stress_max_MPa'):.2f} MPa" if ok else f"HTTP {r.status_code} {r.text[:120]}",
    )
)

# --- Reologia --------------------------------------------------------------
fp = DATA / "rheology_frequency_sweep_SYNTHETIC.csv"
h, b = read_cols(fp)
r = client.post(
    "/api/v1/rheology/sweep",
    json={
        "omega": col(h, b, "omega_rad_per_s"),
        "G_prime": col(h, b, "G_prime_Pa"),
        "G_double_prime": col(h, b, "G_double_prime_Pa"),
    },
)
body = r.json() if r.status_code == 200 else {}
ok = r.status_code == 200 and body.get("cross_over_freq") is not None
results.append(
    check(
        "reologia",
        ok,
        f"HTTP {r.status_code}  crossover={body.get('cross_over_freq'):.3g} rad/s  G0={body.get('plateau_modulus_G0')}" if ok else f"HTTP {r.status_code} {r.text[:120]}",
    )
)

print(f"\n{sum(results)}/{len(results)} modulos responderam com numero")
sys.exit(0 if all(results) else 1)
