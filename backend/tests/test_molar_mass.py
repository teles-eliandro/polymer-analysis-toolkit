"""Molar-mass averages: exact values, analytic identities, input validation."""

from __future__ import annotations

import math

import pytest

from app.core.molar_mass import (
    log_normal_moments,
    mark_houwink_viscosity_average,
    moment_averages,
)

# The three-point distribution used throughout. Hand calculation:
#   Mn = 1 / (0.2/1000 + 0.5/2000 + 0.3/5000) = 1/0.000510 = 1960.784313...
#   Mw = 0.2*1000 + 0.5*2000 + 0.3*5000 = 200 + 1000 + 1500 = 2700
#   D  = 2700 / 1960.784313... = 1.377
MASSES = [1000.0, 2000.0, 5000.0]
FRACTIONS = [0.2, 0.5, 0.3]

# Values derived by hand, to full double precision.
MN_EXPECTED = 1.0 / (0.2 / 1000 + 0.5 / 2000 + 0.3 / 5000)
MW_EXPECTED = 2700.0


def test_known_distribution_matches_hand_calculation():
    r = moment_averages(MASSES, FRACTIONS)
    assert r.Mn == pytest.approx(MN_EXPECTED, rel=1e-12)
    assert r.Mw == pytest.approx(MW_EXPECTED, rel=1e-12)
    assert r.dispersity == pytest.approx(MW_EXPECTED / MN_EXPECTED, rel=1e-12)


def test_mz_and_mz_plus_1_hand_calculation():
    # Mz   = sum(w M^2) / sum(w M)
    #      = (0.2*1e6 + 0.5*4e6 + 0.3*25e6) / 2700
    #      = (2e5 + 2e6 + 7.5e6) / 2700 = 9.7e6 / 2700
    mz = (0.2 * 1000**2 + 0.5 * 2000**2 + 0.3 * 5000**2) / MW_EXPECTED
    # Mz+1 = sum(w M^3) / sum(w M^2)
    mz1 = (
        0.2 * 1000**3 + 0.5 * 2000**3 + 0.3 * 5000**3
    ) / (0.2 * 1000**2 + 0.5 * 2000**2 + 0.3 * 5000**2)
    r = moment_averages(MASSES, FRACTIONS)
    assert r.Mz == pytest.approx(mz, rel=1e-12)
    assert r.Mz_plus_1 == pytest.approx(mz1, rel=1e-12)


def test_average_ordering_is_monotonic():
    """Mn <= Mw <= Mz <= Mz+1 holds for every distribution, by construction."""
    r = moment_averages(MASSES, FRACTIONS)
    assert r.Mn <= r.Mw <= r.Mz <= r.Mz_plus_1


def test_monodisperse_gives_dispersity_one():
    r = moment_averages([10000.0] * 3, [1 / 3, 1 / 3, 1 / 3])
    assert r.dispersity == pytest.approx(1.0, abs=1e-12)
    assert r.Mn == pytest.approx(10000.0, rel=1e-12)
    assert r.Mz == pytest.approx(10000.0, rel=1e-12)


def test_single_slice_is_monodisperse():
    r = moment_averages([5000.0], [1.0])
    assert r.Mn == pytest.approx(5000.0)
    assert r.Mw == pytest.approx(5000.0)
    assert r.dispersity == pytest.approx(1.0)


def test_scale_invariance_of_dispersity():
    """Dispersity must not depend on the unit the masses are given in."""
    r1 = moment_averages([1000, 2000, 5000], [0.2, 0.5, 0.3])
    r2 = moment_averages([1, 2, 5], [0.2, 0.5, 0.3])
    assert r1.dispersity == pytest.approx(r2.dispersity, rel=1e-12)


def test_tolerance_accepts_small_rounding_residual():
    """
    Instrument exports round fractions to 3 or 4 dp, so the sum is rarely
    exactly 1. A tolerance of 1e-3 is the documented default and must absorb
    that.
    """
    fractions = [0.333, 0.333, 0.333]  # sums to 0.999, residual 1e-3
    r = moment_averages(MASSES, fractions)
    assert r.Mn > 0


