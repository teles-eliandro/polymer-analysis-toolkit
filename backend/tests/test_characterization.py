"""
Mechanical, rheology and structure modules, against analytic references.

The rheology tests use a Maxwell model, whose crossover, terminal slopes and
relaxation time are known exactly, so the expected values come from the model
rather than from the implementation.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.core.mechanical import analyse_tensile
from app.core.rheology import analyse_rheology
from app.core.structure import (
    analyse_ftir,
    analyse_xrd,
    scherrer_crystallite_size,
)
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Mechanical
# ---------------------------------------------------------------------------


def _linear_elastic(E_MPa=2000.0, strain_end_pct=5.0, n=300):
    """
    A perfectly linear elastic curve. With strain in percent,
    sigma = E * (strain_pct / 100), so the slope per percent is E/100.
    """
    eps = np.linspace(0, strain_end_pct, n)
    sig = E_MPa * (eps / 100.0)
    return eps, sig


def test_modulus_recovers_the_constructed_value():
    """
    The 100x unit trap: a slope taken over a percent strain axis is in
    MPa/percent, a hundred times smaller than the modulus in MPa.
    """
    eps, sig = _linear_elastic(E_MPa=2000.0)
    r = analyse_tensile(eps, sig)
    assert r.E_MPa == pytest.approx(2000.0, rel=1e-3)


@pytest.mark.parametrize("E", [100.0, 500.0, 2400.0, 3500.0])
def test_modulus_is_correct_across_the_range_of_real_polymers(E):
    """Polyolefins near 100 MPa up to glassy polymers near 3500 MPa."""
    eps, sig = _linear_elastic(E_MPa=E)
    r = analyse_tensile(eps, sig)
    assert r.E_MPa == pytest.approx(E, rel=1e-3)


def test_max_stress_and_break_strain():
    eps, sig = _linear_elastic(E_MPa=2000.0, strain_end_pct=5.0)
    r = analyse_tensile(eps, sig)
    assert r.stress_max_MPa == pytest.approx(100.0, rel=1e-6)
    assert r.strain_break_pct == pytest.approx(5.0, rel=1e-6)


def test_toughness_matches_the_triangle_area():
    """
    A linear ramp to 100 MPa at 5 % strain encloses 0.5*100*5 = 250 MPa*%,
    which is 2.5 MJ/m^3.
    """
    eps, sig = _linear_elastic(E_MPa=2000.0, strain_end_pct=5.0)
    r = analyse_tensile(eps, sig)
    assert r.toughness_MJ_m3 == pytest.approx(2.5, rel=0.02)


def test_yield_point_is_detected():
    """A curve that peaks then drops before breaking shows a yield point."""
    eps = np.concatenate([np.linspace(0, 4, 120), np.linspace(4, 300, 240)])
    sig = np.concatenate([np.linspace(0, 60, 120), np.linspace(60, 50, 240)])
    r = analyse_tensile(eps, sig)
    assert r.yielded is True
    assert r.stress_yield_MPa == pytest.approx(60.0, abs=0.5)
    assert r.strain_yield_pct == pytest.approx(4.0, abs=0.1)


def test_brittle_curve_has_no_yield():
    eps, sig = _linear_elastic()
    r = analyse_tensile(eps, sig)
    assert r.yielded is False
    assert r.brittle is True


def test_modulus_window_is_reported():
    """The strain window used for the regression must be visible."""
    eps, sig = _linear_elastic()
    r = analyse_tensile(eps, sig)
    assert r.modulus_window is not None
    lo, hi = r.modulus_window
    assert 0 <= lo < hi <= 5.0


def test_explicit_modulus_window_is_honoured():
    eps, sig = _linear_elastic(E_MPa=2000.0)
    r = analyse_tensile(eps, sig, modulus_window=(0.5, 2.0))
    assert r.modulus_window == (0.5, 2.0)
    assert r.E_MPa == pytest.approx(2000.0, rel=1e-3)


def test_negative_stress_is_rejected():
    with pytest.raises(ValueError, match="non-negative"):
        analyse_tensile([0, 1, 2, 3], [0, -1, 2, 3])


# ---------------------------------------------------------------------------
# Rheology: Maxwell model with known analytic properties
# ---------------------------------------------------------------------------


def _maxwell(G0=1.0e6, tau=0.01, n=80, w_lo=1e-1, w_hi=1e4):
    """
    G'  = G0 (w tau)^2 / (1 + (w tau)^2)
    G'' = G0 (w tau)   / (1 + (w tau)^2)

    The exact crossover is at w tau = 1, i.e. w = 1/tau, where both moduli
    equal G0/2.
    """
    w = np.logspace(np.log10(w_lo), np.log10(w_hi), n)
    x = w * tau
    Gp = G0 * x**2 / (1 + x**2)
    Gpp = G0 * x / (1 + x**2)
    return w, Gp, Gpp


def test_crossover_frequency_matches_1_over_tau():
    tau = 0.01
    w, Gp, Gpp = _maxwell(tau=tau)
    r = analyse_rheology(w, Gp, Gpp)
    assert r.cross_over_freq == pytest.approx(1.0 / tau, rel=0.02)


def test_crossover_modulus_is_half_the_plateau():
    G0 = 1.0e6
    w, Gp, Gpp = _maxwell(G0=G0)
    r = analyse_rheology(w, Gp, Gpp)
    assert r.cross_over_modulus == pytest.approx(G0 / 2, rel=0.02)


def test_relaxation_time_is_the_inverse_of_the_crossover():
    tau = 0.01
    w, Gp, Gpp = _maxwell(tau=tau)
    r = analyse_rheology(w, Gp, Gpp)
    assert r.relaxation_time_s == pytest.approx(tau, rel=0.02)


def test_terminal_slopes_match_maxwell_theory():
    """
    In the terminal zone a Maxwell fluid gives log-log slopes of exactly 2
    for G' and 1 for G''. These are a diagnostic of whether a measurement
    reached the terminal regime at all.
    """
    w, Gp, Gpp = _maxwell()
    r = analyse_rheology(w, Gp, Gpp)
    assert r.terminal_slope_Gprime == pytest.approx(2.0, abs=0.05)
    assert r.terminal_slope_Gpp == pytest.approx(1.0, abs=0.05)


def test_gel_like_sample_is_flagged_solid_at_low_frequency():
    """
    A crosslinked network has G' > G'' across the whole window. There is no
    crossover, and the flag must say so rather than inventing one.
    """
    w = np.logspace(-1, 3, 50)
    Gp = np.full_like(w, 1e5)
    Gpp = np.full_like(w, 1e4)
    r = analyse_rheology(w, Gp, Gpp)
    assert r.solid_like_at_low_freq is True
    assert r.cross_over_freq is None


def test_frequency_independent_tan_delta_flags_a_gel_point():
    """
    The Winter-Chambon criterion: at the gel point G' and G'' share a power
    law, so tan(delta) is independent of frequency.
    """
    w = np.logspace(-2, 2, 60)
    n_exp = 0.5
    Gp = 1e4 * w**n_exp
    Gpp = 1e4 * w**n_exp  # identical exponents -> tan(delta) = 1 everywhere
    r = analyse_rheology(w, Gp, Gpp)
    assert r.gel_point_detected is True
    assert r.tan_delta_spread == pytest.approx(0.0, abs=1e-6)


def test_liquid_sample_is_not_flagged_as_a_gel():
    w, Gp, Gpp = _maxwell()
    r = analyse_rheology(w, Gp, Gpp)
    assert r.gel_point_detected is False


def test_rheology_rejects_non_positive_moduli():
    w = np.logspace(0, 3, 10)
    with pytest.raises(ValueError, match="strictly positive"):
        analyse_rheology(w, np.zeros_like(w), np.ones_like(w))


# ---------------------------------------------------------------------------
# Structure: Scherrer
# ---------------------------------------------------------------------------


def test_scherrer_matches_a_hand_calculation():
    """
    D = K lambda / (beta cos theta), with beta in radians.
    2-theta = 20 deg, FWHM = 1 deg, Cu K-alpha1.
    """
    K, lam, fwhm, tt = 0.9, 1.5406, 1.0, 20.0
    beta = math.radians(fwhm)
    theta = math.radians(tt / 2.0)
    expected_nm = K * lam / (beta * math.cos(theta)) / 10.0
    assert scherrer_crystallite_size(tt, fwhm, lam, K) == pytest.approx(
        expected_nm, rel=1e-12
    )


def test_narrower_peak_gives_a_larger_crystallite():
    """The defining inverse relationship of the Scherrer equation."""
    broad = scherrer_crystallite_size(20.0, 2.0)
    narrow = scherrer_crystallite_size(20.0, 0.2)
    assert narrow > broad


def test_instrumental_broadening_increases_the_reported_size():
    """
    Subtracting the instrumental contribution narrows the peak, which
    increases D. Ignoring it therefore always under-reports the size.
    """
    without = scherrer_crystallite_size(20.0, 1.0, instrumental_fwhm_deg=0.0)
    with_correction = scherrer_crystallite_size(20.0, 1.0, instrumental_fwhm_deg=0.2)
    assert with_correction > without
    assert with_correction is not None and without is not None


def test_instrumental_broadening_larger_than_the_peak_returns_none():
    """A peak narrower than the instrument resolution cannot be sized."""
    assert scherrer_crystallite_size(20.0, 0.1, instrumental_fwhm_deg=1.0) is None


@pytest.mark.parametrize("bad", [0.0, -5.0, 200.0])
def test_scherrer_rejects_invalid_angles(bad):
    with pytest.raises(ValueError):
        scherrer_crystallite_size(bad, 1.0)


def test_scherrer_rejects_non_positive_fwhm():
    with pytest.raises(ValueError, match="positive"):
        scherrer_crystallite_size(20.0, 0.0)


def test_xrd_indexes_a_synthetic_pattern():
    """
    Two Gaussian peaks on a flat background, positions known.

    Peaks are returned in ascending 2-theta order, which is the order a
    diffraction pattern is read in, not in intensity order.
    """
    tt = np.linspace(5, 60, 1200)
    y = 100 + 900 * np.exp(-0.5 * ((tt - 18.0) / 0.25) ** 2) + 400 * np.exp(
        -0.5 * ((tt - 24.0) / 0.3) ** 2
    )
    r = analyse_xrd(tt, y)
    assert len(r.peaks_two_theta) >= 2
    assert r.peaks_two_theta[0] == pytest.approx(18.0, abs=0.3)
    assert r.peaks_two_theta[1] == pytest.approx(24.0, abs=0.3)
    # Peaks must be ordered by angle.
    assert r.peaks_two_theta == sorted(r.peaks_two_theta)
    # d-spacing for 2-theta = 18 deg with Cu K-alpha1:
    # d = lambda / (2 sin theta) = 1.5406 / (2 sin 9 deg)
    # The detected peak sits at 17.98 deg rather than exactly 18.00, because
    # the synthetic grid steps by about 0.046 deg. That 0.02 deg offset moves
    # d by 0.11 %, so the tolerance must accommodate the grid resolution
    # rather than the arithmetic alone.
    d_expected = 1.5406 / (2 * math.sin(math.radians(9.0)))
    assert r.d_spacing_angstrom[0] == pytest.approx(d_expected, rel=2e-3)


def test_xrd_d_spacing_decreases_as_angle_increases():
    """Bragg's law: larger 2-theta means smaller d."""
    tt = np.linspace(5, 60, 1200)
    y = (
        100
        + 900 * np.exp(-0.5 * ((tt - 18.0) / 0.25) ** 2)
        + 400 * np.exp(-0.5 * ((tt - 24.0) / 0.3) ** 2)
    )
    r = analyse_xrd(tt, y)
    assert r.d_spacing_angstrom[0] > r.d_spacing_angstrom[1]


