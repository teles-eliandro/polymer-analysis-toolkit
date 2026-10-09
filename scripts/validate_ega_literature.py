"""TGA-FTIR EGA: tratamento dos dados + comparacao com a literatura.

ESTRATEGIA DE VALIDACAO
-----------------------
A descricao do dataset nao informa taxa de aquecimento nem atmosfera, entao
Td absoluto NAO e comparavel com a literatura (Td desloca 30-60 C com a taxa:
Td(1 C/min) < Td(10 C/min) < Td(20 C/min), e ~50-80 C mais alto em N2 que em ar
para a maioria dos polimeros).

O que E comparavel, porque independe da taxa:
  1. RESIDUO a 700 C em N2 -- propriedade intrinseca do material (quanto
     carbono/inerte sobra). Esta e a comparacao mais forte disponivel.
  2. T_peak do DTG relativo (ordem de estabilidade entre familias).
  3. PERFIL de estagios (1 vs 2 estagios) -- PVC e EVA devem ter 2.

Valores de referencia de residuo a 700-800 C em N2:
  PE       ~0 %      (despolimeriza/volatiliza quase totalmente)
  PP       ~0 %
  PMMA     ~0-2 %    (despolimeriza para monomer)
  PS       ~0-2 %
  PVAc     ~2-5 %
  EVA      ~0-5 %    (depende do teor de VA)
  EVOH     ~0-5 %
  Nylon-6  ~0-3 %
  Nylon-66 ~0-5 %
  PU       ~2-10 %
  PHB      ~0-5 %
  PVOH     ~2-8 %    (deixa residuo carbonoso parcial)
  PVC      ~10-20 %  (perde HCl, deixa esqueleto carbonoso)
  PAN      ~40-55 %  (cicliza -> escada de carbono, residuo ALTO)
  SAN      ~0-3 %

Fontes: Levchik & Weil (PVC), Grassie & Scott "Polymer Degradation and
Stabilisation", Beyler & Hirschler (SFPE Handbook, cap. 7), ASTM E2550/E1131.
"""

import csv
import glob
import os
import sys

import numpy as np

sys.path.insert(0, "/home/hermes/projects/polymer-analysis-toolkit/backend")
from app.core.thermal import analyse_tga

# familia -> (residuo_min, residuo_max, estagios_esperados)
LIT = {
    "PE":    (0, 5, 1),
    "PP":    (0, 5, 1),
    "PMMA":  (0, 3, 1),
    "PS":    (0, 3, 1),
    "PVAc":  (0, 8, 2),
    "EVA":   (0, 8, 2),
    "EVOH":  (0, 8, 2),
    "Nylon": (0, 5, 1),
    "PU":    (0, 12, 2),
    "PHB":   (0, 8, 1),
    "PVOH":  (0, 10, 2),
    "PVC":   (8, 25, 2),
    "PAN":   (30, 60, 1),   # cicliza -> escada de carbono; 30-60 % na literatura
    "SAN":   (0, 5, 1),
}


def family(name):
    base = name.split()[0].upper()
    if base.startswith("NYLON"):
        return "Nylon"
    for fam in sorted(LIT, key=len, reverse=True):
        if base.startswith(fam):
            return fam
    return None


def read_pair(path):
    T, W = [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.reader(fh)
        next(rdr)
        units = next(rdr)
        tcol = wcol = None
        for i, c in enumerate(units):
            c = c.strip().lower()
            if c.startswith("temp") and "c" in c:
                tcol = i
            if "weight" in c or "mass" in c:
                wcol = i
        if tcol is None or wcol is None:
            return None, None
        for row in rdr:
            if len(row) <= max(tcol, wcol):
                continue
            try:
                T.append(float(row[tcol]))
                W.append(float(row[wcol]))
            except (ValueError, IndexError):
                continue
    return np.asarray(T, float), np.asarray(W, float)


def main():
    files = sorted(glob.glob("/tmp/tga_ega/*EGA.csv"))
    print(f"{len(files)} arquivos\n")
    print(f"{'arquivo':<20} {'res%':>7} {'lit res':>12} {'':<3} {'Tmax_rate':>9} "
          f"{'passos':>6} {'esp':>4} {'':<3} {'n':>5}")
    print("-" * 95)

    ok_res = tot_res = 0
    ok_st = tot_st = 0
    neg = []
    recs = []

    for path in files:
        name = os.path.basename(path)
        T, W = read_pair(path)
        if T is None or len(T) < 100:
            print(f"{name:<20} FALHA LEITURA")
            continue
        res = analyse_tga(T, W)
        fam = family(name)
        r = res.residue_pct
        steps = len(res.steps) if res.steps else 0
        tmr = res.T_max_rate

        if r < 0:
            neg.append((name, r))
        mark_r = ""
        if fam and fam in LIT:
            lo, hi, _ = LIT[fam]
            tot_res += 1
            if lo <= r <= hi:
                ok_res += 1
                mark_r = "OK"
            else:
                mark_r = "FORA"
        exp_st = LIT[fam][2] if fam in LIT else None
        mark_s = ""
        if exp_st is not None:
            tot_st += 1
            if steps == exp_st:
                ok_st += 1
                mark_s = "OK"
            else:
                mark_s = "FORA"
        recs.append((name, fam, r, tmr, steps))
        lit = f"{LIT[fam][0]}-{LIT[fam][1]}%" if fam in LIT else "-"
        fmt = lambda v: f"{v:9.1f}" if v is not None else "        -"
        print(f"{name:<20} {r:7.2f} {lit:>12} {mark_r:<3} {fmt(tmr)} "
              f"{steps:>6} {str(exp_st):>4} {mark_s:<3} {len(T):>5}")

    print()
    print("=== COMPARACOES INDEPENDENTES DE TAXA DE AQUECIMENTO ===")
    print(f"  Residuo dentro da literatura: {ok_res}/{tot_res}")
    print(f"  Numero de estagios correto  : {ok_st}/{tot_st}")
    print()
    print("=== ANOMALIAS ===")
    print(f"  Residuo NEGATIVO (impossivel fisicamente): {len(neg)}")
    for n, r in neg:
        print(f"    {n:<20} {r:.2f} %")
    print()
    print("=== residuos observados por familia (para leitura de tendencia) ===")
    byfam = {}
    for n, f, r, t, s in recs:
        byfam.setdefault(f, []).append(r)
    for f in sorted(byfam, key=lambda k: (k is None, k)):
        vals = byfam[f]
        lit = f"lit {LIT[f][0]}-{LIT[f][1]}%" if f in LIT else "-"
        print(f"  {str(f):<7} n={len(vals):<2} {min(vals):6.2f}..{max(vals):6.2f}  {lit}")


if __name__ == "__main__":
    main()