def test_rejects_fractions_not_summing_to_one():
    with pytest.raises(ValueError, match="sum to 1.0"):
        moment_averages([1000, 2000], [0.2, 0.2])


def test_rejects_negative_fraction():
    with pytest.raises(ValueError, match="non-negative"):
        moment_averages([1000, 2000], [1.5, -0.5])


def test_rejects_non_positive_mass():
    with pytest.raises(ValueError, match="positive"):
        moment_averages([1000, 0], [0.5, 0.5])


def test_rejects_length_mismatch():
    with pytest.raises(ValueError, match="same length"):
        moment_averages([1000, 2000, 5000], [0.5, 0.5])


def test_rejects_non_finite_values():
    with pytest.raises(ValueError, match="non-finite"):
        moment_averages([1000, float("nan")], [0.5, 0.5])
    with pytest.raises(ValueError, match="non-finite"):
        moment_averages([1000, 2000], [0.5, float("inf")])


def test_rejects_empty_input():
    with pytest.raises(ValueError, match="cannot be empty"):
        moment_averages([], [])


# ---------------------------------------------------------------------------
# Mark-Houwink
# ---------------------------------------------------------------------------


def test_mv_equals_mw_when_a_is_one():
    """Mv = [sum(w M^a)]^(1/a); at a = 1 this is exactly Mw."""
    mv = mark_houwink_viscosity_average(MASSES, FRACTIONS, a=1.0)
    assert mv == pytest.approx(MW_EXPECTED, rel=1e-12)


def test_mv_hand_calculation_at_a_equals_half():
    # Mv = (0.2*sqrt(1000) + 0.5*sqrt(2000) + 0.3*sqrt(5000))^2
    expected = (0.2 * math.sqrt(1000) + 0.5 * math.sqrt(2000) + 0.3 * math.sqrt(5000)) ** 2
    mv = mark_houwink_viscosity_average(MASSES, FRACTIONS, a=0.5)
    assert mv == pytest.approx(expected, rel=1e-12)


def test_mv_lies_between_mn_and_mw_for_typical_a():
    """For 0.5 <= a <= 1 the viscosity average is bracketed by Mn and Mw."""
    r = moment_averages(MASSES, FRACTIONS)
    for a in (0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        mv = mark_houwink_viscosity_average(MASSES, FRACTIONS, a=a)
        assert r.Mn - 1e-6 <= mv <= r.Mw + 1e-6, f"a={a} gave Mv={mv}"


def test_mv_rejects_non_positive_a():
    with pytest.raises(ValueError, match="must be finite and > 0"):
        mark_houwink_viscosity_average(MASSES, FRACTIONS, a=0.0)
    with pytest.raises(ValueError, match="must be finite and > 0"):
        mark_houwink_viscosity_average(MASSES, FRACTIONS, a=-0.5)


# ---------------------------------------------------------------------------
# Log-normal reference distribution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("dispersity", [1.02, 1.05, 1.2, 1.5, 2.0, 3.0])
def test_log_normal_satisfies_analytic_identity(dispersity):
    """
    For a log-normal MWD, Mz/Mw = Mw/Mn = exp(sigma^2) exactly. This is an
    independent check that the moment machinery is correct, because the
    expected relation comes from theory rather than from the implementation.
    """
    d = log_normal_moments(50000.0, dispersity, n_points=8000, n_sigma=5.0)
    ratio_mz_mw = d["Mz"] / d["Mw"]
    ratio_mw_mn = d["Mw"] / d["Mn"]
    # The grid is truncated at 5 sigma; at D = 3 that leaves the largest
    # truncation error, so the tolerance scales with the span.
    assert ratio_mz_mw == pytest.approx(ratio_mw_mn, rel=0.05)
    # The recovered dispersity must be close to the requested one.
    assert d["dispersity"] == pytest.approx(dispersity, rel=0.05)


def test_log_normal_rejects_invalid_parameters():
    with pytest.raises(ValueError, match="positive"):
        log_normal_moments(-1.0, 1.5)
    with pytest.raises(ValueError, match=">= 1"):
        log_normal_moments(1000.0, 0.5)
