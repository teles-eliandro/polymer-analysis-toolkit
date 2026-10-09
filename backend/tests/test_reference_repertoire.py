"""
The repertoire must never resolve a name to the wrong polymer.

This file guards the two ways an expanded repertoire goes wrong quietly.

The first is a dead alias: an alias whose target key has no entry. That does
not raise, it does not warn, and it does not look like a bug -- the user types
PEEK, the alias table matches, the lookup misses, and the interface reports
"the polymer was not identified". The reason shown is then about the input
rather than about the data, which is a worse failure than no answer. PEEK,
PPSU and PTFE were in exactly that state.

The second is shadowing. Names are resolved by matching the longest alias that
prefixes the cleaned sample name, so a short alias can steal a name meant for
a longer one: "pa" would take "pa12" to nylon-6, and "pp" would take "pps" to
polypropylene. Both are valid polymers with published ranges thirty degrees
apart, so the comparison would look successful and be wrong. These tests fail
if an alias is shadowed, which is the only reliable way to catch it -- the
output of a shadowed alias is a plausible answer, not an error.
"""

from __future__ import annotations

import pytest

from app.core.reference import ALIASES, REPERTOIRE, resolve


def test_every_alias_points_at_an_entry_that_exists():
    """No alias may be a dead end."""
    dead = sorted({target for target in ALIASES.values()} - set(REPERTOIRE))
    assert dead == [], f"aliases point at entries that do not exist: {dead}"


def test_every_entry_is_reachable_by_its_own_key():
    """A key absent from the alias table cannot be reached by typing it."""
    unreachable = [
        key
        for key in REPERTOIRE
        if resolve(key.lower()) is None
    ]
    assert unreachable == [], f"entries unreachable by name: {unreachable}"


def test_every_entry_has_at_least_one_property():
    empty = [key for key, p in REPERTOIRE.items() if not p.properties]
    assert empty == [], f"entries with no properties: {empty}"


def test_every_property_range_carries_a_source():
    """
    A range with no citation cannot be checked and does not belong here. This
    is the rule that made the module possible in the first place: the data is
    admissible only because each entry names where it came from.
    """
    missing = []
    for key, polymer in REPERTOIRE.items():
        for prop, ref in polymer.properties.items():
            if not ref.source or not ref.source.strip():
                missing.append(f"{key}.{prop}")
    assert missing == [], f"ranges with no source: {missing}"


def test_every_range_is_ordered_and_positive_width():
    """low <= high, or the comparison silently never matches."""
    bad = []
    for key, polymer in REPERTOIRE.items():
        for prop, ref in polymer.properties.items():
            if ref.low > ref.high:
                bad.append(f"{key}.{prop}: low {ref.low} > high {ref.high}")
    assert bad == [], f"ranges with inverted bounds: {bad}"


def test_every_range_has_a_unit():
    bad = []
    for key, polymer in REPERTOIRE.items():
        for prop, ref in polymer.properties.items():
            if not ref.unit:
                bad.append(f"{key}.{prop}")
    assert bad == [], f"ranges with no unit: {bad}"


class TestAliasShadowing:
    """
    An alias that is shadowed by a shorter one returns the wrong polymer.

    The failure is silent, so each case is asserted explicitly rather than
    relying on a general property that a prefix-matching scheme does not have.
    """

    @pytest.mark.parametrize(
        "name,expected",
        [
            # "pa" would steal these for nylon-6.
            ("pa12", "PA12"),
            ("PA12", "PA12"),
            ("nylon12", "PA12"),
            ("nylon-12", "PA12"),
            ("pa11", "PA11"),
            ("nylon11", "PA11"),
            ("Nylon-11", "PA11"),
            # "pp" would steal pps for polypropylene.
            ("pps", "PPS"),
            ("PPS", "PPS"),
            ("ryton", "PPS"),
            # "ps" would steal psu for polystyrene.
            ("psu", "PSU"),
            ("PSU", "PSU"),
            ("udel", "PSU"),
            # "pe" is a real entry, so its high- and low-density forms must not
            # collapse into it: they melt 25-30 C apart.
            ("ldpe", "LDPE"),
            ("LDPE", "LDPE"),
            ("hdpe", "HDPE"),
            ("HDPE", "HDPE"),
            ("pe", "PE"),
            # "pom" would steal pom-c, "ptfe" the tradename.
            ("pom-c", "POM"),
            ("teflon", "PTFE"),
            ("pvc-u", "PVC-U"),
            ("upvc", "PVC-U"),
            ("uPVC", "PVC-U"),
        ],
    )
    def test_alias_resolves_to_the_specific_polymer(self, name, expected):
        polymer = resolve(name)
        assert polymer is not None, f"{name} did not resolve at all"
        assert polymer.key == expected, (
            f"{name} resolved to {polymer.key}, not {expected} "
            "(a shorter alias is shadowing the longer one)"
        )

    def test_a_specific_name_is_not_shadowed_by_a_generic_one(self):
        """
        The property behind the parametrised cases: for every alias, resolving
        that alias must land on its own target. A shadowed alias is caught here
        even for entries added after this test was written.
        """
        wrong = []
        for alias, target in ALIASES.items():
            polymer = resolve(alias)
            if polymer is None or polymer.key != target:
                got = polymer.key if polymer else None
                wrong.append(f"{alias!r} -> {got!r} (alias table says {target!r})")
        assert wrong == [], "aliases resolved elsewhere: " + "; ".join(wrong)


