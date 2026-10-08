"""
Thermal analysis against synthetic traces whose answers are known.

Each trace is built from an explicit analytic form, so the expected value is
computed independently of the code under test. This is what distinguishes
these tests from ones that merely assert a result is positive.
"""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.thermal import analyse_dsc, analyse_tga
from app.main import app

client = TestClient(app)


def _two_step_tga():
    """
    30 % loss centred at 350 C, then 60 % loss centred at 500 C, leaving
    10 % residue. The logistic steps are the standard idealisation of a
    first-order decomposition.
    """
    T = np.linspace(30, 800, 1540)
    m = np.full_like(T, 100.0)
    m -= 30.0 / (1 + np.exp(-(T - 350) / 12))
    m -= 60.0 / (1 + np.exp(-(T - 500) / 10))
    return T, m


def test_tga_residue_matches_construction():
    T, m = _two_step_tga()
    r = analyse_tga(T, m)
    assert r.residue_pct == pytest.approx(10.0, abs=0.2)


def test_tga_td5_is_where_5_percent_has_been_lost():
    """
    Td at 5 % loss must be the temperature at which the trace crosses 95 %
    remaining mass. Verified by locating that crossing independently.
    """
    T, m = _two_step_tga()
    r = analyse_tga(T, m)
    idx = int(np.argmax(m <= 95.0))
    assert r.Td_5pct == pytest.approx(T[idx], abs=1.5)


def test_tga_td10_is_after_td5():
    T, m = _two_step_tga()
    r = analyse_tga(T, m)
    assert r.Td_10pct > r.Td_5pct


def test_tga_detects_both_decomposition_steps():
    T, m = _two_step_tga()
    r = analyse_tga(T, m)
    assert len(r.steps) == 2
    losses = sorted(s["loss_pct"] for s in r.steps)
    # Built as 30 % then 60 %, and the analysis recovers both exactly: the
    # threshold locates each step, then the boundaries are extended to the
    # valley between peaks so the decaying tails are counted with the step they
    # belong to. Without that extension this read 23.8 % and 55.3 %.
    assert losses[0] == pytest.approx(30.0, abs=1.0)
    assert losses[1] == pytest.approx(60.0, abs=1.0)


def test_tga_accounts_for_every_percent_of_mass():
    """
    The steps plus the unattributed remainder must equal the mass actually
    lost. This is the invariant that makes the step list trustworthy: without
    it, a detector that finds only one of two steps looks like a clean result
    rather than an incomplete one.
    """
    T, m = _two_step_tga()
    r = analyse_tga(T, m)
    total_lost = float(m[0] - m[-1])
    attributed = sum(s["loss_pct"] for s in r.steps)
    assert attributed + r.unattributed_loss_pct == pytest.approx(total_lost, abs=0.05)
    # And the remainder is not a way of hiding a missed step: it is the tail,
    # so it stays small relative to the loss.
    assert r.unattributed_loss_pct < 0.25 * total_lost


def test_tga_flags_a_faint_event_riding_on_a_large_step():
    """
    A small loss whose rate never rises to the detection threshold is absorbed
    into the span of a large one. Its mass is accounted for, but a reader must
    be told a soft event is in there: reporting "one step of 76 %" with no note
    hides that the first few percent are moisture rather than polymer.
    """
    T = np.linspace(30, 800, 1541)
    m = np.full_like(T, 100.0)
    m -= 5.0 / (1 + np.exp(-(T - 120) / 15))     # broad, faint moisture loss
    m -= 72.0 / (1 + np.exp(-(T - 430) / 18))    # dominant decomposition
    m += np.random.default_rng(11).normal(0, 0.02, T.size)
    r = analyse_tga(T, m)
    # The mass still balances, whether or not the faint event is split out.
    attributed = sum(s["loss_pct"] for s in r.steps) + r.unattributed_loss_pct
    assert attributed == pytest.approx(float(m[0] - m[-1]), abs=0.05)
    assert any("riding on the main decomposition" in n for n in r.notes)


