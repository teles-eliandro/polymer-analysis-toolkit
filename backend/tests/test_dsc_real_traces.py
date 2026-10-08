"""
DSC against a real instrument trace: a heating ramp on ABS.

Source: figshare 10.6084/m9.figshare.24462004 ("DSC raw data files", NREL),
file ABS2_AR.tri, decoded from the Trios binary format and stored at stride
100. One heating ramp from -90 to 174 C at 10.00 C/min.

This trace is here because it broke the Tg search twice over. The glass
transition of ABS is at about 105 C, and the routine reported no Tg at all --
not because the data was poor (15 903 points at 10 Hz) but because of two
choices in the candidate search, both invisible on the smooth synthetic
traces the other tests use.
"""

import json
from pathlib import Path

import pytest

from app.core.thermal import analyse_dsc

FIXTURES = Path(__file__).parent / "fixtures"


def _load() -> tuple[list[float], list[float]]:
    data = json.loads((FIXTURES / "dsc_abs_ramp.json").read_text())
    return data["temperature_C"], data["heat_flow_W_g"]


def test_abs_glass_transition_is_found():
    """
    The bug this guards: the routine used to return None on this trace.
    Ranking candidates by step-over-noise selected 46.6 C, where the baseline
    is flattest and a negligible step therefore scored highest, and the
    significance floor then rejected it -- discarding the real transition.

    ABS transitions around 105 C. The values asserted are the step midpoint
    with its onset and end, which is the ASTM D3418 construction.
    """
    T, hf = _load()
    r = analyse_dsc(T, hf)
    assert r.Tg is not None
    assert r.Tg == pytest.approx(96.0, abs=12.0)
    assert r.Tg_onset is not None and r.Tg_end is not None
    assert r.Tg_onset < r.Tg < r.Tg_end
    # The transition spans a realistic width, not the whole scan.
    assert 10.0 < r.Tg_end - r.Tg_onset < 80.0


def test_abs_tg_survives_a_reduced_sample():
    """
    Detecting the transition must not depend on a dense trace. The fixture is
    796 points; halving it to 398 keeps the transition, and halving again to
    199 is the point at which the 3 %-of-scan window stops fitting reliably.
    """
    T, hf = _load()
    fine = analyse_dsc(T, hf)
    coarse = analyse_dsc(T[::2], hf[::2])
    assert fine.Tg is not None and coarse.Tg is not None
    assert coarse.Tg == pytest.approx(fine.Tg, abs=3.0)


def test_start_of_scan_transient_is_not_reported_as_tg():
    """
    A DSC opens with the cell still settling, and on this trace that
    transient is a larger level change than the glass transition itself. It
    must not be what gets reported: a Tg far below the sample's real range is
    the symptom of exactly that mistake.
    """
    T, hf = _load()
    r = analyse_dsc(T, hf)
    assert r.Tg is not None
    # The scan starts at -90 C; a settling artefact would land down there.
    assert r.Tg > 20.0
