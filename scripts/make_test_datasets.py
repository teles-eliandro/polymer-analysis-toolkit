#!/usr/bin/env python3
"""Gera um CSV real por modulo do PAT, a partir dos datasets brutos ja baixados.

Cada arquivo vem de dado de instrumento real, nao de gerador sintetico:

  * molar_mass  <- .reference-data/thf (Zenodo 17306416, GPC/SEC de PLLA/PDLA)
  * dsc         <- /tmp/dsc116 (*.tri, figshare 24462004, 116 tracos DSC)
  * tga         <- /tmp/tga_ega/*.csv (figshare 24595695, TGA-FTIR EGA)
  * ftir        <- /tmp/ftir/*.csv (figshare 24593022, FTIR as-received)
  * xrd         <- pat-test-data/WAXS_*.dat (Zenodo 20466241, WAXS de PLA)

Mecanica e reologia NAO existem nestes datasets. Para nao entregar dado
inventado disfarcado de real, os dois arquivos correspondentes sao gerados a
partir de um modelo constitutivo declarado e marcados como sinteticos no
cabecalho, com os parametros que os geraram.

Uso: python scripts/make_test_datasets.py [destino]
"""

from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "exemples" / "datasets")

REF = ROOT / ".reference-data"
DSC_DIR = Path("/tmp/dsc116")
TGA_DIR = Path("/tmp/tga_ega")
FTIR_DIR = Path("/tmp/ftir")
WAXS_PATH = Path("/home/hermes/pat-test-data")


def write_csv(name: str, rows, header=None) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        for row in rows:
            writer.writerow(row)
    return path


def write_with_comments(name: str, comments, header, rows) -> Path:
    """CSV com linhas de comentario (#) antes do cabecalho."""
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", newline="", encoding="utf-8") as fh:
        for line in comments:
            fh.write(f"# {line}\n")
        writer = csv.writer(fh)
        writer.writerow(header)
        for row in rows:
            writer.writerow(row)
    return path


# ---------------------------------------------------------------------------
# 1. Massa molar — GPC/SEC real (Zenodo 17306416)
# ---------------------------------------------------------------------------

def molar_mass() -> Path | None:
    """Extrai uma distribuicao Mw real da tabela do ASTRA (GPC_THF).

    Usa a coluna da amostra DL25_THF, que tem Mn/Mw publicados no relatorio
    ASTRA correspondente (reported_values.json) — assim o resultado do PAT
    pode ser conferido contra o valor do instrumento.
    """
    table = (
        REF
        / "thf/GPC_THF/tables/Mw_distribution_PLLA_PDLLA_PScalibrated_THF.txt"
    )
    if not table.exists():
        return None

    raw = table.read_text(encoding="utf-8-sig", errors="replace")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    if len(lines) < 2:
        return None

    header = lines[0].split("\t")
    # Cada amostra ocupa 3 colunas: time | Rayleigh | Molar mass.
    # Pega a primeira amostra disponivel (DL25_THF).
    time_idx = molar_idx = None
    for i, col in enumerate(header):
        label = col.strip().lower()
        if time_idx is None and "time" in label:
            time_idx = i
        elif molar_idx is None and "molar mass" in label:
            molar_idx = i
        if time_idx is not None and molar_idx is not None:
            break
    if time_idx is None or molar_idx is None:
        return None

    rows = [["molar_mass_g_per_mol"]]
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) <= max(time_idx, molar_idx):
            continue
        cell = parts[molar_idx].strip().replace(",", ".")
        try:
            value = float(cell)
        except ValueError:
            continue
        if value > 0:
            rows.append([f"{value:.4f}"])
    if len(rows) < 3:
        return None
    return write_with_comments(
        "molar_mass_gpc_pla.csv",
        [
            "GPC/SEC real — distribuicao de massa molar de PLLA (Zenodo 17306416).",
            "Cada linha e a massa molar de um slice do cromatograma, em g/mol.",
            "O arquivo NAO traz a fracao de cada slice; ao carregar no modulo use",
            "normalise=true, que trata os slices como igualmente ponderados.",
            "Valor do proprio instrumento (relatorio ASTRA DL_25k_THF):",
            "  Mn = 14060 g/mol, Mw = 15440 g/mol, D = 1.099.",
            "O resultado do PAT depende das fracoes escolhidas e nao vai bater",
            "exatamente: sirva-se disto para ver a sensibilidade da media a elas.",
        ],
        ["molar_mass_g_per_mol"],
        rows[1:],
    )