def test_tga_max_rate_is_the_largest_dtg_peak():
    """
    The tallest DTG peak is the step that loses mass fastest. Here that is
    the second step (60 % lost over a narrower window), which is why the
    docstring warns that T_max_rate is not necessarily the first step.
    """
    T, m = _two_step_tga()
    r = analyse_tga(T, m)
    dtg = -np.gradient(m, T)
    assert r.T_max_rate == pytest.approx(T[int(np.argmax(dtg))], abs=2.0)


def test_tga_single_step_residue_and_td():
    T = np.linspace(25, 600, 1150)
    m = 100.0 - 100.0 / (1 + np.exp(-(T - 400) / 8))
    r = analyse_tga(T, m)
    assert r.residue_pct == pytest.approx(0.0, abs=0.5)
    # 5 % lost happens well before the midpoint of the step.
    assert 360 < r.Td_5pct < 400


def test_tga_rejects_too_few_points():
    with pytest.raises(ValueError):
        analyse_tga([100, 200], [90, 80])


def _dsc_with_tg_and_tm(tg=100.0, tm=165.0):
    """A heat-capacity step at Tg plus a Gaussian melting endotherm at Tm."""
    T = np.linspace(0, 250, 2500)
    step = 0.5 / (1 + np.exp(-(T - tg) / 3))
    hf = 0.3 + step + 3.0 * np.exp(-0.5 * ((T - tm) / 6) ** 2)
    return T, hf


def test_dsc_tg_is_not_confused_with_the_melting_peak():
    """
    Regression test. Detecting Tg as the maximum of |dH/dT| returns the
    melting peak instead of the glass transition, because the flanks of a
    sharp melt are steeper than a broad Tg step. The reported Tg must be
    near the constructed step, not near Tm.
    """
    T, hf = _dsc_with_tg_and_tm(tg=100.0, tm=165.0)
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tg == pytest.approx(100.0, abs=3.0), f"Tg came out as {r.Tg}"
    assert abs(r.Tg - r.Tm) > 30, "Tg collapsed onto the melting peak"


def test_dsc_tm_matches_the_constructed_peak():
    T, hf = _dsc_with_tg_and_tm(tm=165.0)
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tm == pytest.approx(165.0, abs=1.0)


def test_dsc_delta_cp_unit_conversion():
    """
    A step of 0.5 W/g scanned at 10 K/min is
    0.5 / (10/60) = 3.0 J/(g.K). The factor of 60 is the one that is
    routinely forgotten.
    """
    T, hf = _dsc_with_tg_and_tm()
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.delta_cp == pytest.approx(3.0, rel=0.05)


def test_dsc_tg_only_trace():
    """A wholly amorphous polymer: no melting peak, only a Tg step."""
    T = np.linspace(0, 200, 2000)
    hf = 0.2 + 0.8 / (1 + np.exp(-(T - 110) / 4))
    r = analyse_dsc(T, hf, heating_rate=20.0)
    assert r.Tg == pytest.approx(110.0, abs=3.0)


def test_dsc_heat_only_trace_reports_no_glass_transition():
    """
    A trace with only a melting endotherm has no glass transition, so Tg must
    be absent rather than fabricated from whatever residual curvature remains
    after the melting region is excluded.
    """
    T = np.linspace(0, 250, 2500)
    hf = 0.5 + 3.0 * np.exp(-0.5 * ((T - 165) / 8) ** 2)
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tg is None, f"a spurious Tg of {r.Tg} was reported"


