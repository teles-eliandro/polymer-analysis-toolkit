"""
The glass transition must come with an idea of how much to trust it.

The exercise that prompted this: use PAT as a lab researcher would, on real
instrument data. The numbers were useful, but every one of them arrived as a
bare float with no indication of whether it was solid to a degree or to
twenty. Measured on the real ABS trace (figshare 24462004), adding noise at
the level a real instrument carries moves the reported Tg by 7-14 C, and the
tool says nothing about it -- it prints one number and stops.

For a researcher that is the difference between a publishable value and a
retracted one. So the transition now carries a footing: how stable the
detection is when the data is resampled. This is deliberately *not* a claim
about accuracy (which would need a certified reference material); it is a
statement about the method's own sensitivity to the particular trace it was
given, which is the part the tool can honestly know.
"""

import numpy as np

from app.core.thermal import analyse_dsc


def _quiet_trace(n=2000, seed=1):
    """An isothermal-ish baseline: no transition of any kind."""
    rng = np.random.default_rng(seed)
    T = np.linspace(20.0, 220.0, n)
    return T, -0.10 + rng.normal(0, 0.0004, n)


# --------------------------------------------------------------------------
# A stable transition reports a small spread; an unstable one a large spread.
# --------------------------------------------------------------------------


def test_a_clean_glass_transition_is_reported_as_well_determined():
    """A strong, isolated Tg must not be flagged as doubtful."""
    T = np.linspace(20.0, 120.0, 1500)
    hf = -0.10 + 0.35 / (1 + np.exp(-(T - 75.0) / 3.0))

    r = analyse_dsc(list(T), list(hf), heating_rate=10.0)

    assert r.Tg is not None
    assert abs(r.Tg - 75.0) < 5.0
    # A large step in a quiet trace: the answer must not wander.
    assert r.Tg_uncertainty_C is not None
    assert r.Tg_uncertainty_C < 3.0, (
        f"a clean 0.35 W/g step was reported with +/-{r.Tg_uncertainty_C:.1f} C"
    )
    assert r.Tg_reliable is True


def test_a_barely_visible_step_is_reported_as_uncertain():
    """
    When the step is a small fraction of the trace, the detection depends on
    the sampling and the value must be marked as such rather than published.
    """
    T = np.linspace(20.0, 220.0, 800)
    rng = np.random.default_rng(3)
    # A Tg step that is tiny next to the noise on this trace.
    hf = -0.10 + 0.004 / (1 + np.exp(-(T - 75.0) / 4.0)) + rng.normal(0, 0.002, len(T))

    r = analyse_dsc(list(T), list(hf), heating_rate=10.0)

    assert r.Tg_uncertainty_C is not None
    assert r.Tg_uncertainty_C > 5.0, (
        "a step buried in noise was reported as well determined"
    )
    assert r.Tg_reliable is False


def test_a_trace_with_no_transition_gets_no_fabricated_certainty():
    """No Tg means no claim either way -- the footing fields stay None."""
    T, hf = _quiet_trace()
    r = analyse_dsc(list(T), list(hf), heating_rate=10.0)

    if r.Tg is None:
        assert r.Tg_uncertainty_C is None
        assert r.Tg_reliable is None


def test_the_uncertainty_is_not_a_constant():
    """
    A footing that never changes carries no information. Two traces of very
    different quality must not receive the same spread.
    """
    T1 = np.linspace(20.0, 120.0, 1500)
    clean = -0.10 + 0.35 / (1 + np.exp(-(T1 - 75.0) / 3.0))
    r_clean = analyse_dsc(list(T1), list(clean), heating_rate=10.0)

    T2 = np.linspace(20.0, 220.0, 800)
    rng = np.random.default_rng(3)
    muddy = -0.10 + 0.004 / (1 + np.exp(-(T2 - 75.0) / 4.0)) + rng.normal(0, 0.002, len(T2))
    r_muddy = analyse_dsc(list(T2), list(muddy), heating_rate=10.0)

    assert r_clean.Tg_uncertainty_C != r_muddy.Tg_uncertainty_C


def test_uncertainty_is_never_negative():
    T = np.linspace(20.0, 120.0, 900)
    hf = -0.10 + 0.2 / (1 + np.exp(-(T - 75.0) / 3.0))
    r = analyse_dsc(list(T), list(hf), heating_rate=10.0)
    if r.Tg_uncertainty_C is not None:
        assert r.Tg_uncertainty_C >= 0.0
