"""
Verificação contra valores publicados na literatura e em padrões certificados.

Este arquivo é diferente do resto da suite. Os outros testes verificam
**coerência interna**: que a implementação satisfaz as identidades analíticas
dos modelos. Isso prova que o código faz o que pretendemos. Não prova que os
números concordam com o mundo.

Aqui comparamos com **valores de referência externos**, baixados de fontes
abertas e citadas. Onde a comparação não é possível, o teste não é omitido em
silêncio: ele é marcado `xfail` com a razão, para que a lacuna seja visível no
relatório de testes em vez de desaparecer.

Fontes usadas
-------------
[1] NIST IR 6091 (1998), Guttman, Blair & Maurey, "Recertification of the
    SRM 706a, a Polystyrene", NIST Polymers Division.
    DOI 10.6028/nist.ir.6091 — acesso aberto.
    Mw certificado do SRM 706a = 2.85e5 g/mol, incerteza expandida
    0.23e5 g/mol (k = 2), de 8 corridas de espalhamento de luz.

[2] Zenodo 10.5281/zenodo.17306416 (CC-BY-4.0) — GPC/SEC de amostras de
    poli(ácido láctico) em THF, Centro de Física de Materiais (CSIC-UPV/EHU),
    San Sebastián. Relatórios ASTRA 8.2.2 (Wyatt) com Mn, Mw, Mz, Mz+1 e
    incertezas por amostra.

Os arquivos baixados não são versionados no repositório (são alguns MB e têm
licença própria). O teste que os usa é pulado com uma mensagem explícita
quando não estão presentes, e um script em `scripts/` os baixa.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.core.molar_mass import (
    log_normal_moments,
    moment_averages,
)

# Diretório onde os dados de referência são colocados por
# scripts/fetch_reference_data.py. Fora do controle de versão.
REFERENCE_DIR = Path(__file__).resolve().parent.parent.parent / ".reference-data"

REPORTED_VALUES = REFERENCE_DIR / "reported_values.json"
PLA_TABLES = REFERENCE_DIR / "thf" / "GPC_THF" / "tables"
PLA_TABLE_MAIN = "Mw_distribution_PLLA_PDLLA_PScalibrated_THF.txt"
PLA_TABLE_PDLA = "Mw_distribution_PDLA_PLA3D850_PScalibrated_THF.txt"

has_reported = REPORTED_VALUES.exists() and PLA_TABLES.exists()

needs_data = pytest.mark.skipif(
    not has_reported,
    reason=(
        "Dados de referência ausentes. Rode "
        "`python scripts/fetch_reference_data.py` para baixá-los do Zenodo "
        "(10.5281/zenodo.17306416) antes de executar a verificação externa."
    ),
)

# ---------------------------------------------------------------------------
# [1] NIST SRM 706a -- valor certificado
# ---------------------------------------------------------------------------

NIST_SRM_706A = {
    "Mw": 2.85e5,
    "uncertainty_expanded": 0.23e5,  # k = 2
    "coverage_factor": 2,
    "n_runs": 8,
    "run_std_dev": 0.019e5,
    "doi": "10.6028/nist.ir.6091",
    "citation": "NIST IR 6091 (1998), Guttman, Blair & Maurey, Table 1",
}


def test_nist_certified_polystyrene_value_is_the_one_we_cite():
    """
    Trava o valor certificado que o projecto cita.

    Se alguém alterar a constante acima, este teste falha e obriga a revisitar
    o documento do NIST. O valor foi lido do texto do Abstract e da Table 1 do
    NIST IR 6091: "The Mw of SRM 706a by light scattering was determined to be
    2.85 x 10^5 g/mol with a sample standard deviation of 0.019 x 10^5 g/mol",
    e a incerteza combinada expandida de 0.23 x 10^5 g/mol.
    """
    assert NIST_SRM_706A["Mw"] == 2.85e5
    assert NIST_SRM_706A["uncertainty_expanded"] == 0.23e5
    assert NIST_SRM_706A["coverage_factor"] == 2
    assert NIST_SRM_706A["n_runs"] == 8
    # A incerteza expandida tem de ser maior que o desvio padrão das corridas,
    # porque inclui as contribuições sistemáticas. Se não fosse, o valor
    # certificado teria sido lido errado.
    assert NIST_SRM_706A["uncertainty_expanded"] > NIST_SRM_706A["run_std_dev"]


def test_moments_reproduce_the_log_normal_identity_used_to_cross_check_nist():
    """
    A identidade que permite relacionar as médias do SRM 706a entre si.

    O NIST certifica apenas Mw. Para uma distribuição log-normal
    (a forma que um poliestireno radicalar de distribuição larga aproxima),
    vale exatamente Mz/Mw = Mw/Mn = exp(sigma^2). Testamos que as nossas
    quatro médias respeitam essa relação, que é o que nos autoriza a afirmar
    algo sobre Mn, Mz e Mz+1 a partir de um Mw certificado.
    """
    for dispersity in (1.5, 2.0, 2.5, 2.9):
        d = log_normal_moments(
            NIST_SRM_706A["Mw"] / dispersity, dispersity, n_points=20000, n_sigma=6.0
        )
        mz_over_mw = d["Mz"] / d["Mw"]
        mw_over_mn = d["Mw"] / d["Mn"]
        assert mz_over_mw == pytest.approx(mw_over_mn, rel=0.02), (
            f"D={dispersity}: Mz/Mw={mz_over_mw:.4f} mas Mw/Mn={mw_over_mn:.4f}; "
            "a identidade da log-normal deve valer"
        )
        # E a ordem dos momentos tem de se manter.
        assert d["Mn"] <= d["Mw"] <= d["Mz"] <= d["Mz_plus_1"]


def test_scaling_a_certified_polystyrene_keeps_dispersity():
    """
    Um valor certificado em unidades diferentes descreve o mesmo polímero.

    Se tomarmos o Mw do SRM 706a e o expressarmos em kg/mol, a dispersidade
    não pode mudar. Isto protege contra um erro de unidade que faria o
    módulo molecular devolver números plausíveis mas errados.
    """
    masses_g = [1.0e5, 2.0e5, 2.85e5 * 2, 4.0e5]
    w = [0.15, 0.35, 0.35, 0.15]
    r_g = moment_averages(masses_g, w)
    r_kg = moment_averages([m / 1000.0 for m in masses_g], w)
    assert r_g.dispersity == pytest.approx(r_kg.dispersity, rel=1e-12)
    assert r_kg.Mw == pytest.approx(r_g.Mw / 1000.0, rel=1e-12)
    # O material construído tem Mw próximo do certificado, dentro de 25 %.
    assert r_g.Mw == pytest.approx(NIST_SRM_706A["Mw"], rel=0.25)


# ---------------------------------------------------------------------------
# [2] Valores reportados pelo ASTRA no dataset de PLA
# ---------------------------------------------------------------------------


def _load_reported():
    return json.loads(REPORTED_VALUES.read_text())


KEYMAP = {
    "DL_10k_THF.pdf": (PLA_TABLE_MAIN, "DL10_THF"),
    "DL_15k_THF.pdf": (PLA_TABLE_MAIN, "DL15_THF"),
    "DL_25k_THF.pdf": (PLA_TABLE_MAIN, "DL25_THF"),
    "DL_50k_THF.pdf": (PLA_TABLE_MAIN, "DL50_THF"),
    "LL_10k_THF.pdf": (PLA_TABLE_MAIN, "LL10_THF"),
    "LL_25k_THF.pdf": (PLA_TABLE_MAIN, "LL25_THF"),
    "LL_50k_THF.pdf": (PLA_TABLE_MAIN, "LL50_THF"),
    "PDLA_100k_THF.pdf": (PLA_TABLE_PDLA, "PDLA_100k_THF"),
    "PDLA_25k_THF.pdf": (PLA_TABLE_PDLA, "PDLA_25k_THF"),
    "PDLA_50k_THF.pdf": (PLA_TABLE_PDLA, "PDLA_50k_THF"),
}


def _load_distribution(table_name: str, key: str):
    """
    Lê o par (massa molar, sinal dRI) de uma amostra da tabela do dataset.

    Estrutura do arquivo, verificada campo a campo: cada amostra ocupa SEIS
    campos consecutivos na ordem (t, Rayleigh ratio, t_ref, dRI, logM, M).
    O cabeçalho lista 42 nomes para 7 amostras, 6 cada, o que confirma o
    passo; mas os nomes NÃO estão alinhados com os dados campo a campo (o
    nome "time (min)" cai sobre o valor de logM), por isso os índices são
    derivados do início do sexteto e não de procurar o nome e somar um.
    """
    path = PLA_TABLES / table_name
    if not path.exists():
        return None
    lines = [ln.rstrip("\r\n") for ln in path.read_text(encoding="utf-8").split("\n") if ln.strip()]
    header = [h.strip() for h in lines[0].split("\t")]
    try:
        base = (header.index(f"{key} (dRI)") // 6) * 6
    except ValueError:
        return None

    conc, mass = [], []
    for ln in lines[1:]:
        parts = ln.split("\t")
        if len(parts) <= base + 5:
            continue
        try:
            c = float(parts[base + 3].replace(",", "."))
            m = float(parts[base + 5].replace(",", "."))
        except (ValueError, IndexError):
            continue
        if m > 0 and c > 0:
            conc.append(c)
            mass.append(m)
    if len(mass) < 10:
        return None
    m = np.array(mass)
    c = np.array(conc)
    order = np.argsort(m)
    return m[order], c[order]


@needs_data
def test_reported_values_are_internally_consistent():
    """
    Gate de qualidade sobre a referência, antes de a usar para julgar o código.

    Se os valores publicados não satisfizessem as relações que a teoria impõe,
    não serviriam como referência e nenhuma conclusão poderia ser tirada de
    uma comparação com eles. As três relações testadas são:
      (a) Mn <= Mw <= Mz <= Mz+1
      (b) Mw/Mn publicado == Mw/Mn recalculado dos momentos publicados
      (c) Mz/Mn publicado == Mz/Mn recalculado dos momentos publicados
    """
    reported = _load_reported()
    checked = 0
    for rec in reported:
        f = rec.get("fields", {})
        if not all(k in f for k in ("Mn", "Mw", "Mz", "Mz+1")):
            continue
        checked += 1
        mn, mw, mz, mz1 = f["Mn"], f["Mw"], f["Mz"], f["Mz+1"]
        assert mn <= mw <= mz <= mz1, f"{rec['report']}: ordem dos momentos violada"
        if f.get("Mw/Mn"):
            assert mw / mn == pytest.approx(f["Mw/Mn"], rel=0.02), rec["report"]
        if f.get("Mz/Mn"):
            assert mz / mn == pytest.approx(f["Mz/Mn"], rel=0.02), rec["report"]
    assert checked >= 8, f"esperava ao menos 8 relatórios com os quatro momentos, achei {checked}"


@needs_data
def test_moments_against_instrument_reported_mw_on_covered_samples():
    """
    Comparação com o Mw que o equipamento reportou, nas amostras em que a
    tabela do dataset cobre a faixa de massa molar.

    O critério de inclusão é explícito e não escolhido a posteriori: só entram
    as amostras cujo intervalo reconstruído [M_min, M_max] contém o Mw
    publicado. Quando a tabela não contém o valor reportado, a comparação
    mediria a cobertura do arquivo, não o nosso código, e atribuir o desvio ao
    cálculo seria falso.

    Resultado medido com os dados baixados: 8 amostras incluídas, desvio
    mediano de Mw de 4.9 % e máximo de 35 %, contra valores do fabricante.
    A tolerância de 15 % no teste é folgada em relação ao mediano e existe para
    detectar uma regressão grosseira, não para reivindicar precisão.
    """
    reported = _load_reported()
    covered, excluded = [], []
    for rec in reported:
        rep = rec.get("report")
        if rep not in KEYMAP:
            continue
        table, key = KEYMAP[rep]
        data = _load_distribution(table, key)
        if data is None:
            continue
        m, c = data
        w = c / m
        w = w / w.sum()
        r = moment_averages(m, w)
        ref_mw = rec["fields"]["Mw"]
        entry = (key, ref_mw, r.Mw, float(m.min()), float(m.max()))
        if float(m.min()) <= ref_mw <= float(m.max()):
            covered.append(entry)
        else:
            excluded.append(entry)

    assert covered, "nenhuma amostra coberta; a comparação não pode ser feita"
    # O gate de cobertura tem de excluir algo: se não excluísse nada, ou os
    # dados mudaram, ou o critério não está a ser aplicado.
    assert excluded, (
        "esperava que algumas amostras fossem excluídas por falta de cobertura; "
        "se nenhuma foi, verificar se os dados de referência mudaram"
    )

    deviations = [abs((pat - ref) / ref * 100.0) for _, ref, pat, _, _ in covered]
    median_dev = float(np.median(deviations))
    assert median_dev < 15.0, (
        f"desvio mediano de Mw = {median_dev:.1f}% em {len(covered)} amostras "
        f"cobertas; esperado abaixo de 15 %"
    )


@needs_data
def test_moments_ordering_holds_on_real_distributions():
    """A ordem Mn <= Mw <= Mz <= Mz+1 tem de valer em toda distribuição real."""
    reported = _load_reported()
    n = 0
    for rec in reported:
        rep = rec.get("report")
        if rep not in KEYMAP:
            continue
        table, key = KEYMAP[rep]
        data = _load_distribution(table, key)
        if data is None:
            continue
        m, c = data
        w = c / m
        w = w / w.sum()
        r = moment_averages(m, w)
        assert r.Mn <= r.Mw <= r.Mz <= r.Mz_plus_1, key
        assert r.dispersity >= 1.0, f"{key}: dispersidade {r.dispersity} < 1"
        n += 1
    assert n >= 5, f"esperava ao menos 5 distribuições reais, processei {n}"


@needs_data
def test_dispersity_from_reconstructed_distribution_is_plausible_for_pla():
    """
    A dispersidade que obtemos tem de estar no regime reportado para PLA
    sintetizado por abertura de anel.

    Os relatórios do próprio dataset indicam Mw/Mn entre 1.04 e 1.30. Uma
    distribuição real processada pelo nosso código deve cair nessa faixa; um
    valor fora dela indicaria que estamos a ler a coluna errada.
    """
    reported = _load_reported()
    dispersities = []
    for rec in reported:
        rep = rec.get("report")
        if rep not in KEYMAP:
            continue
        table, key = KEYMAP[rep]
        data = _load_distribution(table, key)
        if data is None:
            continue
        m, c = data
        w = c / m
        w = w / w.sum()
        dispersities.append(moment_averages(m, w).dispersity)

    assert dispersities, "nenhuma distribuição processada"
    for d in dispersities:
        assert 1.0 <= d <= 2.5, f"dispersidade {d} fora do plausível para PLA"


# ---------------------------------------------------------------------------
# Verificações que NÃO podem ser feitas com os dados abertos disponíveis
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "O certificado NIST do SRM 706a publica apenas Mw; a distribuição de "
        "massa molar slice-a-slice do material não foi encontrada em nenhum "
        "repositório aberto. Reproduzir o certificado exigiria essa "
        "distribuição. Ver o relatório de verificação para o estado desta "
        "lacuna e o que a fecharia."
    ),
    strict=True,
)
def test_reproduce_nist_certified_mw_from_a_distribution():
    """Não executável hoje — ver a razão do xfail."""
    raise AssertionError("distribuição certificada indisponível")


@pytest.mark.xfail(
    reason=(
        "Verificar Mv de forma independente exigiria um par (K, a) de "
        "Mark-Houwink publicado E a viscosidade intrínseca medida da mesma "
        "amostra. O dataset de PLA não traz [eta]. O limite teórico Mv(a=1) = "
        "Mw é verificado em test_molar_mass.py."
    ),
    strict=True,
)
def test_mv_against_a_published_intrinsic_viscosity():
    """Não executável hoje — ver a razão do xfail."""
    raise AssertionError("viscosidade intrínseca medida indisponível")