# ---------------------------------------------------------------------------
# 2. DSC — traco real .tri (figshare 24462004)
# ---------------------------------------------------------------------------

def dsc() -> Path | None:
    """Traco DSC real de PLLA no 2o aquecimento (Zenodo 17288962).

    Escolhido entre os disponiveis porque e um dos poucos em que as transicoes
    sao fisicamente corretas: o dataset traz Tg (cerca de 95 C pelo ponto
    medio ASTM D3418, conforme medido) e Tm (173 C) na ordem esperada, contra
    os tracos figshare 24462004 onde o detector de Tg reporta o fim da rampa.
    """
    src = WAXS_PATH / "DSC_PLLA_50K_2nd_heating.dat"
    if not src.exists():
        # Fallback: tenta o .tri, mesmo sabendo que a Tg la nao e confiavel.
        return _dsc_from_tri()
    rows = [["temperature_C", "heat_flow_W_per_g"]]
    for line in src.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            rows.append([f"{float(parts[0]):.3f}", f"{float(parts[1]):.6f}"])
        except ValueError:
            continue
    if len(rows) > 20:
        return write_with_comments(
            "dsc_plla_second_heating.csv",
            [
                "DSC real — PLLA_50K, 2o aquecimento a 10 K/min (Zenodo 17288962).",
                "Massa 3.6 mg, exotermico PARA CIMA, heat flow em W/g.",
                "Referencia: Tm esperado 170-180 C; dHm de PLLA 100% cristalino = 93 J/g.",
                "A Tg medida por este modulo fica proxima de 95 C; o valor de",
                "literatura para PLLA e cerca de 60-65 C. Leia a Tg com a ressalva",
                "que a ferramenta declara (grau 'suggested').",
            ],
            ["temperature_C", "heat_flow_W_per_g"],
            rows[1:],
        )
    return _dsc_from_tri()


def _dsc_from_tri() -> Path | None:
    from app.core.io.tri_reader import read_tri

    for candidate in ("PE2-AR.tri", "PET2-AR.tri"):
        path = DSC_DIR / candidate
        if not path.exists():
            continue
        parsed = read_tri(path)
        temp = parsed.temperature
        hf = None
        for ch in parsed.channels:
            if (ch.name or "").strip().lower() == "heat flow":
                hf = ch.values
                break
        if not temp or not hf:
            continue
        n = min(len(temp), len(hf))
        rows = [["temperature_C", "heat_flow_W_per_g"]]
        for i in range(n):
            rows.append([f"{temp[i]:.3f}", f"{hf[i]:.6f}"])
        return write_csv("dsc_figshare_trace.csv", rows)
    return None


# ---------------------------------------------------------------------------
# 3. TGA — curva TGA real (figshare 24595695, arquivo EGA)
# ---------------------------------------------------------------------------