def test_xrd_crystallite_size_is_reported_per_peak():
    tt = np.linspace(5, 60, 1200)
    y = 100 + 900 * np.exp(-0.5 * ((tt - 18.0) / 0.25) ** 2)
    r = analyse_xrd(tt, y)
    assert len(r.crystallite_size_nm) == len(r.peaks_two_theta)
    assert all(s is None or s > 0 for s in r.crystallite_size_nm)


def test_xrd_rejects_negative_intensity():
    with pytest.raises(ValueError, match="non-negative"):
        analyse_xrd(np.linspace(5, 60, 20), np.full(20, -1.0))


# ---------------------------------------------------------------------------
# Structure: FTIR
# ---------------------------------------------------------------------------


def _polyethylene_like_spectrum():
    """
    A synthetic alkane-rich spectrum: CH2 asymmetric and symmetric stretches
    near 2920 and 2850, the CH2 scissor near 1465 and the rocking band near
    720. Wavenumbers run high to low, as an IR spectrum is conventionally
    plotted.
    """
    wn = np.linspace(4000, 400, 3600)
    a = np.full_like(wn, 0.02)
    for centre, height, width in [
        (2920, 0.80, 18),
        (2850, 0.60, 18),
        (1465, 0.45, 12),
        (720, 0.35, 10),
    ]:
        a += height * np.exp(-0.5 * ((wn - centre) / width) ** 2)
    return wn, a


