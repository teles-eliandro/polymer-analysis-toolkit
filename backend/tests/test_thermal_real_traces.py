"""
TGA against two real instrument traces, not synthetic idealisations.

Both come from Zenodo 10.5281/zenodo.18940798 (a study of PLA and PLA/PHA
blends for additive manufacturing) and are stored verbatim at stride 4.

The point of these is that synthetic logistic steps, which every other
thermal test uses, are smooth where a real trace is not, and they never
reproduce the awkward cases. The PLA/PHA blend is the awkward case: a
faint early loss from one component riding on the strong loss of the
other, with no valley between them.
"""

import json
from pathlib import Path

import pytest

from app.core.thermal import analyse_tga

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> tuple[list[float], list[float]]:
    data = json.loads((FIXTURES / f"{name}.json").read_text())
    return data["temperature_C"], data["mass_pct"]


def test_pla_matches_its_known_degradation():
    """
    PLA decomposes in one step near 360 C and leaves almost no residue. These
    are the values the source dataset reports for this trace.
    """
    T, m = _load("tga_pla_pure")
    r = analyse_tga(T, m)
    assert r.T_max_rate == pytest.approx(362.0, abs=8.0)
    assert r.residue_pct == pytest.approx(1.1, abs=0.5)
    assert len(r.steps) == 1
    # One step carrying essentially the whole mass loss, starting around 290 C.
    assert r.steps[0]["loss_pct"] > 90.0
    assert 270.0 < r.steps[0]["onset_C"] < 300.0


def test_pla_pha_blend_is_not_split_into_a_fake_second_step():
    """
    The blend loses 6.7 % over 200-300 C (its PHA fraction) before the main
    88.3 % over 300-400 C (its PLA fraction). There is no valley between the
    two: the rate of loss rises through the shoulder without falling.

    Fitting two sigmoids to force a split returns anything from 9.8 % to
    40.3 % for the first fraction depending on the starting guess, against a
    true 6.7 %, so the honest answer is one step plus a note. This test pins
    that: it would fail if a decomposition feature were ever added on the
    strength of a better curve fit.
    """
    T, m = _load("tga_pla_pha_blend")
    r = analyse_tga(T, m)
    assert len(r.steps) == 1
    # The single step does span both events.
    assert r.steps[0]["onset_C"] < 270.0
    assert r.steps[0]["end_C"] > 400.0
    # And the reader is told the early loss is inside it rather than separate.
    assert any("riding on the main decomposition" in n for n in r.notes)


def test_pla_pha_blend_is_less_stable_than_pla():
    """
    The physical reason the blend matters: the PHA fraction decomposes first,
    so the blend reaches 5 % and 10 % loss at a lower temperature. Measured
    from the traces, not assumed.
    """
    Tp, mp = _load("tga_pla_pure")
    Tb, mb = _load("tga_pla_pha_blend")
    pure = analyse_tga(Tp, mp)
    blend = analyse_tga(Tb, mb)
    assert pure.Td_5pct is not None and blend.Td_5pct is not None
    assert pure.Td_10pct is not None and blend.Td_10pct is not None
    assert blend.Td_5pct < pure.Td_5pct
    assert blend.Td_10pct < pure.Td_10pct
    # The gap is real but not huge on this pair.
    assert 15.0 < pure.Td_5pct - blend.Td_5pct < 60.0


def test_real_traces_balance_their_mass():
    """
    The invariant that must hold on every trace, real or synthetic: the steps
    plus the unattributed remainder equal the mass actually lost.

    Compared against the module's own smoothed endpoints rather than the raw
    first and last samples, because a raw DSC/TGA export opens with a settling
    sample that is not part of the measurement.
    """
    for name in ("tga_pla_pure", "tga_pla_pha_blend", "tga_pei_25000"):
        T, m = _load(name)
        r = analyse_tga(T, m)
        attributed = sum(s["loss_pct"] for s in r.steps) + r.unattributed_loss_pct
        # r.mass_pct is the smoothed curve the analysis worked on.
        assert attributed == pytest.approx(r.mass_pct[0] - r.mass_pct[-1], abs=0.5), name
        assert attributed > 0.0, name