def tga() -> Path | None:
    # O arquivo EGA tem 3 blocos lado a lado; o terceiro e a curva TGA.
    for candidate in ("EVA-1 EGA.csv", "PMMA-1 EGA.csv", "PS-2 EGA.csv"):
        path = TGA_DIR / candidate
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        lines = text.splitlines()
        if len(lines) < 3:
            continue

        hdr = lines[1].split(",")
        # Localiza o par de colunas "Temperature (C)" / "Weight (%)".
        t_idx = m_idx = None
        for i, col in enumerate(hdr):
            low = col.strip().lower()
            if "temperature" in low:
                t_idx = i
            if "weight" in low:
                m_idx = i
        if t_idx is None or m_idx is None:
            continue

        rows = [["temperature_C", "mass_pct"]]
        for line in lines[2:]:
            parts = line.split(",")
            if len(parts) <= max(t_idx, m_idx):
                continue
            try:
                t = float(parts[t_idx].strip())
                m = float(parts[m_idx].strip())
            except ValueError:
                continue
            if math.isnan(t) or math.isnan(m):
                continue
            rows.append([f"{t:.2f}", f"{m:.4f}"])
        if len(rows) > 20:
            sample = path.name.replace("FTIR_", "").replace(".csv", "")
            return write_with_comments(
                "tga_eva_nitrogen.csv",
                [
                    f"TGA real — {sample}, em nitrogenio (figshare 24595695).",
                    "Curva extraida do arquivo EGA do instrumento; cada linha e",
                    "temperatura (C) e massa restante (% da inicial).",
                    "Referencia: para EVA a perda principal fica em 340-480 C em duas",
                    "etapas (desacetilacao e quebra da cadeia).",
                    "Valores do proprio dataset nesta amostra: Td5% ~ 363 C, residuo ~ 6%.",
                ],
                ["temperature_C", "mass_pct"],
                rows[1:],
            )
    return None


# ---------------------------------------------------------------------------
# 4. FTIR — espectro real (figshare 24593022)
# ---------------------------------------------------------------------------

def ftir() -> Path | None:
    for candidate in ("FTIR_PET-1.csv", "FTIR_PC-1.csv", "FTIR_PS-1.csv"):
        path = FTIR_DIR / candidate
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        lines = text.splitlines()
        if len(lines) < 3:
            continue

        rows = [["wavenumber_cm-1", "transmittance_pct"]]
        for line in lines[2:]:
            parts = line.split(",")
            if len(parts) < 2:
                continue
            try:
                wn = float(parts[0].strip())
                val = float(parts[1].strip())
            except ValueError:
                continue
            rows.append([f"{wn:.2f}", f"{val:.4f}"])
        if len(rows) > 50:
            sample = path.name.replace("FTIR_", "").replace(".csv", "")
            return write_with_comments(
                "ftir_pet_transmittance.csv",
                [
                    f"FTIR real — {sample}, as-received (figshare 24593022).",
                    "ATENCAO: o arquivo cru e TRANSMITANCIA (%), como o instrumento",
                    "exporta. O modulo do PAT espera ABSORBANCIA e vai recusar %T com",
                    "uma mensagem explicita — isso e o guard funcionando, nao um erro",
                    "do arquivo. Converta com A = -log10(T/100) antes de carregar.",
                    "Referencia PET: C=O estiramento 1715 cm-1; C-O 1240 e 1095 cm-1;",
                    "anel aromático 1505 e 1410 cm-1.",
                ],
                ["wavenumber_cm-1", "transmittance_pct"],
                rows[1:],
            )
    return None


# ---------------------------------------------------------------------------
# 5. XRD — padrao WAXS real (Zenodo 20466241)
# ---------------------------------------------------------------------------

def xrd() -> Path | None:
    path = WAXS_PATH / "WAXS_film4-16_002.dat"
    if not path.exists():
        return None
    rows = [["two_theta_deg", "intensity_counts"]]
    for line in path.read_text(errors="replace").splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            rows.append([f"{float(parts[0]):.4f}", f"{float(parts[1]):.4f}"])
        except ValueError:
            continue
    if len(rows) > 10:
        return write_with_comments(
            "xrd_plla_waxs.csv",
            [
                "WAXS real — filme de PLLA/PEO (Zenodo 20466241).",
                "O eixo ja esta convertido para 2-theta (graus), como o modulo espera.",
                "ATENCAO: o padrao comeca em 2-theta ~ 5 graus, onde fica o pico do",
                "feixe direto do instrumento. O primeiro 'pico' que o modulo lista",
                "com d ~ 17 A e esse artefato, nao uma reflexao do polimero. Os",
                "picos de PLLA relevantes ficam em 16.7 e 19.1 graus (d = 5.3 e 4.6 A).",
            ],
            ["two_theta_deg", "intensity_counts"],
            rows[1:],
        )
    return None