def test_ftir_finds_all_four_bands():
    wn, a = _polyethylene_like_spectrum()
    r = analyse_ftir(wn, a)
    assert len(r.detected_peaks) >= 4


def test_ftir_handles_a_descending_wavenumber_axis():
    """
    Regression test: peak detection assumed an ascending axis, so a spectrum
    plotted the conventional way (wavenumber decreasing) lost all but one
    band.
    """
    wn, a = _polyethylene_like_spectrum()
    r_desc = analyse_ftir(wn, a)
    r_asc = analyse_ftir(wn[::-1], a[::-1])
    assert len(r_desc.detected_peaks) == len(r_asc.detected_peaks)
    assert sorted(round(p, 1) for p in r_desc.detected_peaks) == sorted(
        round(p, 1) for p in r_asc.detected_peaks
    )


def test_ftir_reports_every_candidate_assignment():
    """
    At a band where two reference windows overlap the response must carry both
    candidates. Choosing one silently would imply a certainty the method does
    not have.
    """
    wn = np.linspace(4000, 400, 3600)
    a = np.full_like(wn, 0.02) + 0.8 * np.exp(-0.5 * ((wn - 1715) / 10) ** 2)
    r = analyse_ftir(wn, a)
    assert r.matches, "no match at 1715 cm^-1"
    first = r.matches[0]
    assert len(first["candidates"]) >= 2, "overlapping bands were collapsed"


