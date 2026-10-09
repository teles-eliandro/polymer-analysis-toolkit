"""
A comparison must say "not comparable" rather than mislead.

The tri-state verdict exists because a two-state one produces a confident wrong
answer in four situations. Each has a test here, and the tests are written so
that removing the NOT_COMPARABLE branch makes them fail rather than silently
degrade -- that branch is the feature, not an error path.

The case that motivated it: on the repository's own 116 real DSC traces the
detector reported a glass transition of 160-176 °C for polypropylene, whose real
Tg is about -10 °C. Comparing that against the published PP range returns
"outside", which reads as a finding about the sample. It is a statement about
the detector. The distinction is what these tests protect.
"""

from __future__ import annotations

from app.core.compare import (
    NOT_COMPARABLE,
    OUTSIDE,
    WITHIN,
    compare_property,
    compare_result,
)
from app.core.reference import REPERTOIRE, resolve


def test_a_value_inside_the_published_range_is_within():
    ps = resolve("PS")
    c = compare_property("Tg", 100.0, "°C", ps)
    assert c.verdict == WITHIN
    assert c.reference is not None
    assert c.reference.contains(100.0)


def test_a_value_outside_the_range_is_outside():
    ps = resolve("PS")
    c = compare_property("Tg", 160.0, "°C", ps)
    assert c.verdict == OUTSIDE


def test_the_range_boundaries_are_inclusive():
    """A value exactly on the boundary is inside; the bounds are the data."""
    ps = resolve("PS")
    ref = ps.properties["Tg"]
    assert compare_property("Tg", ref.low, "°C", ps).verdict == WITHIN
    assert compare_property("Tg", ref.high, "°C", ps).verdict == WITHIN


def test_an_unidentified_polymer_is_not_comparable():
    """
    The first reason for the third state: comparing against the wrong polymer's
    range produces a confident wrong answer.
    """
    c = compare_property("Tg", 100.0, "°C", None)
    assert c.verdict == NOT_COMPARABLE
    assert c.reason and "not identified" in c.reason


def test_an_unstable_suggestion_is_never_compared():
    """
    The second and most important reason. The analysis has already said it does
    not trust this number; comparing it would launder that doubt into an
    apparent measurement.
    """
    pp = resolve("PP")
    # The real failure from the 116-trace set: Tg reported on the melting flank.
    c = compare_property(
        "Tg", 165.0, "°C", pp, confidence="suggested", stable=False
    )
    assert c.verdict == NOT_COMPARABLE, (
        "a value the analysis flagged as unstable must not be compared"
    )
    assert c.reason and "stability" in c.reason
    # And crucially it does NOT come back as OUTSIDE, which would read as a
    # finding about the sample.
    assert c.verdict != OUTSIDE


def test_a_stable_suggestion_is_compared():
    """Stability False blocks the comparison; stability True does not."""
    ps = resolve("PS")
    c = compare_property(
        "Tg", 100.0, "°C", ps, confidence="suggested", stable=True
    )
    assert c.verdict == WITHIN


def test_a_missing_property_is_not_comparable():
    """No published range for this property of this polymer."""
    ps = resolve("PS")
    c = compare_property("Tm", 170.0, "°C", ps)
    assert c.verdict == NOT_COMPARABLE
    assert c.reason and "No published range" in c.reason


def test_a_missing_measurement_is_not_comparable():
    ps = resolve("PS")
    c = compare_property("Tg", None, "°C", ps)
    assert c.verdict == NOT_COMPARABLE