# ---------------------------------------------------------------------------
# 6 e 7. Mecanica e reologia — SEM dado real disponivel; modelo declarado
# ---------------------------------------------------------------------------

def mechanical() -> Path:
    """Curva tensao-deformacao de um modelo bilinear declarado.

    NAO e dado de instrumento. Os parametros sao tipicos de um poliolefino
    ductil e estao no cabecalho para que a origem seja rastreavel.
    """
    E = 1200.0        # MPa, modulo elastico
    sigma_y = 28.0    # MPa, tensao de escoamento
    eps_y = sigma_y / E * 100.0
    strain_break = 350.0
    sigma_break = 22.0

    rows = []
    for i in range(0, 1000):
        eps = strain_break * i / 999.0
        if eps <= eps_y:
            sigma = E * eps / 100.0
        else:
            frac = (eps - eps_y) / (strain_break - eps_y)
            sigma = sigma_y + (sigma_break - sigma_y) * frac
        rows.append([f"{eps:.4f}", f"{sigma:.5f}"])

    return write_with_comments(
        "mechanical_tensile_SYNTHETIC.csv",
        [
            "DADO SINTETICO — nenhum dataset publico de tracao foi usado por este projeto.",
            "Modelo bilinear: E=1200 MPa, sigma_y=28 MPa, ruptura em 350% / 22 MPa.",
            "Use para exercitar o modulo, nao como referencia de material.",
        ],
        ["strain_pct", "stress_MPa"],
        rows,
    )


def rheology() -> Path:
    """Varredura de frequencia de um modelo Maxwell generalizado declarado."""
    # Dois modos Maxwell: tau em s, G em Pa.
    modes = [(1.0, 3.0e4), (0.01, 1.2e6)]
    rows = []
    for i in range(41):
        omega = 10 ** (-2 + 5 * i / 40.0)  # 0.01 a 1000 rad/s
        gp = sum(
            g * (omega * tau) ** 2 / (1 + (omega * tau) ** 2) for tau, g in modes
        )
        gpp = sum(
            g * (omega * tau) / (1 + (omega * tau) ** 2) for tau, g in modes
        )
        rows.append([f"{omega:.6g}", f"{gp:.6f}", f"{gpp:.6f}"])

    return write_with_comments(
        "rheology_frequency_sweep_SYNTHETIC.csv",
        [
            "DADO SINTETICO — nenhum dataset publico de reologia foi usado por este projeto.",
            "Maxwell generalizado de 2 modos: (tau=1e-2 s, G=1.2e6 Pa) e (tau=1 s, G=3e4 Pa).",
            "Use para exercitar o modulo, nao como referencia de material.",
        ],
        ["omega_rad_per_s", "G_prime_Pa", "G_double_prime_Pa"],
        rows,
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    produced = []

    for label, fn in (
        ("massa molar (GPC/SEC real)", molar_mass),
        ("DSC (traco real .tri)", dsc),
        ("TGA (curva real)", tga),
        ("FTIR (espectro real)", ftir),
        ("XRD/WAXS (padrao real)", xrd),
        ("mecanica (SINTETICO)", mechanical),
        ("reologia (SINTETICO)", rheology),
    ):
        try:
            path = fn()
        except Exception as exc:  # noqa: BLE001
            print(f"  {label:28} ERRO: {exc}")
            continue
        if path is None:
            print(f"  {label:28} fonte ausente — pulado")
        else:
            n = sum(1 for _ in path.open()) - 1
            produced.append((label, path, n))
            print(f"  {label:28} {path.name}  ({n} linhas)")

    print(f"\n{len(produced)} arquivos em {OUT}")
    return 0 if produced else 1


if __name__ == "__main__":
    raise SystemExit(main())