def test_ftir_alkane_bands_are_assigned_as_CH():
    wn, a = _polyethylene_like_spectrum()
    r = analyse_ftir(wn, a)
    stretch = [m for m in r.matches if 2900 <= m["observed_cm1"] <= 2930]
    assert stretch, "the 2920 cm^-1 band was not detected"
    names = " ".join(c["assignment"] for c in stretch[0]["candidates"])
    assert "C-H" in names


def test_ftir_nitrile_band_is_recognised():
    wn = np.linspace(4000, 400, 3600)
    a = np.full_like(wn, 0.01) + 0.6 * np.exp(-0.5 * ((wn - 2245) / 8) ** 2)
    r = analyse_ftir(wn, a)
    names = " ".join(
        c["assignment"] for m in r.matches for c in m["candidates"]
    )
    assert "nitrile" in names.lower()


def test_ftir_rejects_negative_absorbance():
    wn = np.linspace(4000, 400, 100)
    with pytest.raises(ValueError, match="non-negative"):
        analyse_ftir(wn, np.full(100, -0.5))


def test_ftir_carries_its_disclaimer():
    wn, a = _polyethylene_like_spectrum()
    r = analyse_ftir(wn, a)
    assert "does not" in r.note.lower() or "indicative" in r.note.lower()


# ---------------------------------------------------------------------------
# HTTP surface
# ---------------------------------------------------------------------------


def test_tensile_endpoint():
    eps, sig = _linear_elastic(E_MPa=2000.0)
    r = client.post(
        "/api/v1/mechanical/tensile",
        json={"strain_pct": eps.tolist(), "stress_MPa": sig.tolist()},
    )
    assert r.status_code == 200, r.text
    assert r.json()["E_MPa"] == pytest.approx(2000.0, rel=1e-3)


def test_rheology_endpoint():
    w, Gp, Gpp = _maxwell()
    r = client.post(
        "/api/v1/rheology/sweep",
        json={"omega": w.tolist(), "G_prime": Gp.tolist(), "G_double_prime": Gpp.tolist()},
    )
    assert r.status_code == 200, r.text
    assert r.json()["cross_over_freq"] == pytest.approx(100.0, rel=0.02)


def test_xrd_endpoint():
    tt = np.linspace(5, 60, 600)
    y = 100 + 900 * np.exp(-0.5 * ((tt - 18.0) / 0.25) ** 2)
    r = client.post("/api/v1/structure/xrd", json={"two_theta": tt.tolist(), "intensity": y.tolist()})
    assert r.status_code == 200, r.text
    assert len(r.json()["peaks_two_theta"]) >= 1