def test_dsc_crystallinity_matches_the_reference_enthalpy():
    """
    Crystallinity is delta_Hm / ref_enthalpy. The synthetic peak is a
    Gaussian of height 3.0 W/g and sigma 8 K, whose area is
    3.0 * 8 * sqrt(2*pi) W/g*K; divided by the 10 K/min rate this is a
    melting enthalpy of about 361 J/g. With a 290 J/g reference that gives
    about 124 %, which is physically impossible and therefore the right way
    to expose that the reference must be chosen for the actual polymer.

    The assertion here checks the arithmetic, and a separate test below
    checks that an unphysical value is reported rather than clamped.
    """
    T = np.linspace(0, 250, 2500)
    hf = 0.5 + 3.0 * np.exp(-0.5 * ((T - 165) / 8) ** 2)
    r = analyse_dsc(T, hf, heating_rate=10.0, ref_enthalpy_J_g=290.0)
    expected_enthalpy = (3.0 * 8.0 * np.sqrt(2 * np.pi)) / (10.0 / 60.0)
    assert r.delta_Hm == pytest.approx(expected_enthalpy, rel=0.05)
    assert r.crystallinity_pct == pytest.approx(
        100.0 * expected_enthalpy / 290.0, rel=0.05
    )


def test_dsc_crystallinity_over_100_is_reported_not_hidden():
    """
    When the reference enthalpy is too small for the measured peak the ratio
    exceeds 100 %. That signals a wrong reference (or an overlapping event),
    so the honest response is to return the computed number and let the user
    see it, not to clamp it to 100 and conceal the mistake.
    """
    T = np.linspace(0, 250, 2500)
    hf = 0.5 + 3.0 * np.exp(-0.5 * ((T - 165) / 8) ** 2)
    r = analyse_dsc(T, hf, heating_rate=10.0, ref_enthalpy_J_g=100.0)
    assert r.crystallinity_pct is not None
    assert r.crystallinity_pct > 100.0


def test_dsc_crystallinity_is_about_50_percent_for_a_matching_reference():
    """
    Same peak, but with the reference chosen so the answer lands on a
    physical value: pass twice the enthalpy, get about 50 %.
    """
    T = np.linspace(0, 250, 2500)
    hf = 0.5 + 3.0 * np.exp(-0.5 * ((T - 165) / 8) ** 2)
    ref = 2 * (3.0 * 8.0 * np.sqrt(2 * np.pi)) / (10.0 / 60.0)
    r = analyse_dsc(T, hf, heating_rate=10.0, ref_enthalpy_J_g=ref)
    assert r.crystallinity_pct == pytest.approx(50.0, rel=0.05)


def test_dsc_enthalpy_requires_a_heating_rate():
    T, hf = _dsc_with_tg_and_tm()
    r = analyse_dsc(T, hf)  # no rate
    assert r.delta_cp is None
    # The enthalpy is reported on the arbitrary area scale when no rate is
    # given, so it must not be presented as J/g; with no rate the field is
    # still computed but the caller is told the rate is missing by the
    # absence of delta_cp and crystallinity.
    assert r.crystallinity_pct is None


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


def test_tga_endpoint():
    T, m = _two_step_tga()
    r = client.post("/api/v1/thermal/tga", json={"temperature": T.tolist(), "mass_pct": m.tolist()})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["residue_pct"] == pytest.approx(10.0, abs=0.2)
    assert len(body["steps"]) == 2


