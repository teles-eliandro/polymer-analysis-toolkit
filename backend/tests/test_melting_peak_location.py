"""
The melting peak must not be located on the end of the programmed ramp.

The bug this guards
-------------------
``_find_peak_temperature`` localised the melting peak with ``argmax(y - chord)``,
where ``chord`` joins the first and last sample of the scan. On the figshare
24462004 traces the heat flow at the start of the ramp is the *global maximum*
of the series (the sample is coldest there, under the exothermic-up convention
the instrument stores), so the curve lies entirely below the chord and the
residual has no positive value anywhere. ``argmax`` over an array whose maximum
is 0.0 returns index 0 by construction, and the "melting temperature" came back
as the first sample of the ramp:

    PLA1-AR   Tm = -90.0597   (the start of the ramp)
    EVA2-AR   Tm = -90.0590
    PET2-AR   Tm = -0.0589
    PE-NEW-AR Tm =  159.43    (the last sample -- the other degenerate end)

Because the melting window is what the glass-transition search then excludes, a
wrong Tm poisoned the Tg as well: the reported reliability confidence never once
fired across the 116 real traces.

The fixture is real data, not a synthetic imitation, because the failure depends
on the exact shape of the stored trace (start-of-scan maximum and a melt dip
small enough to stay under the chord) and a Gaussian imitation does not
reproduce it.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.core.thermal import analyse_dsc

FIXTURES = Path(__file__).parent / "fixtures"
PLA = FIXTURES / "dsc_pla_ramp.json"


def _load_pla() -> tuple[np.ndarray, np.ndarray]:
    data = json.loads(PLA.read_text())
    return (
        np.asarray(data["temperature_C"], dtype=float),
        np.asarray(data["heat_flow_W_g"], dtype=float),
    )


@pytest.mark.skipif(not PLA.exists(), reason="PLA fixture not present")
def test_pla_melting_temperature_is_not_the_start_of_the_ramp():
    """
    PLA1-AR.tri melts near 150 C, and the stored method ramps -90 to 180 C.

    The old code reported -90.06 -- the first sample of the ramp -- because the
    chord residual had no positive value. Anything at or below the start of the
    scan is that failure, not a measurement.
    """
    T, hf = _load_pla()
    r = analyse_dsc(T.tolist(), hf.tolist(), heating_rate=10.0)

    assert r.Tm is not None, "PLA has a clear melting endotherm; it must be found"
    assert 120.0 < r.Tm < 190.0, (
        f"PLA Tm={r.Tm} is outside the published range. A value near -90 means "
        "the start of the ramp was reported as melting."
    )
    assert r.Tm != pytest.approx(float(T[0]), abs=1.0)
    assert r.Tm != pytest.approx(float(T[-1]), abs=1.0)


@pytest.mark.skipif(not PLA.exists(), reason="PLA fixture not present")
def test_pla_melting_temperature_lands_on_the_endotherm():
    """
    The endotherm is where it is, and the fixture says so: the minimum of the
    stored heat flow sits at 151.2 C, which is the melting peak under the
    exothermic-up convention the instrument uses.
    """
    T, hf = _load_pla()
    dip_T = float(T[int(np.argmin(hf))])
    r = analyse_dsc(T.tolist(), hf.tolist(), heating_rate=10.0)

    assert r.Tm is not None
    # The stored minimum IS the melting peak of this trace; the reported Tm
    # must be near it, not merely "some plausible number".
    assert abs(r.Tm - dip_T) < 12.0, (
        f"reported Tm={r.Tm} but the endotherm in this trace is at {dip_T} C"
    )


def test_amorphous_trace_reports_no_melting_peak():
    """
    A glass transition with no crystallinity must not produce a Tm at all.

    The chord residual is positive over most of a step, so ``argmax`` always had
    a winner and a "melting temperature" was invented for a sample that cannot
    melt. This uses a synthetic step because the point is the *absence* of any
    endotherm, which is a shape the generator controls exactly.
    """
    T = np.linspace(30.0, 180.0, 3000)
    step = -0.35 / (1.0 + np.exp(-(T - 105.0) / 2.5))
    hf = 0.02 + 1e-4 * T + step

    r = analyse_dsc(T, hf, heating_rate=10.0)

    assert r.Tm is None, (
        f"an amorphous trace produced Tm={r.Tm}; there is no melting endotherm "
        "in this signal, so any value is fabricated"
    )
