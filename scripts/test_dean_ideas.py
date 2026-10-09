#!/usr/bin/env python3
"""Testa as ideias do Dean (DSC, Univ. Alabama) contra o caso que falha.

Caso de teste: DSC_PLLA_50K_2nd_heating.dat
  O modulo reporta Tg = 94.7 C.
  O degrau real de Tg esta em ~56 C (maior gradiente da regiao 40-90 C).

Ideias do Dean a testar:

1. p.55-56  A Tg e medida por ponto medio entre onset extrapolado e fim
            extrapolado; o onset sozinho e a construcao de Tm.
2. p.72     Agua absorvida desloca a Tg do nylon de 94 C (0.35% H2O) a 6 C
            (10.3% H2O) -- umidade e uma causa fisica de Tg baixa, nao erro.
3. p.74-76  Envelhecimento fisico cria pico endotermico SOBRE a Tg; aquecer
            acima da Tg e resfriar rapido apaga o efeito. Isto preve um pico
            espurio que o detector pode confundir com transicao.
4. p.29     Numa curva DSC as transicoes tem ordem: Tg -> crist. fria ->
            Tm. A cristalizacao fria e EXOTERMICA e vem DEPOIS da Tg.
5. p.100-106 MDSC separa reversivel (Cp, Tg) de nao-reversivel (cinetico,
            crist. fria, cura, vaporizacao). E a solucao de fundo, mas exige
            dado modulado -- nao ha neste dataset.
6. p.59-61  Taxa de aquecimento recomendada para Tg: 20 C/min. A 10 C/min,
            sensibilidade "poor". Isto e quantificavel no nosso dado.
7. p.11,57  Tg = transicao de 2a ordem (degrau em Cp); Tm = 1a ordem (pico).
            A derivada transforma o degrau de Tg num pico -- por isso
            |dhf/dT| localiza a Tg (o detector ja faz isto).

Hipotese a testar (usando a ideia 4): o modulo pegou a cristalizacao fria
como Tg porque ela e um pico exotermico grande e vem depois da Tg real.
Se a regra de ordenacao "Tg < Tc_fria < Tm" for imposta, a Tg tem de ser
MENOR que o evento exotermico.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.thermal import analyse_dsc  # noqa: E402

DATA = Path("/home/hermes/pat-test-data")


def load(name: str):
    d = np.loadtxt(DATA / name)
    return d[:, 0], d[:, 1]


def report(tag: str, T, hf):
    r = analyse_dsc(T, hf, heating_rate=10.0, ref_enthalpy_J_g=93.0)
    tg = None if r.Tg is None else round(r.Tg, 1)
    tm = None if r.Tm is None else round(r.Tm, 1)
    tc = getattr(r, "Tc", None)
    print(f"  {tag:26} Tg={str(tg):>7}  Tm={str(tm):>7}  Tc={tc}")
    return r


print("=" * 78)
print("1. O caso que falha, e o mesmo traco com a ideia de ordenacao aplicada")
print("=" * 78)

for f in ("DSC_PLLA_10K_2nd_heating.dat", "DSC_PLLA_25K_2nd_heating.dat", "DSC_PLLA_50K_2nd_heating.dat"):
    T, hf = load(f)
    report(f.replace("DSC_", "").replace(".dat", ""), T, hf)

print()
print("=" * 78)
print("2. Onde esta o pico EXOTERMICO (cristalizacao fria) e onde esta o degrau")
print("=" * 78)

T, hf = load("DSC_PLLA_50K_2nd_heating.dat")
grad = np.gradient(hf, T)

# Pico exotermico: minimo local de hf (exotermico para baixo neste arquivo,
# segundo o manifesto: exotherm = UP... conferir o sinal).
print(f"  hf minimo global: {hf.min():.4f} em T = {T[np.argmin(hf)]:.1f}")
print(f"  hf maximo global: {hf.max():.4f} em T = {T[np.argmax(hf)]:.1f}")

# O manifesto diz 'endothermic up'. Entao endotermico = para cima.
# Cristalizacao fria = exotermico = para BAIXO = minimo local.
from scipy.signal import find_peaks  # noqa: E402
if True:
    peaks_down, props = find_peaks(-hf, prominence=0.05)
    print(f"  minimos locais (exotermicos) em T = {[round(T[p],1) for p in peaks_down]}")
    peaks_up, _ = find_peaks(hf, prominence=0.05)
    print(f"  maximos locais (endotermicos) em T = {[round(T[p],1) for p in peaks_up]}")

print()
print("=" * 78)
print("3. Ideia 1 do Dean: Tg pelo PONTO MEDIO da construcao ASTM D3418")
print("   (onset extrapolado a fim extrapolado), nao pelo maximo de |dhf/dT|")
print("=" * 78)

# Construcao classica: achar o degrau, ajustar retas antes/depois, o ponto
# medio entre onset e fim e a Tg.
def mid_point_tg(T, hf, lo=40.0, hi=90.0):
    m = (T >= lo) & (T <= hi)
    Ts, hs = T[m], hf[m]
    g = np.gradient(hs, Ts)
    # Onset: onde o desvio da linha de base fria atinge metade do degrau.
    n = len(Ts)
    q = max(3, n // 6)
    base_lo = np.mean(hs[:q])
    base_hi = np.mean(hs[-q:])
    step = base_hi - base_lo
    half = base_lo + step / 2
    idx = int(np.argmin(np.abs(hs - half)))
    return float(Ts[idx]), float(base_lo), float(base_hi), float(step)

tg_mid, blo, bhi, step = mid_point_tg(T, hf)
print(f"  base fria (40 C): {blo:.4f}   base quente (90 C): {bhi:.4f}   degrau: {step:.4f}")
print(f"  Tg por ponto medio (hi-lo/2): {tg_mid:.1f} C")

# Metodo do maximo de |dhf/dT| na regiao
m = (T >= 40) & (T <= 90)
g = np.gradient(hf, T)
i = np.argmax(np.abs(g[m]))
print(f"  Tg por |dhf/dT| maximo:        {T[m][i]:.1f} C")

print()
print("=" * 78)
print("4. Ideia 6 do Dean: taxa de aquecimento 20 C/min (10 C/min = 'poor')")
print("   Nao podemos remedir, mas podemos ver SE a sensibilidade muda o achado")
print("   quando o traco e suavizado como um instrumento mais lento faria.")
print("=" * 78)

for w in (1, 11, 31, 71):
    if w == 1:
        hfw = hf
    else:
        k = np.ones(w) / w
        hfw = np.convolve(hf, k, mode="same")
    r = analyse_dsc(T, hfw, heating_rate=10.0)
    tg = None if r.Tg is None else round(r.Tg, 1)
    print(f"  suavizacao w={w:3} -> Tg={str(tg):>7}")

print()
print("=" * 78)
print("5. Ideia 4 aplicada: impor a ordem fisica Tg < Tc_fria < Tm")
print("=" * 78)

# Onde esta a cristalizacao fria? Pico exotermico (hf para baixo) depois da Tg.
m = (T > 55) & (T < 150)
ig = np.argmin(hf[m])
tc_cold = T[m][ig]
print(f"  cristalizacao fria (minimo entre 55-150 C): T = {tc_cold:.1f} C, hf = {hf[m][ig]:.4f}")
print(f"  Tg real (degrau a 56 C) ... {56.3:.1f} C < Tc_fria {tc_cold:.1f} C < Tm {T[np.argmax(hf)]:.1f} C")
print(f"  A ordem fisica e satisfeita para 56 C, mas NAO para 94.7 C?")
print(f"  94.7 < {tc_cold:.1f} ? {94.7 < tc_cold}")