def test_dsc_endpoint():
    T, hf = _dsc_with_tg_and_tm()
    r = client.post(
        "/api/v1/thermal/dsc",
        json={"temperature": T.tolist(), "heat_flow": hf.tolist(), "heating_rate": 10.0},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["Tg"] == pytest.approx(100.0, abs=3.0)
    assert body["Tm"] == pytest.approx(165.0, abs=1.0)


def test_tga_endpoint_rejects_mismatched_lengths():
    r = client.post("/api/v1/thermal/tga", json={"temperature": [1, 2, 3], "mass_pct": [1, 2]})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Amorphous traces and the sign of delta_cp.
#
# Both of these come from a real DSC scan of atactic polystyrene (pure PS,
# 8.45 mg, 10 K/min, 30-180 C), which is an amorphous polymer. It has a glass
# transition at ~100 C and no melting endotherm at all -- and that combination
# is what exposed the two bugs below.
# ---------------------------------------------------------------------------


def _amorphous_ps_like():
    """
    A trace with the shape of the real polystyrene scan: a glass transition,
    no melting peak, and a monotonic downward drift in the raw signal (the
    instrument's exothermic-up convention), scanned well past Tg.

    The key property is that there is *no* event that returns to the baseline.
    """
    T = np.linspace(30, 180, 300)
    step = -0.037 / (1 + np.exp(-(T - 100) / 5.0))
    drift = -0.133 - 0.0004 * (T - 30)
    return T, drift + step


def test_dsc_monotonic_amorphous_trace_has_no_melting_peak():
    """
    An amorphous polymer cannot melt, so a monotonic trace must report no Tm.

    This is the bug the real polystyrene scan exposed: the peak search took
    the residual against the end-to-end chord, which on a monotonic trace is
    positive over a large part of the range. The argmax landed on the shoulder
    of the glass transition and a "melting enthalpy" of 2.7 J/g was integrated
    from it. Nothing in that trace is a melting endotherm.
    """
    T, hf = _amorphous_ps_like()
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tm is None, f"reported a spurious melting peak at {r.Tm} C"
    assert r.delta_Hm is None, f"reported a spurious melting enthalpy {r.delta_Hm} J/g"


def test_dsc_a_real_melting_peak_is_still_found():
    """
    The guard that rejects a monotonic trace must not reject a genuine
    endotherm. A real melting peak is a transient excursion that returns to
    the baseline, unlike the amorphous false positive.
    """
    T = np.linspace(30, 220, 1900)
    hf = -0.10 + 0.02 / (1 + np.exp(-(T - 100) / 5.0)) + 1.5 * np.exp(
        -0.5 * ((T - 165) / 5.0) ** 2
    )
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tm == pytest.approx(165.0, abs=3.0)
    assert r.delta_Hm is not None and r.delta_Hm > 5.0


def test_dsc_delta_cp_is_positive_on_a_falling_step():
    """
    delta_cp is the heat-capacity change across a glass transition, so it is
    positive by definition -- it cannot depend on the instrument's sign
    convention. This trace steps *down* (exothermic-up instrument), which is
    exactly the case that used to report a negative value.

    A 0.5 W/g step at 20 K/min is 0.5/(20/60) = 1.5 J/(g.K).
    """
    T = np.linspace(0, 200, 2000)
    hf = 0.9 - 0.5 / (1 + np.exp(-(T - 100) / 3.0))
    r = analyse_dsc(T, hf, heating_rate=20.0)
    assert r.delta_cp is not None
    assert r.delta_cp > 0.0, f"delta_cp = {r.delta_cp} is negative, which is unphysical"
    assert r.delta_cp == pytest.approx(1.5, rel=0.15)


def test_dsc_delta_cp_ignores_baseline_drift_far_from_tg():
    """
    The step must be measured between the plateaus adjacent to the transition,
    not between the ends of the scan. Here a strong linear drift is added on
    top of the 0.5 W/g step: if the analyser averages the first and last 10 %
    of the scan instead, the drift is mistaken for part of the step and the
    value comes out far too large.
    """
    T = np.linspace(0, 400, 4000)
    step = 0.5 / (1 + np.exp(-(T - 200) / 4.0))
    drift = 0.0009 * (T - 200)
    r = analyse_dsc(T, drift + step, heating_rate=20.0)
    assert r.delta_cp == pytest.approx(1.5, rel=0.2)


# ---------------------------------------------------------------------------
# A semi-crystalline trace: Tg and a melting peak in the SAME scan.
#
# This is the ordinary case for a semicrystalline polymer, and it is where the
# Tg search was failing. The melting peak is the larger feature, so anything
# that ranks candidates by the size of the level change picks the melting flank
# over the glass transition.
#
# The trace below is PLLA-like: a Tg step at 75 C and a melting endotherm at
# 170 C, which is roughly the real separation (PLLA: Tg ~ 60-65 C, Tm ~ 170-180 C).
# ---------------------------------------------------------------------------


def _semicrystalline(tg=75.0, tm=170.0, step_h=0.08, peak_h=1.5):
    T = np.linspace(20, 220, 2000)
    hf = (
        -0.10
        + step_h / (1 + np.exp(-(T - tg) / 4.0))
        + peak_h * np.exp(-0.5 * ((T - tm) / 5.0) ** 2)
    )
    return T, hf


def test_dsc_tg_is_not_taken_from_the_melting_flank():
    """
    The glass transition must be reported at the step, not on the flank of the
    melting peak.

    The melting flank scores about 32x higher than the true Tg on the level-change
    test the search used, so the search landed at 185-192 C -- far above the
    real transition, and outside the scan region where a Tg could physically be
    for this polymer.
    """
    T, hf = _semicrystalline(tg=75.0, tm=170.0)
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tg is not None
    assert r.Tg == pytest.approx(75.0, abs=6.0), (
        f"Tg reported at {r.Tg} C, which is the melting flank, not the step at 75 C"
    )
    # And it must stay well clear of the melting peak.
    assert r.Tg < 140.0, "Tg must not be drawn from the melting region"


def test_dsc_tg_and_tm_are_both_found_on_a_semicrystalline_trace():
    """Both transitions are present and must both be reported, and distinct."""
    T, hf = _semicrystalline(tg=75.0, tm=170.0)
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tm == pytest.approx(170.0, abs=3.0)
    assert r.Tg == pytest.approx(75.0, abs=6.0)
    assert abs(r.Tm - r.Tg) > 60.0, "Tg collapsed onto the melting peak"


def test_dsc_tg_survives_when_the_melting_peak_dominates():
    """
    A large melting peak must not swallow a small glass transition. Here the
    peak is 40x the height of the step, which is realistic for a highly
    crystalline sample.
    """
    T, hf = _semicrystalline(tg=75.0, tm=170.0, step_h=0.05, peak_h=2.0)
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tg is not None
    assert r.Tg == pytest.approx(75.0, abs=8.0), f"Tg reported at {r.Tg} C"


def test_dsc_melting_enthalpy_is_not_inflated_by_the_glass_transition():
    """
    The melting enthalpy must be the area of the melting peak, not the peak
    plus the heat-capacity step underneath it.

    The baseline is fitted on points well away from the peak; on a trace whose
    Tg sits far below the melting peak, that baseline region includes the
    glass transition, so the step is counted as part of the melting enthalpy.
    The true area of the Gaussian below is A*sigma*sqrt(2*pi), truncated by the
    end of the scan.

    Measured: the analyser returned 121.5 J/g against a true 112.8 -- about
    7.7 % high, from the 0.08 W/g step being integrated along with the peak.
    """
    T, hf = _semicrystalline(tg=75.0, tm=170.0, step_h=0.08, peak_h=1.5)
    r = analyse_dsc(T, hf, heating_rate=10.0)

    # True peak area, integrated numerically over the full scan to account for
    # the truncation at 220 C.
    peak_only = 1.5 * np.exp(-0.5 * ((T - 170.0) / 5.0) ** 2)
    true_area = float(np.trapezoid(peak_only, T))
    true_hm = true_area / (10.0 / 60.0)
    assert r.delta_Hm is not None
    assert r.delta_Hm == pytest.approx(true_hm, rel=0.03), (
        f"delta_Hm = {r.delta_Hm:.2f} J/g against a true {true_hm:.2f}"
    )


def test_dsc_amorphous_trace_still_reports_no_melting_peak():
    """Regression guard: the semicrystalline fix must not resurrect bug 1."""
    T, hf = _amorphous_ps_like()
    r = analyse_dsc(T, hf, heating_rate=10.0)
    assert r.Tm is None
    assert r.delta_Hm is None