class TestReasonCodes:
    """
    Every NOT_COMPARABLE carries a stable code beside its English prose.

    The code exists so a client presenting another language can translate the
    reason without the backend holding translation tables. What matters is
    that the two never drift: a verdict with prose but no code would fall back
    to English in the Portuguese and Spanish interfaces, and a code with no
    prose would leave nothing to show a client that does not know it.
    """

    def test_every_not_comparable_carries_a_code_and_prose(self):
        cases = [
            ("unidentified polymer", compare_property("Tg", 100.0, "°C", None)),
            ("missing measurement", compare_property("Tg", None, "°C", resolve("PS"))),
            (
                "unstable suggestion",
                compare_property(
                    "Tg", 165.0, "°C", resolve("PP"),
                    confidence="suggested", stable=False,
                ),
            ),
            ("no range for property", compare_property("Tm", 170.0, "°C", resolve("PS"))),
            (
                "unit mismatch",
                compare_property("Tg", 373.0, "K", resolve("PS")),
            ),
        ]
        for label, c in cases:
            assert c.verdict == NOT_COMPARABLE, label
            assert c.reason, f"{label}: no prose to fall back on"
            assert c.reason_code, f"{label}: no code for a translated client"

    def test_the_codes_are_distinct(self):
        """Each reason must be separately translatable."""
        codes = {
            compare_property("Tg", 100.0, "°C", None).reason_code,
            compare_property("Tg", None, "°C", resolve("PS")).reason_code,
            compare_property(
                "Tg", 165.0, "°C", resolve("PP"),
                confidence="suggested", stable=False,
            ).reason_code,
            compare_property("Tm", 170.0, "°C", resolve("PS")).reason_code,
            compare_property("Tg", 373.0, "K", resolve("PS")).reason_code,
        }
        assert len(codes) == 5, f"codes collide: {codes}"

    def test_the_codes_survive_serialisation(self):
        """The API serialises through as_dict; the code must be in the JSON."""
        c = compare_property("Tg", 100.0, "°C", None)
        d = c.as_dict()
        assert d["reason_code"] == c.reason_code
        assert d["reason"] == c.reason

    def test_a_comparable_verdict_carries_no_reason_code(self):
        """A code on a 'within' verdict would be meaningless, so it is absent."""
        c = compare_property("Tg", 100.0, "°C", resolve("PS"))
        assert c.verdict == WITHIN
        assert c.reason_code is None
        assert c.reason is None


def test_a_unit_mismatch_is_not_converted_silently():
    """
    Kelvin against a Celsius range must not be silently compared: the value
    would be reported as far outside a range it is actually inside.
    """
    ps = resolve("PS")
    c = compare_property("Tg", 373.15, "K", ps)
    assert c.verdict == NOT_COMPARABLE
    assert c.reason and "K" in c.reason


def test_the_repertoire_resolves_real_sample_names():
    """
    Instrument files carry names written by whoever ran them. A repertoire that
    only matches clean names never fires on real data.
    """
    cases = {
        "PLA1-AR": "PLA",
        "PLA-GF-Feb2021-NC,1": "PLA",
        "EVA2-cryo": "EVA",
        "PE-NEW-AR": "PE",
        "PP3-CRYO": "PP",
        "PMMA4_cryo": "PMMA",
        "PS5-AR": "PS",
        "ABS2_AR": "ABS",
        "PVC1-AR": "PVC",
        "Nylon66-AR": "PA66",
        "Nylon6-AR": "PA6",
    }
    for name, expected in cases.items():
        p = resolve(name)
        assert p is not None, f"{name!r} did not resolve"
        assert p.key == expected, f"{name!r} resolved to {p.key}, not {expected}"


def test_an_unknown_name_resolves_to_nothing_rather_than_a_guess():
    """
    Guessing the polymer is how a comparison produces a confident wrong answer.
    """
    for name in ("", "UNKNOWN-XYZ", "sample-42", None):
        assert resolve(name) is None


def test_delta_Hm_has_a_reference_enthalpy_only_where_one_is_published():
    """
    The crystallinity denominator is a published property in its own right, and
    it is not available for every polymer. Inventing one would silently corrupt
    every crystallinity figure derived from it.
    """
    for key in ("PE", "PP", "PET", "PLA", "PCL"):
        assert "delta_Hm" in REPERTOIRE[key].properties, key
    # PS is amorphous; a 100 % crystalline reference enthalpy is meaningless.
    assert "delta_Hm" not in REPERTOIRE["PS"].properties


def test_compare_result_reports_every_comparable_property():
    """One entry per comparable property, so the interface can render a table."""
    out = compare_result("PLA1-AR", {"Tg": 60.0, "Tm": 151.2, "delta_Hm": None})
    props = {c.property for c in out}
    assert props == {"Tg", "Tm", "delta_Hm"}


def test_compare_result_blocks_an_unstable_suggestion():
    """
    End to end: the claim note carries the stability outcome, and the comparison
    respects it without needing a new field per property.
    """
    class Claim:
        confidence = "suggested"
        note = (
            "A suggested glass transition that did NOT survive the resampling "
            "test: it moves more than 3 K with the sampling of this trace."
        )

    out = compare_result(
        "PP3-CRYO", {"Tg": 165.0}, claims={"Tg": Claim()}
    )
    tg = next(c for c in out if c.property == "Tg")
    assert tg.verdict == NOT_COMPARABLE