def test_ftir_endpoint():
    wn, a = _polyethylene_like_spectrum()
    r = client.post("/api/v1/structure/ftir", json={"wavenumber": wn.tolist(), "absorbance": a.tolist()})
    assert r.status_code == 200, r.text
    assert len(r.json()["matches"]) >= 3


# ---------------------------------------------------------------------------
# Regression: non-finite values must never reach the response
# ---------------------------------------------------------------------------
#
# Real WAXS/SEC exports (Nika + Fit2D, DIFFRAC) carry many narrow spikes whose
# width is below the sampling interval. Those peaks have no measurable FWHM, and
# the first implementation wrote float("nan") into fwhm_deg while leaving the
# crystallite size as None - breaking the parallel arrays and, because NaN is
# not valid JSON, making Starlette raise on serialisation. Every synthetic test
# passed because synthetic peaks are always wide enough to measure.
#
# This reproduces the failure mode from the real trace that exposed it
# (Zenodo 10.5281/zenodo.20466241, WAXS of a PLA/PE film, lambda = 1.541 A).


def _instrument_like_trace():
    """A real WAXS trace segment where peaks have no measurable FWHM.

    Taken from Zenodo 10.5281/zenodo.20466241 (WAXS of a PLA/PE film, lambda =
    1.541 A), 2theta 23.58-32.58 deg, 110 points at the export's own 0.08 deg
    spacing. In this region the background is rising steeply and the local
    maxima are sub-sampling ripples whose shoulders never cross half maximum
    within the search window, so _fwhm_at returns None for nine of them.

    This is the fixture that actually reproduces the bug: a synthetic Gaussian
    on a flat background does not, which is why the original suite missed it.
    Recorded rather than regenerated so the regression cannot silently drift.
    """
    tt = np.array([
        23.5803, 23.6621, 23.7439, 23.8257, 23.9075, 23.9894, 24.0712, 24.1531,
        24.2349, 24.3168, 24.3987, 24.4806, 24.5625, 24.6444, 24.7264, 24.8083,
        24.8903, 24.9723, 25.0543, 25.1363, 25.2183, 25.3003, 25.3824, 25.4645,
        25.5465, 25.6286, 25.7107, 25.7928, 25.875, 25.9571, 26.0393, 26.1214,
        26.2036, 26.2858, 26.368, 26.4502, 26.5325, 26.6147, 26.697, 26.7793,
        26.8615, 26.9439, 27.0262, 27.1085, 27.1909, 27.2732, 27.3556, 27.438,
        27.5204, 27.6028, 27.6853, 27.7677, 27.8502, 27.9327, 28.0152, 28.0977,
        28.1802, 28.2627, 28.3453, 28.4278, 28.5104, 28.593, 28.6756, 28.7583,
        28.8409, 28.9236, 29.0063, 29.0889, 29.1717, 29.2544, 29.3371, 29.4199,
        29.5026, 29.5854, 29.6682, 29.751, 29.8339, 29.9167, 29.9996, 30.0825,
        30.1654, 30.2483, 30.3312, 30.4142, 30.4971, 30.5801, 30.6631, 30.7461,
        30.8291, 30.9122, 30.9952, 31.0783, 31.1614, 31.2445, 31.3276, 31.4108,
        31.4939, 31.5771, 31.6603, 31.7435, 31.8268, 31.91, 31.9933, 32.0766,
        32.1599, 32.2432, 32.3265, 32.4099, 32.4932, 32.5766,
    ])
    y = np.array([
        345.557, 344.061, 343.663, 343.032, 341.231, 340.493, 340.18, 338.512,
        338.003, 336.964, 336.159, 335.246, 333.351, 332.858, 330.945, 329.449,
        328.384, 327.711, 327.935, 326.099, 324.981, 323.974, 322.16, 321.033,
        320.401, 318.513, 318.103, 317.549, 315.863, 314.437, 313.617, 312.613,
        311.483, 311.961, 312.11, 312.788, 313.185, 313.965, 314.86, 313.879,
        313.053, 311.851, 309.627, 307.306, 304.392, 300.948, 298.457, 297.185,
        295.497, 294.169, 293.739, 291.838, 292.474, 290.728, 289.971, 288.698,
        288.813, 288.288, 287.492, 287.217, 285.932, 285.746, 285.386, 283.962,
        282.847, 282.059, 281.418, 281.1, 281.444, 281.056, 280.478, 280.11,
        279.981, 279.949, 280.779, 281.517, 281.898, 282.252, 283.926, 283.356,
        283.367, 282.522, 281.59, 280.332, 278.397, 275.53, 271.582, 268.462,
        263.182, 258.536, 253.342, 252.357, 249.753, 243.164, 234.278, 230.578,
        234.278, 230.578, 227.112, 226.042, 228.951, 227.919, 229.134, 236.842,
        251.361, 272.108, 297.189, 328.593, 356.831, 372.999,
    ])
    return tt, y[: tt.size]


