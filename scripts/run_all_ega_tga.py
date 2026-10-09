"""Testa o modulo TGA do PAT contra os 27 arquivos TGA-FTIR EGA reais (figshare 24595695).

Formato: CSV de 10 colunas.
  cols 1-2 : FTIR "Weight Loss 1" (cm-1, %T)
  cols 4-5 : FTIR "Weight Loss 2" (cm-1, %T)
  cols 7-8 : TGA (Temp C, Weight %)
"""
import csv
import glob
import os
import sys

sys.path.insert(0, "/home/hermes/projects/polymer-analysis-toolkit/backend")
import numpy as np
from app.core.thermal import analyse_tga

# Td (5% e 10%) e residuo tipicos por familia, para checagem grosseira.
# Fontes: literatura classica de degradacao termica.
EXPECTED = {
    "PE":    (380, 460, 0, 5),      # PE degrada ~400-450 C, residuo ~0
    "PVC":   (200, 300, 5, 25),     # PVC perde HCl ~250-300, deixa residuo carbono
    "PMMA":  (250, 350, 0, 5),      # PMMA despolimeriza ~300-380
    "PS":    (300, 400, 0, 5),      # PS ~350-400
    "PAN":   (250, 350, 30, 60),    # PAN cicliza ~250-300, residuo alto
    "PVOH":  (200, 300, 0, 15),
    "PVAc":  (280, 350, 0, 10),
    "EVA":   (280, 400, 0, 10),
    "EVOH":  (250, 400, 0, 10),
    "PU":    (200, 350, 0, 15),
    "PHB":   (230, 300, 0, 10),
    "Nylon": (350, 450, 0, 10),
    "SAN":   (300, 400, 0, 5),
}


def family(name):
    base = name.split()[0].upper()
    if base.startswith("NYLON"):
        return "Nylon"
    for fam in EXPECTED:
        if base.startswith(fam):
            return fam
    return None


def read_tga(path):
    """Le so o par TGA, ignorando as tabelas FTIR a esquerda.

    O dataset tem DUAS variantes de layout:
      A) 10 colunas -- duas tabelas FTIR (cm-1,%T) + TGA em cols 9,10
      B)  6 colunas -- uma tabela FTIR (cm-1,%T) + TGA em cols 5,6
    A coluna TGA e localizada pelo *cabecalho*, nao por indice fixo, porque
    o indice depende da variante e da a variante do arquivo.
    """
    T, W = [], []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rdr = csv.reader(fh)
        header = next(rdr)          # linha 1: titulos/temperatura do evento
        units = next(rdr)           # linha 2: unidades

        # Achar a coluna cujo cabecalho comeca com "Temp" e cuja unidade
        # contem "C" -- isso identifica o par TGA independente do layout.
        tcol = wcol = None
        for i, cell in enumerate(units):
            c = cell.strip().lower()
            if c.startswith("temp") and "c" in c:
                tcol = i
            if "weight" in c or "mass" in c:
                wcol = i
        if tcol is None or wcol is None:
            return np.asarray([], float), np.asarray([], float)

        for row in rdr:
            if len(row) <= max(tcol, wcol):
                continue
            t, w = row[tcol].strip(), row[wcol].strip()
            if not t or not w:
                continue
            try:
                T.append(float(t))
                W.append(float(w))
            except ValueError:
                continue
    return np.asarray(T, float), np.asarray(W, float)


def main():
    files = sorted(glob.glob("/tmp/tga_ega/*EGA.csv"))
    print(f"{len(files)} arquivos TGA-FTIR EGA\n")
    print(f"{'arquivo':<20} {'n':>6} {'Tmax':>7} {'Td5%':>7} {'Td10%':>7} "
          f"{'DTG':>7} {'res%':>6} {'passos':>6}  {'fam':<6} {'chk'}")

    rows = []
    for path in files:
        name = os.path.basename(path)
        try:
            T, W = read_tga(path)
            if len(T) < 50:
                print(f"{name:<20} POUCOS PONTOS ({len(T)})")
                continue
            res = analyse_tga(T, W)
            td5 = res.Td_5pct
            td10 = res.Td_10pct
            dtg = res.T_max_rate
            resid = res.residue_pct
            steps = len(res.steps) if getattr(res, "steps", None) else 0
            fam = family(name)
            chk = ""
            if fam and fam in EXPECTED:
                td_lo, td_hi, r_lo, r_hi = EXPECTED[fam]
                ref = td10 if td10 is not None else td5
                if ref is not None:
                    ok_t = "T-OK" if td_lo <= ref <= td_hi else "T-FORA"
                    ok_r = ("R-OK" if resid is not None
                            and r_lo <= resid <= r_hi else "R-FORA")
                    chk = f"{ok_t} {ok_r}"
            rows.append((name, fam, td5, td10, dtg, resid))
            fmt = lambda v: f"{v:7.1f}" if v is not None else "      -"
            rp = f"{resid:6.2f}" if resid is not None else "     -"
            print(f"{name:<20} {len(T):>6} {T.max():>7.1f} {fmt(td5)} {fmt(td10)} "
                  f"{fmt(dtg)} {rp} {steps:>6}  {str(fam):<6} {chk}")
        except Exception as exc:  # noqa: BLE001
            print(f"{name:<20} ERRO {type(exc).__name__}: {exc}")

    # resumo
    print("\n=== resumo ===")
    n_td = sum(1 for r in rows if r[3] is not None or r[2] is not None)
    print(f"  Td reportado em {n_td}/{len(rows)}")
    n_dtg = sum(1 for r in rows if r[4] is not None)
    print(f"  DTG reportado em {n_dtg}/{len(rows)}")
    ok = sum(1 for r in rows if r[1] in EXPECTED and r[3] is not None
             and EXPECTED[r[1]][0] <= r[3] <= EXPECTED[r[1]][1])
    tot = sum(1 for r in rows if r[1] in EXPECTED)
    print(f"  Td10 dentro da janela: {ok}/{tot}")


if __name__ == "__main__":
    main()
