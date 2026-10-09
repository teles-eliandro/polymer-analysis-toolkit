"""Run the PAT DSC detector over the full figshare 24462004 set (116 .tri files).

Compares recovered Tg / Tm against literature ranges for each polymer family
and reports where the detector lands outside the published window.
"""

from __future__ import annotations

import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.io.tri_reader import read_tri  # noqa: E402
from app.core.thermal import analyse_dsc  # noqa: E402

# Published Tg / Tm windows (C) for the polymers in this dataset.
# Ranges are deliberately generous -- the point is to catch gross failures
# (a Tg reported on a melting flank, a sign flip), not to grade the detector.
LITERATURE = {
    "PS": ((80, 110), None),
    "SAN": ((95, 115), None),
    "ABS": ((95, 115), None),
    "PMMA": ((95, 115), None),
    "PVC": ((60, 90), None),
    "PVAc": ((25, 45), None),
    "PVOH": ((60, 95), None),
    "PU": ((-60, -10), None),
    "PC": ((140, 155), None),
    "PET": ((65, 85), (240, 265)),
    "PBT": ((30, 60), (215, 235)),
    "PK": ((70, 120), (215, 240)),
    "PLA": ((50, 70), (160, 180)),
    "PLLA": ((50, 75), (165, 185)),
    "PMMA": ((95, 115), None),
    "PE": ((-130, -80), (100, 140)),
    "PE-NEW": ((-130, -80), (100, 140)),
    "PMMA": ((95, 115), None),
    "PP": ((-20, 10), (150, 175)),
    "POM": ((-70, -50), (165, 185)),
    "PHB": ((-10, 20), (160, 185)),
    "PA6": ((40, 70), (210, 230)),
    "NYLON6": ((40, 70), (210, 230)),
    "NYLON66": ((40, 70), (250, 270)),
    "Nylon6": ((40, 70), (210, 230)),
    "Nylon66": ((40, 70), (250, 270)),
    "PAN": ((80, 110), None),
    "EVA": ((-40, 0), (60, 100)),
    "EVOH": ((50, 80), (150, 190)),
}


def family_of(name: str) -> str:
    stem = os.path.basename(name).replace(".tri", "")
    stem = re.sub(r"[-_](AR|Cryo|cryo|CRYO|Cyro)([-_]dried)?$", "", stem)
    stem = re.sub(r"[-_]dried$", "", stem)
    return re.sub(r"\d+$", "", stem).upper().rstrip("-")


def in_window(value, window) -> bool:
    if window is None:
        return True
    if value is None:
        return True  # an event that legitimately is not present
    return window[0] <= value <= window[1]


def main() -> None:
    root = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dsc116"
    files = sorted(glob.glob(os.path.join(root, "*.tri")))
    print(f"analisando {len(files)} arquivos .tri\n")

    rows = []
    read_fail = []
    for path in files:
        try:
            tri = read_tri(path)
            T = tri.temperature
            hf = tri.heat_flow
            if T is None or hf is None:
                read_fail.append((path, "sem canal T ou heat flow"))
                continue
            proc = tri.procedure or ""
            m = re.search(r"Ramp\s+([\d.]+)", proc)
            rate = float(m.group(1)) if m else 10.0
            res = analyse_dsc(T, hf, heating_rate=rate)
            rows.append(
                {
                    "file": os.path.basename(path),
                    "family": family_of(path),
                    "n": len(T),
                    "rate": rate,
                    "Tg": res.Tg,
                    "Tm": res.Tm,
                    "dHm": res.delta_Hm,
                    "conf": getattr(res, "Tg_confidence", None),
                    "unc": getattr(res, "Tg_uncertainty", None),
                }
            )
        except Exception as exc:  # noqa: BLE001
            read_fail.append((path, f"{type(exc).__name__}: {exc}"))

    print(f"lidos: {len(rows)}   falhas de leitura: {len(read_fail)}")
    for p, why in read_fail[:10]:
        print(f"  FALHA {os.path.basename(p)}: {why}")

    # --- literature check -------------------------------------------------
    print("\n=== fora da janela de literatura ===")
    bad_tg = []
    bad_tm = []
    for r in rows:
        tg_w, tm_w = LITERATURE.get(r["family"], (None, None))
        if not in_window(r["Tg"], tg_w):
            bad_tg.append(r)
        if not in_window(r["Tm"], tm_w):
            bad_tm.append(r)

    print(f"\nTg fora da janela: {len(bad_tg)}/{len(rows)}")
    for r in bad_tg:
        w = LITERATURE.get(r["family"], (None, None))[0]
        print(f"  {r['file']:<24} fam={r['family']:<8} Tg={r['Tg']}  esperado {w}")

    print(f"\nTm fora da janela: {len(bad_tm)}/{len(rows)}")
    for r in bad_tm:
        w = LITERATURE.get(r["family"], (None, None))[1]
        print(f"  {r['file']:<24} fam={r['family']:<8} Tm={r['Tm']}  esperado {w}")

    # --- summary per family ----------------------------------------------
    print("\n=== resumo por família ===")
    fams: dict[str, list] = {}
    for r in rows:
        fams.setdefault(r["family"], []).append(r)
    for fam in sorted(fams):
        g = fams[fam]
        tgs = [r["Tg"] for r in g if r["Tg"] is not None]
        tms = [r["Tm"] for r in g if r["Tm"] is not None]
        tg_s = f"{min(tgs):.1f}..{max(tgs):.1f}" if tgs else "-"
        tm_s = f"{min(tms):.1f}..{max(tms):.1f}" if tms else "-"
        print(f"  {fam:<9} n={len(g):<3} Tg {tg_s:<16} Tm {tm_s}")

    # --- confidence coverage ---------------------------------------------
    with_conf = sum(1 for r in rows if r["conf"] is not None)
    print(f"\nconfiança de Tg presente em {with_conf}/{len(rows)}")


if __name__ == "__main__":
    main()
