"""
O banco de entalpias de fusão de 100 % cristalino.

Estes testes verificam três coisas que quebrariam o uso do banco sem que
nenhum número errado aparecesse na tela:

1. Que a detecção pelo nome de amostra funcione nas formas em que os nomes
   realmente chegam (nome de arquivo com prefixo do instrumento, sufixo de
   corrida, qualificador de processamento).
2. Que a detecção **não** confunda polímeros parecidos: ``PEKK`` não é
   polietileno e ``PA46`` não é nylon-6. Um ΔHf100 do polímero errado produz
   uma cristalinidade plausível e errada, que é o pior resultado possível.
3. Que o guarda de >100 % recuse o impossível sem recusar o legítimo.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.core.crystallinity_ref import ENTHALPY_DB, lookup, options
from app.core.thermal import analyse_dsc


class TestLookup:
    def test_resolves_the_polymer_from_a_real_sample_name(self) -> None:
        # O nome do FTIR que o usuário enviou.
        entry = lookup("ldpe sbc 818 0")
        assert entry is not None
        assert entry.key == "PE"
        assert entry.primary is not None
        assert entry.primary.value_J_g == pytest.approx(293.0)

    def test_resolves_through_an_instrument_filename_prefix(self) -> None:
        # "JASCO_LDPE-SBC-818" é como o arquivo se chama no disco.
        entry = lookup("JASCO_LDPE-SBC-818")
        assert entry is not None and entry.key == "PE"
        assert lookup("FTIR_PE-1") is not None
        assert lookup("DSC_PLA").key == "PLA"  # type: ignore[union-attr]

    def test_resolves_run_suffix_and_qualifier(self) -> None:
        assert lookup("PS1-AR").key == "PS"  # type: ignore[union-attr]
        assert lookup("PLA-GF-Feb2021-NC").key == "PLA"  # type: ignore[union-attr]
        assert lookup("PP3-CRYO").key == "PP"  # type: ignore[union-attr]

    def test_nylon_66_is_not_nylon_6(self) -> None:
        # "nylon66" contém "nylon6" como prefixo; a resolução não pode parar
        # no primeiro que casa.
        assert lookup("Nylon-66").key == "PA66"  # type: ignore[union-attr]
        assert lookup("Nylon-6").key == "PA6"  # type: ignore[union-attr]
        assert lookup("PA66-2").key == "PA66"  # type: ignore[union-attr]

    def test_pekk_is_not_polyethylene(self) -> None:
        # PEKK contém "PE" como prefixo. Identificá-lo como polietileno daria
        # a todo PEKK uma cristalinidade de referência de poliolefina.
        assert lookup("PEKK-1") is None

    def test_pa46_is_not_pa6(self) -> None:
        # O dígito faz parte do nome: PA46 é uma poliamida própria.
        assert lookup("PA46") is None

    def test_unknown_and_empty_return_none(self) -> None:
        assert lookup("unknown-xyz") is None
        assert lookup("") is None
        assert lookup(None) is None

    def test_atactic_ps_resolves_without_a_value(self) -> None:
        # O PS comum é amorfo: a resposta certa é "não se aplica", não um
        # número, e nem o valor do PS isotático.
        entry = lookup("PS-1")
        assert entry is not None
        assert entry.key == "PS"
        assert entry.primary is None
        assert "amorfo" in (entry.note or "")


class TestDatabaseIntegrity:
    def test_every_value_has_a_citation(self) -> None:
        # Um valor sem fonte não tem lugar num banco feito para citar.
        for key, entry in ENTHALPY_DB.items():
            for ref in entry.references:
                assert ref.source and len(ref.source) > 20, f"{key}: fonte curta"
                assert ref.value_J_g > 0

    def test_values_are_in_a_physical_range(self) -> None:
        # Entalpias de fusão de polímeros ficam entre ~50 e ~300 J/g. Fora
        # disso é erro de digitação.
        for key, entry in ENTHALPY_DB.items():
            for ref in entry.references:
                assert 50.0 <= ref.value_J_g <= 300.0, f"{key}: {ref.value_J_g}"

    def test_verified_entries_cite_a_doi(self) -> None:
        # O rótulo 'verified' significa que o registro foi conferido, então a
        # citação precisa carregar o DOI que foi conferido.
        for key, entry in ENTHALPY_DB.items():
            for ref in entry.references:
                if ref.confidence == "verified":
                    assert "doi:" in ref.source.lower(), f"{key} sem DOI"

    def test_options_carry_the_citation(self) -> None:
        # O menu do formulário precisa entregar a citação junto com o valor,
        # senão o número circula sem a fonte.
        for opt in options():
            if opt["value_J_g"] is not None:
                assert opt["source"], f"{opt['key']} sem fonte no menu"

    def test_options_are_sorted_and_keyed(self) -> None:
        keys = [o["key"] for o in options()]
        assert keys == sorted(keys)
        assert len(keys) == len(set(keys))


class TestCrystallinityGuard:
    """
    Xc > 100 % é impossível. O valor continua sendo reportado (suprimi-lo
    esconderia o erro, e um campo vazio diz menos que um 124 % visível), mas
    vem acompanhado de um sinal legível por máquina. Estes testes garantem que
    o guarda marque o impossível sem marcar o legítimo.
    """

    T = np.linspace(20.0, 200.0, 3601)

    def _endotherm(self, dh_J_g: float, tm: float = 132.0, sigma: float = 3.0):
        amp = dh_J_g * 10.0 / 60.0 / (sigma * np.sqrt(2.0 * np.pi))
        return amp * np.exp(-((self.T - tm) ** 2) / (2.0 * sigma**2))

    @pytest.mark.parametrize("target_xc", [20.3, 27.1, 30.5])
    def test_legitimate_crystallinity_is_not_flagged(self, target_xc: float) -> None:
        dh = 293.0 * target_xc / 100.0
        r = analyse_dsc(
            self.T.tolist(), self._endotherm(dh).tolist(), heating_rate=10.0,
            ref_enthalpy_J_g=293.0,
        )
        assert r.crystallinity_pct == pytest.approx(target_xc, abs=1.0)
        assert r.crystallinity_refusal is None

    def test_impossible_crystallinity_is_flagged(self) -> None:
        r = analyse_dsc(
            self.T.tolist(), self._endotherm(350.0).tolist(), heating_rate=10.0,
            ref_enthalpy_J_g=293.0,
        )
        # O número é reportado -- e a flag diz que ele não pode estar certo.
        assert r.crystallinity_pct is not None
        assert r.crystallinity_pct > 100.0
        assert r.crystallinity_refusal is not None
        assert "impossível" in r.crystallinity_refusal
        # O ΔHm é medido e continua reportado.
        assert r.delta_Hm is not None

    def test_flag_is_in_the_dict(self) -> None:
        r = analyse_dsc(
            self.T.tolist(), self._endotherm(350.0).tolist(), heating_rate=10.0,
            ref_enthalpy_J_g=293.0,
        )
        d = r.as_dict()
        assert d["crystallinity_refusal"] is not None
        assert d["crystallinity_pct"] is not None