def test_xrd_never_returns_non_finite_values():
    """Every reported value must be finite, and the arrays must stay parallel."""
    tt, y = _instrument_like_trace()
    r = analyse_xrd(tt.tolist(), y.tolist(), wavelength_angstrom=1.541)

    for name in ("peaks_two_theta", "d_spacing_angstrom", "crystallite_size_nm", "fwhm_deg"):
        values = getattr(r, name)
        assert all(math.isfinite(v) for v in values), f"{name} contains a non-finite value"

    n = len(r.peaks_two_theta)
    assert len(r.d_spacing_angstrom) == n
    assert len(r.crystallite_size_nm) == n
    assert len(r.fwhm_deg) == n


def test_xrd_endpoint_serialises_an_instrument_like_trace():
    """
    The endpoint must answer 200, and the body must survive allow_nan=False.

    Before the fix this returned a 500: unmeasurable peaks were written as
    NaN, and NaN is not valid JSON, so Starlette's serialiser raised. The
    assert on json.dumps reproduces that serialiser's contract exactly.
    """
    tt, y = _instrument_like_trace()
    r = client.post(
        "/api/v1/structure/xrd",
        json={"two_theta": tt.tolist(), "intensity": y.tolist(), "wavelength_angstrom": 1.541},
    )
    assert r.status_code == 200, r.text
    json.dumps(r.json(), allow_nan=False)


def test_unmeasurable_peaks_are_dropped_not_reported_as_nan():
    """
    A trace whose peaks cannot be measured yields fewer, valid peaks.

    Nine local maxima in the fixture have no half-maximum crossing. They must
    disappear from the result rather than appear with a NaN width.
    """
    tt, y = _instrument_like_trace()
    r = analyse_xrd(tt.tolist(), y.tolist(), wavelength_angstrom=1.541)
    assert r.fwhm_deg and all(f > 0 for f in r.fwhm_deg), r.fwhm_deg
    assert r.crystallite_size_nm and all(s > 0 for s in r.crystallite_size_nm), r.crystallite_size_nm


def test_crystallinity_index_is_not_reported_when_it_saturates():
    """
    A monotonically decaying pattern must not report 100 % crystallinity.

    The crystallinity index divides peak area by total area. On a pattern whose
    amorphous halo decays steeply (a q-space profile in arbitrary units), the
    straight-line baseline sits under every point, so the whole trace counts as
    crystalline and the index saturates. Observed on the real WAXS films in
    Zenodo 10.5281/zenodo.20466241, where every sample returned 100 %. A
    saturated index measures nothing - it means the amorphous reference is
    absent - so None is the honest answer.
    """
    tt = np.linspace(5.0, 45.0, 400)
    # Steep monotonic decay, as in the real q-space profiles, with a small peak.
    y = 900.0 * np.exp(-0.03 * (tt - 5.0)) + 40.0 * np.exp(-0.5 * ((tt - 21.0) / 0.3) ** 2)
    r = analyse_xrd(tt.tolist(), y.tolist(), wavelength_angstrom=1.541)
    assert r.crystallinity_pct is None, r.crystallinity_pct
    # The peak itself must still be found and indexed.
    assert any(20.0 <= p <= 22.0 for p in r.peaks_two_theta), r.peaks_two_theta


def test_crystallinity_index_still_reported_on_a_flat_baseline():
    """A normal pattern with a flat baseline keeps a meaningful index."""
    tt = np.linspace(5.0, 45.0, 400)
    y = 100.0 + 900.0 * np.exp(-0.5 * ((tt - 21.0) / 0.35) ** 2)
    r = analyse_xrd(tt.tolist(), y.tolist(), wavelength_angstrom=1.541)
    assert r.crystallinity_pct is not None
    assert 0.0 < r.crystallinity_pct <= 100.0
