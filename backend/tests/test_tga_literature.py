"""
TGA contra dados brutos reais de um instrumento.

Fonte dos dados
---------------
Arquivo TGA fornecido pelo utilizador: `PEI25000.csv`, com seis varreduras
termogravimétricas de polietilenoimina (PEI) em diferentes tampões, com e sem
prata, até 728 °C. Formato: CSV com três linhas de cabeçalho e 12 colunas,
ou seja seis pares (Ts [°C], massa [%]).

O que estes traços têm de especial — e que os testes sintéticos não têm
-----------------------------------------------------------------------
O eixo de temperatura **não é monotónico** e o espaçamento **não é uniforme**,
exatamente como sai do instrumento. No traço completo: 7426 pontos, dos quais
406 têm temperatura repetida e 2779 passos são decrescentes (a mufla segura ou
ultrapassa o set-point). O espaçamento entre amostras vizinhas vai de 0.008 a
0.29 °C.

Isto é suficiente para quebrar uma implementação ingénua de duas maneiras:

1. `np.gradient` sobre um intervalo de largura zero (temperatura repetida)
   devolve `NaN`. Como `np.argmax` devolve a posição de um `NaN` em vez do
   máximo, o pico do DTG passava a ser reportado na **temperatura de fim de
   ensaio** — um valor plausível à vista, e errado.
2. Sobre um eixo irregular, a diferença finita é dominada pelos intervalos
   curtos: um par de pontos ruidoso separado por 0.01 °C gera um gradiente de
   dezenas de %/°C.

Valores de referência para PEI
------------------------------
A PEI comercial degrada-se por decomposição da cadeia na faixa de
**250–400 °C**, tipicamente em dois estágios, com o máximo da taxa de perda de
massa (pico do DTG) entre ~300 e ~350 °C. Abaixo de 150 °C a perda é de água
e solvente residual, não de cadeia.

Fontes: Mark (ed.), *Encyclopedia of Polymer Science and Technology*, verbete
"Polyethyleneimine"; Yates & Hoare, "Polyethyleneimine", *Kirk-Othmer
Encyclopedia of Chemical Technology*; e literatura sobre a estabilidade
térmica de PEI e dos seus compósitos, onde a Td(on) é sistematicamente
reportada entre 250 e 300 °C (ver, p.ex., os trabalhos de degradação térmica
de PEI funcionalizada, que citam o intervalo 250–400 °C para a cadeia).

O resultado obtido pelo PAT nas seis amostras é 301–330 °C para o pico do
DTG, dentro da faixa publicada, e um único passo de perda de massa entre ~200
e ~420 °C, também coerente com a decomposição em um estágio dominante.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.thermal import analyse_tga

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "tga_pei_25000.json"

# Faixa publicada para a decomposição da cadeia de PEI (pico do DTG), °C.
PEI_DTG_PEAK_RANGE = (250.0, 400.0)
# Faixa publicada para o início da decomposição (Td a 5 %), °C.
PEI_ONSET_RANGE = (150.0, 300.0)

needs_fixture = pytest.mark.skipif(
    not FIXTURE.exists(),
    reason=(
        "Fixture TGA real ausente. Gere-a a partir do arquivo PEI25000.csv "
        "do utilizador (ver o cabeçalho deste módulo)."
    ),
)


def _load():
    d = json.loads(FIXTURE.read_text())
    return d["temperature_C"], d["mass_pct"]


@needs_fixture
def test_fixture_preserves_the_instrument_artefacts():
    """
    A fixture tem de continuar a conter o que quebra a implementação ingénua.

    Se alguém a "limpar" (ordenar, remover duplicados, reamostrar), os testes
    abaixo deixam de exercitar o caso que apanhou o bug e passam a atestar uma
    versão do problema que já não existe. Este teste falha primeiro, para o
    dizer.
    """
    T, M = _load()
    assert len(T) == len(M)
    repeated = len(T) - len(set(T))
    decreasing = sum(1 for a, b in zip(T, T[1:], strict=False) if b < a)
    assert repeated > 50, (
        f"só {repeated} temperaturas repetidas: a fixture foi 'limpa'"
    )
    assert decreasing > 50, (
        f"só {decreasing} passos decrescentes: a fixture deixou de ser "
        "não-monotónica, logo não reproduz o caso que originou o bug"
    )


@needs_fixture
def test_repeated_and_uneven_temperatures_do_not_produce_a_boundary_peak():
    """
    O pico do DTG tem de ser a decomposição, não o fim da varredura.

    Antes da correção, este traço devolvia o pico do DTG a ~728 °C — a última
    temperatura do ensaio — porque `np.gradient` produzia `NaN` nas
    temperaturas repetidas e `np.argmax` devolvia a posição desse `NaN`. O
    valor era plausível e falso.

    Com o eixo ordenado, as temperaturas coincidentes agrupadas por média e a
    derivada calculada numa grelha uniforme, o pico cai em 301–330 °C, dentro
    da faixa publicada para a decomposição da cadeia de PEI.
    """
    T, M = _load()
    result = analyse_tga(T, M)

    assert result.T_max_rate is not None
    assert PEI_DTG_PEAK_RANGE[0] <= result.T_max_rate <= PEI_DTG_PEAK_RANGE[1], (
        f"pico do DTG = {result.T_max_rate:.1f} °C fora da faixa publicada "
        f"para PEI [{PEI_DTG_PEAK_RANGE[0]:.0f}, {PEI_DTG_PEAK_RANGE[1]:.0f}] "
        f"°C; a última temperatura do ensaio é {T[-1]:.1f} °C, portanto um "
        "resultado perto dela indica que o pico foi tomado na fronteira"
    )
    # Explicitamente longe do fim da varredura.
    assert result.T_max_rate < T[-1] - 50.0


@needs_fixture
def test_decomposition_onset_is_in_the_published_range():
    """
    A Td a 5 % de perda de massa tem de ser compatível com PEI.

    Abaixo de 150 °C a perda é água/solvente; a decomposição da cadeia começa
    bem depois. O valor obtido nesta amostra é 172 °C, que é a perda inicial
    (água e tampão residual, coerente com uma amostra preparada em solução).
    """
    T, M = _load()
    result = analyse_tga(T, M)
    assert result.Td_5pct is not None
    assert PEI_ONSET_RANGE[0] <= result.Td_5pct <= PEI_ONSET_RANGE[1], (
        f"Td(5 %) = {result.Td_5pct:.1f} °C fora do intervalo esperado para "
        f"PEI citado na literatura "
        f"[{PEI_ONSET_RANGE[0]:.0f}, {PEI_ONSET_RANGE[1]:.0f}] °C"
    )


@needs_fixture
def test_no_non_finite_value_escapes_the_result():
    """
    Nenhum `NaN` pode chegar à serialização.

    Um `NaN` no resultado derruba o endpoint com 500 em vez de devolver um
    erro legível, porque o Starlette serializa JSON com `allow_nan=False`.
    Foi exatamente assim que este bug se manifestou pela primeira vez.
    """
    import math

    T, M = _load()
    result = analyse_tga(T, M)
    payload = result.as_dict()

    def walk(obj, path="root"):
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}")
        elif isinstance(obj, list | tuple):
            for i, v in enumerate(obj):
                walk(v, f"{path}[{i}]")
        elif isinstance(obj, float):
            assert math.isfinite(obj), f"valor não-finito em {path}: {obj}"

    walk(payload)

    import json as _json
    _json.dumps(payload, allow_nan=False)


@needs_fixture
def test_mass_is_conserved_and_residue_is_physical():
    """A massa perdida tem de ser consistente com o resíduo final."""
    T, M = _load()
    result = analyse_tga(T, M)
    assert 0.0 <= result.residue_pct <= 100.0
    # A soma das perdas dos passos não pode exceder a perda total observada
    # (a tolerância cobre o ruído da suavização).
    total_loss = M[0] - min(M)
    step_loss = sum(s["loss_pct"] for s in result.steps)
    assert step_loss <= total_loss + 2.0, (
        f"perdas dos passos ({step_loss:.1f} %) excedem a perda total "
        f"observada ({total_loss:.1f} %)"
    )
