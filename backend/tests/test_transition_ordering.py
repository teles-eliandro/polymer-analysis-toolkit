"""A ordem física das transições limita onde uma Tg pode estar.

Contexto
--------
D. Dean, "Differential Scanning Calorimetry" (University of Alabama at
Birmingham), slide 29, dá a sequência de eventos de um traço DSC: numa
varredura de aquecimento de uma amostra amorfa ou temperada, o material passa
pela transição vítrea, pode então cristalizar (cristalização fria,
exotérmica) e só depois funde. Slide 28 define a cristalização fria.

Isso é uma restrição de ordenação, não um ajuste de limiar: **a Tg fica abaixo
do pico de cristalização fria.** Depois que a amostra cristalizou, a fase
amorfa que produz o degrau de Cp já não existe, então um candidato em cima do
pico exotérmico não pode ser uma transição vítrea.

Medido nos três traços reais de PLLA do Zenodo 10.5281/zenodo.17288962
(referência: Tg do PLLA em cerca de 60-65 C), antes desta restrição:

    amostra    Tg reportada   pico de crist. fria   fisicamente possível?
    PLLA_10K      87.6 C            85.3 C                  não
    PLLA_25K      94.2 C            90.8 C                  não
    PLLA_50K      94.7 C            91.8 C                  não

Em todos os três a Tg reportada ficava ACIMA do mínimo exotérmico. O gradiente
naquela queda (-0.332 W/g/K a 90 C no traço de 50K) é vinte vezes o do degrau
real em 55 C (+0.017), então o candidato de derivada era escolhido sempre.

O que estes testes fixam
------------------------
1. A restrição remove a impossibilidade: a Tg nunca sai em cima ou acima do
   pico de cristalização fria.
2. A restrição não inventa nada: num traço sem cristalização fria o detector
   se comporta como antes (o bound é `None`).
3. O detector de cristalização fria não dispara em traço limpo que não tem o
   evento -- um falso positivo aqui suprimiria uma Tg real.

O que estes testes NÃO afirmam
------------------------------
A Tg continua fora do valor de literatura no PLLA (cerca de 87 C contra 60-65).
A restrição de ordenação torna o resultado possível, não correto. O degrau real
em 55 C é rejeitado pelo gate de simetria (`_MIN_TG_SYMMETRY`), porque sua
janela de medida a jusante alcança a queda da cristalização fria e mede um
declive muito maior do que o de montante (razão 0.083 contra o mínimo de 0.5).
Consertar isso exige mudar o gate de simetria, que existe para rejeitar flanco
de fusão e é o que impede um pico de fusão de virar Tg. Ver a seção "What is
not established" do paper.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core.thermal import (
    _clean_curve,
    _find_cold_crystallisation,
    _smooth,
    analyse_dsc,
)

PLLA = "DSC_PLLA_50K_2nd_heating.dat"
PLLA_DIR = "/home/hermes/pat-test-data"


def _load_plla(name: str = PLLA):
    """Carrega um traco real de PLLA; pula se o dataset nao estiver presente."""
    from pathlib import Path

    path = Path(PLLA_DIR) / name
    if not path.exists():
        pytest.skip(f"{path} nao esta presente (dataset do Zenodo 17288962)")
    d = np.loadtxt(path)
    return d[:, 0], d[:, 1]


def _clean(temperature, heat_flow):
    return _clean_curve(temperature, heat_flow, "temperature", "heat_flow")


def _synthetic_without_cold_crystallisation():
    """Traco com degrau de Tg e rampa de fusao, sem cristalizacao fria."""
    rng = np.random.default_rng(0)
    T = np.linspace(-10.0, 200.0, 6000)
    hf = 0.02 * np.tanh((T - 85.0) / 1.0)
    hf += 0.08 * np.tanh((T - 170.0) / 4.0)
    hf += 3.0e-4 * (T - 100.0)
    hf += rng.normal(0.0, 3.0e-4, T.size)
    return T, hf


class TestTheOrderingConstraint:
    def test_the_cold_crystallisation_peak_is_found(self):
        """O evento existe no traco real e o detector o localiza."""
        T, hf = _load_plla()
        T2, y = _clean(T, hf)
        found = _find_cold_crystallisation(T2, _smooth(y, 11), None)
        assert found is not None, (
            "cristalizacao fria nao encontrada no traco de PLLA_50K, onde ela "
            "esta clara (minimo exotermico em cerca de 92 C)"
        )
        assert 85.0 < found < 100.0, (
            f"cristalizacao fria em {found:.1f} C, esperado entre 85 e 100 C"
        )

    def test_the_reported_tg_is_not_above_the_cold_crystallisation_peak(self):
        """
        A impossibilidade fisica nao pode voltar.

        Este e o teste que falhava antes: a Tg saia em 94.7 C contra um pico
        exotermico em 91.8 C.
        """
        T, hf = _load_plla()
        T2, y = _clean(T, hf)
        cc = _find_cold_crystallisation(T2, _smooth(y, 11), None)
        result = analyse_dsc(T, hf, heating_rate=10.0)

        assert result.Tg is not None, "nenhuma Tg reportada"
        assert cc is not None, "cristalizacao fria nao detectada"
        assert result.Tg < cc, (
            f"Tg reportada em {result.Tg:.1f} C, em cima ou acima do pico de "
            f"cristalizacao fria em {cc:.1f} C -- impossivel: depois de "
            "cristalizar nao ha fase amorfa para produzir o degrau"
        )

    def test_none_is_returned_when_there_is_no_cold_crystallisation(self):
        """
        A restricao so pode remover candidatos, nunca criar um.

        Num traco sem cristalizacao fria o detector tem de devolver None, para
        que o comportamento do detector de Tg fique inalterado. Um falso
        positivo aqui suprimiria a Tg real -- foi o que aconteceu quando o
        detector aceitava a rampa de fusao (bound espurio em 161 C num traco
        cuja Tg esta em 85 C).
        """
        T, hf = _synthetic_without_cold_crystallisation()
        T2, y = _clean(T, hf)
        assert _find_cold_crystallisation(T2, _smooth(y, 11), None) is None, (
            "cristalizacao fria reportada num traco que nao tem o evento"
        )


class TestNoRegressionOnRealTraces:
    @pytest.mark.parametrize(
        "name",
        [
            "DSC_PLLA_10K_2nd_heating.dat",
            "DSC_PLLA_25K_2nd_heating.dat",
            "DSC_PLLA_50K_2nd_heating.dat",
        ],
    )
    def test_a_transition_is_still_reported(self, name):
        """A restricao nao pode zerar a deteccao nos tracos que ela toca."""
        T, hf = _load_plla(name)
        result = analyse_dsc(T, hf, heating_rate=10.0)
        assert result.Tg is not None, f"{name}: nenhuma Tg reportada"
        assert result.Tm is not None, f"{name}: nenhum Tm reportado"