class TestTheRealInstrumentNamesStillResolve:
    """
    Expansion must not change what the 116 real traces resolve to.

    These are the sample names as they appear in the figshare set and in the
    repository's own results, including the trailing digits and qualifiers that
    real instrument exports carry.
    """

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("ABS2", "ABS"),
            ("ABS3", "ABS"),
            ("PE-NEW", "PE"),
            ("PP3-CRYO", "PP"),
            ("PS5", "PS"),
            ("PVC1", "PVC"),
            ("PLA1-AR", "PLA"),
            ("PLLA", "PLA"),
            ("Nylon6", "PA6"),
            ("NYLON66", "PA66"),
            ("PVA", "PVOH"),
            ("EVA", "EVA"),
            ("EVOH", "EVOH"),
            ("PMMA", "PMMA"),
            ("PET", "PET"),
            ("PBT", "PBT"),
            ("SAN", "SAN"),
            ("PAN", "PAN"),
            ("PK", "PK"),
            ("PCL", "PCL"),
            ("PHB", "PHB"),
            ("PU", "PU"),
            ("PC", "PC"),
            ("POM", "POM"),
        ],
    )
    def test_the_name_resolves_as_before(self, name, expected):
        polymer = resolve(name)
        assert polymer is not None, f"{name} stopped resolving"
        assert polymer.key == expected


class TestTheRepertoireStaysHonest:
    def test_a_name_that_is_not_a_polymer_still_returns_none(self):
        """
        Tolerance must not become guessing. A comparison against the wrong
        polymer's range is a confident wrong answer, so an unrecognised name
        must stay unrecognised.
        """
        for name in ("Kevlar", "unknown-sample", "sample-1", "xyz", ""):
            assert resolve(name) is None, f"{name} should not resolve"

    def test_none_is_not_an_error(self):
        """A pasted trace carries no sample name at all."""
        assert resolve(None) is None

    def test_the_high_temperature_entries_are_present_and_cited(self):
        """
        The specific gap that motivated the expansion: these were in the alias
        table with nothing behind them.
        """
        for key in ("PEEK", "PPSU", "PTFE"):
            assert key in REPERTOIRE, f"{key} has an alias but no entry"
            for prop, ref in REPERTOIRE[key].properties.items():
                assert ref.source, f"{key}.{prop} has no citation"

    def test_pvdf_states_that_its_melting_range_is_polymorph_dependent(self):
        """
        A range that hides a known polymorph split teaches the user nothing.
        Where the literature distinguishes, the entry must say so.
        """
        note = REPERTOIRE["PVDF"].properties["Tm"].note
        assert note and "polymorph" in note.lower()

    def test_ldpe_and_hdpe_do_not_share_a_melting_range(self):
        """
        The commonest error in polymer DSC is treating polyethylene as one
        material. Separate entries are the whole point of adding them.
        """
        ldpe = REPERTOIRE["LDPE"].properties["Tm"]
        hdpe = REPERTOIRE["HDPE"].properties["Tm"]
        assert ldpe.high < hdpe.low, (
            "LDPE and HDPE melting ranges overlap; they must not"
        )
