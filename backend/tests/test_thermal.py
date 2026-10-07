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
    assert losses[0] == pytest.approx(29.5, abs=1.5)
    assert losses[1] == pytest.approx(59.6, abs=1.5)


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
