"""Varredura dos 116 .tri com deteccao de polaridade do sinal.

O dataset 24462004 exporta o endotermico para BAIXO (DSC convencional de
instrumento: exotermico para cima). O PAT assume endotermico para cima. Sem
tratar isso, `_find_peak_temperature` procura um argmax onde a fusao e um
argmin, cai na transiente de partida e devolve Tm = T[0] (o -90,06 / -0,06
que aparecia em 6 familias diferentes).

Deteccao: a fusao e um evento grande. Onde ele estiver, a curva tem o
extremo local mais forte. Compara-se a assimetria / posicao do extremo de
maior magnitude nas duas polaridades -- a correta poe esse extremo LONGE das
pontas do ensaio (a transiente de partida esta sempre na ponta).

Tambem mede o tempo, para registrar o ganho do hoist do gradiente.
"""
import glob
import os
import sys
import time

import numpy as np

sys.path.insert(0, "/home/hermes/projects/polymer-analysis-toolkit/backend")
from app.core.io.tri_reader import read_tri
from app.core.thermal import analyse_dsc

# (Tg_lo, Tg_hi, Tm_lo, Tm_hi) por familia -- janelas amplas, de literatura.
LIT = {
    "ABS":     (85, 115, None, None),
    "EVA":     (-40, 40, 60, 110),
    "EVOH":    (40, 80, 150, 200),
    "NYLON":   (40, 80, 200, 270),
    "PAN":     (80, 110, None, None),
    "PBT":     (30, 60, 215, 240),
    "PC":      (135, 155, None, None),
    "PE":      (-130, -80, 100, 140),
    "PE-NEW":  (-130, -80, 100, 140),
    "PET":     (65, 90, 240, 265),
    "PHB":     (-10, 20, 160, 185),
    "PK":      (None, None, None, None),
    "PLA":     (50, 70, 160, 185),
    "PMMA":    (95, 115, None, None),
    "PP":      (-20, 10, 155, 175),
    "PS":      (90, 110, None, None),
    "PU":      (-50, -20, 180, 230),
    "PVAC":    (25, 45, None, None),
    "PVC":     (70, 90, None, None),
    "PVOH":    (70, 90, 220, 260),
    "SAN":     (95, 115, None, None),
}


def family_of(path):
    base = os.path.basename(path).upper()
    for fam in sorted(LIT, key=len, reverse=True):
        if base.startswith(fam):
            return fam
    return None


def pick_polarity(T, hf):
    """+1 se o endotermico ja aponta para cima, -1 se estiver invertido.

    O evento termico (fusao) e o extremo local de maior magnitude. Na
    polaridade ERRADA o PAT ancora na transiente de partida, que vive nas
    pontas; na polaridade CERTA o extremo esta no interior do ensaio. Entao
    escolhe-se a polaridade cujo extremo de maior magnitude esteja mais
    afastado das extremidades, ponderado pela magnitude.
    """
    n = T.size
    scores = {}
    for sign, y in ((+1, hf), (-1, -hf)):
        i = int(np.argmax(y))
        mag = float(y[i] - np.median(y))
        # distancia normalizada da ponta mais proxima (0 = na ponta, 0.5 = centro)
        edge = min(i, n - 1 - i) / max(n - 1, 1)
        scores[sign] = mag * edge
    return max(scores, key=scores.get)


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "/tmp/dsc116"
    files = sorted(glob.glob(os.path.join(root, "*.tri")))
    print(f"{len(files)} arquivos\n")

    rows = []
    fails = []
    t0 = time.time()
    for path in files:
        try:
            tri = read_tri(path)
            T = np.asarray(tri.temperature, float)
            hf = np.asarray(tri.heat_flow, float)
            if T.size == 0 or hf.size == 0:
                fails.append((os.path.basename(path), "sem canal"))
                continue
            sign = pick_polarity(T, hf)
            res = analyse_dsc(T, sign * hf, heating_rate=10.0)
            rows.append({
                "file": os.path.basename(path),
                "family": family_of(path),
                "sign": sign,
                "Tg": res.Tg,
                "Tm": res.Tm,
                "dHm": res.delta_Hm,
            })
        except Exception as exc:  # noqa: BLE001
            fails.append((os.path.basename(path), f"{type(exc).__name__}: {exc}"))
    elapsed = time.time() - t0

    print(f"lidos: {len(rows)}   falhas: {len(fails)}   tempo: {elapsed:.1f}s "
          f"({elapsed/max(len(rows),1):.2f}s/arquivo)")
    for f, why in fails[:8]:
        print(f"  FALHA {f}: {why}")

    def inwin(v, lo, hi):
        if v is None or lo is None:
            return None
        return lo <= v <= hi

    print("\n=== TG ===")
    ok = bad = 0
    for r in rows:
        w = LIT.get(r["family"], (None, None, None, None))
        v = inwin(r["Tg"], w[0], w[1])
        if v is True:
            ok += 1
        elif v is False:
            bad += 1
    print(f"  dentro da janela: {ok}   fora: {bad}")

    print("\n=== TM ===")
    ok = bad = miss = 0
    for r in rows:
        w = LIT.get(r["family"], (None, None, None, None))
        if w[2] is None:
            continue
        if r["Tm"] is None:
            miss += 1
        elif w[2] <= r["Tm"] <= w[3]:
            ok += 1
        else:
            bad += 1
    print(f"  dentro: {ok}   fora: {bad}   nao reportado: {miss}")

    print("\n=== por familia ===")
    print(f"{'fam':<9} {'n':>3} {'Tg (min..max)':<22} {'Tm (min..max)':<22} {'sinal'}")
    byfam = {}
    for r in rows:
        byfam.setdefault(r["family"], []).append(r)
    for fam in sorted(byfam, key=lambda k: (k is None, k)):
        g = byfam[fam]
        tgs = [x["Tg"] for x in g if x["Tg"] is not None]
        tms = [x["Tm"] for x in g if x["Tm"] is not None]
        sg = {x["sign"] for x in g}
        tgs_s = f"{min(tgs):.1f}..{max(tgs):.1f}" if tgs else "-"
        tms_s = f"{min(tms):.1f}..{max(tms):.1f}" if tms else "-"
        print(f"{str(fam):<9} {len(g):>3} {tgs_s:<22} {tms_s:<22} {sg}")

    print("\n=== Tm que ainda erram (candidatos a bug restante) ===")
    for r in rows:
        w = LIT.get(r["family"], (None, None, None, None))
        if w[2] is None:
            continue
        if r["Tm"] is not None and not (w[2] <= r["Tm"] <= w[3]):
            print(f"  {r['file']:<22} fam={r['family']:<7} Tm={r['Tm']:8.1f} "
                  f"esperado ({w[2]},{w[3]})")
    print("\n=== Tm nao reportado (esperado existir) ===")
    for r in rows:
        w = LIT.get(r["family"], (None, None, None, None))
        if w[2] is not None and r["Tm"] is None:
            print(f"  {r['file']:<22} fam={r['family']}")


if __name__ == "__main__":
    main()
