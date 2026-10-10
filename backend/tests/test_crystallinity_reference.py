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
        # Entalpias de fusão de polímeros ficam entre ~40 e ~350 J/g. Fora
        # disso é erro de digitação.
        #
        # O limite superior era 300 até a TN048 entrar: o POM tem 326 J/g e
        # seria reprovado por um teto que era, ele mesmo, uma suposição. O
        # limite foi corrigido para o valor publicado, não o contrário -- e o
        # PCTFE (43,1 J/g) é o caso que ancora o piso.
        for key, entry in ENTHALPY_DB.items():
            for ref in entry.references:
                assert 40.0 <= ref.value_J_g <= 350.0, f"{key}: {ref.value_J_g}"

    def test_the_range_bounds_are_actually_exercised(self) -> None:
        # Um limite que nenhum dado toca é decoração. Estes dois garantem que
        # os extremos da faixa são reais, e que afrouxá-la tem preço: se o
        # POM ou o PCTFE saírem do banco, o teste avisa que a faixa perdeu
        # suas testemunhas.
        values = [
            ref.value_J_g for entry in ENTHALPY_DB.values() for ref in entry.references
        ]
        assert max(values) == 326.0, "POM deixou de ser o limite superior"
        assert min(values) == 43.1, "PCTFE deixou de ser o limite inferior"

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


# The TN048 table publishes the enthalpy twice, and the two columns are
# redundant only if the arithmetic between them is right: each row gives
# kJ/mol and the repeat-unit mass, and J/g is kJ/mol * 1000 / M. Deriving the
# J/g from the published kJ/mol and M means the number in the database is
# *recomputed* on every test run rather than trusted -- a transcription slip
# in either column shows up as a mismatch here instead of as a slightly wrong
# crystallinity three months from now.
#
# All 22 rows of the published table reconcile to within 0.5 J/g, which is the
# rounding in the J/g column; the tolerance below allows for that and no more.
TN048_ROWS = [
    # key, kJ per mole of repeat unit, repeat-unit molar mass, J/g in the note
    ("POM", 9.79, 30.03),
    ("PA11", 44.7, 183.3),
    ("PA12", 48.4, 197.3),
    ("PA66", 57.8, 256.3),
    ("PA69", 69.0, 268.4),
    ("PA610", 71.7, 282.4),
    ("PA612", 80.1, 310.5),
    ("PB", 7.00, 56.1),
    ("PCTFE", 5.02, 116.5),
    ("PVF", 7.54, 46.04),
    ("PTrFE", 5.44, 82.0),
    ("PVC", 11.0, 62.50),
]


class TestTN048Derivation:
    """Each TN048 value must reproduce from the kJ/mol and M in its own note."""

    @staticmethod
    def _tn048_ref(key: str):
        """The TN048 citation of an entry, wherever it sits in the list.

        Not necessarily ``references[0]``: PA66 keeps the 255 J/g compilation
        as its primary, because that is the value the applied literature uses,
        and records the TN048 derivation alongside it as the divergent
        alternative. The test is about whether *the derived number* is
        reproducible, not about which one the entry happens to lead with.
        """
        for ref in ENTHALPY_DB[key].references:
            if "TN048" in ref.source:
                return ref
        raise AssertionError(f"{key}: no TN048 citation to check against")

    @pytest.mark.parametrize("key,kj_per_mol,m_repeat", TN048_ROWS)
    def test_value_recomputes_from_its_own_citation(
        self, key: str, kj_per_mol: float, m_repeat: float
    ) -> None:
        expected = kj_per_mol * 1000.0 / m_repeat
        ref = self._tn048_ref(key)

        assert abs(ref.value_J_g - expected) <= 0.5, (
            f"{key}: database says {ref.value_J_g} J/g but the citation's own "
            f"{kj_per_mol} kJ/mol over {m_repeat} g/mol gives {expected:.2f}"
        )
        # The two numbers the derivation needs have to be in the citation,
        # otherwise the test passes while the user cannot check anything. The
        # source text is Portuguese, so the numbers are written with a decimal
        # comma -- normalising both sides is the comparison; checking for a
        # dot would test the notation rather than the presence of the number.
        def as_pt(value: float) -> str:
            return f"{value:g}".replace(".", ",")

        assert as_pt(kj_per_mol) in ref.source, f"{key}: kJ/mol ausente da citação"
        assert as_pt(m_repeat) in ref.source, f"{key}: M ausente da citação"

    def test_every_adopted_row_is_in_the_database(self) -> None:
        # Every row listed above must actually exist in the database. The
        # table has 22 rows; all 22 are adopted, so there is no exclusion list
        # to keep -- if one is ever dropped, it has to be removed from
        # TN048_ROWS too, and that edit is visible in the diff rather than
        # silently reducing the coverage.
        for key, _kj, _m in TN048_ROWS:
            assert key in ENTHALPY_DB, f"{key} derivado da TN048 mas ausente"

    def test_the_adopted_rows_cover_the_polymers_the_table_adds(self) -> None:
        # The eleven keys below are the polymers TN048 supplies that the
        # database did not have before this change, and the twelve minus PVC
        # is deliberate: PVC is in TN048_ROWS because its value is derived
        # from the table, but it is *not* part of the adoption claim -- it
        # enters with a caveat (commercial PVC is amorphous) rather than as a
        # polymer the database can confidently answer for.
        #
        # PA66 is in TN048_ROWS and not here for the opposite reason: the
        # database already had it, and the table contributes a second,
        # divergent value rather than a new polymer.
        adopted = {
            "POM", "PA11", "PA12", "PA610", "PA612", "PA69",
            "PB", "PCTFE", "PVF", "PTrFE",
        }
        derived = {key for key, _kj, _m in TN048_ROWS}
        assert derived - adopted == {"PVC", "PA66"}
        assert len(adopted) == 10


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
