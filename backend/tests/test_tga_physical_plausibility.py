"""A TGA must tell the analyst when the trace is not physically possible.

The figshare 24595695 TGA-FTIR set ships seven of 27 files ending at a
*negative* mass (-0.35 % to -1.41 %). The raw CSV really does contain those
values; the reader is faithful and the analysis passes them through. The
failure is that nothing said so -- "residue = -1.4 %" reads like a
measurement, and was accepted as one here until the values were checked
against the file.

The number is deliberately NOT clamped: it is what the instrument wrote, and
zeroing it would hide a balance fault the analyst needs to see. What must
change is that the result says, in words, that a residue cannot be negative.
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, "/home/hermes/projects/polymer-analysis-toolkit/backend")
from app.core.thermal import analyse_tga


def _trace(end_pct: float = -1.41, start_pct: float = 100.0, n: int = 2000):
    """A single-stage decomposition ending at *end_pct* mass."""
    T = np.linspace(30.0, 700.0, n)
    m = np.where(
        T < 350.0,
        start_pct,
        start_pct + (end_pct - start_pct) * (T - 350.0) / 350.0,
    )
    m = np.clip(m, min(end_pct, start_pct), max(end_pct, start_pct))
    return T, m


def test_negative_residue_is_flagged():
    """A trace ending below zero must carry a warning, not a quiet number."""
    T, m = _trace(end_pct=-1.41)
    res = analyse_tga(T, m)

    assert res.residue_pct < 0.0, "the raw value must survive unchanged"
    joined = " ".join(res.notes).lower()
    assert "negative" in joined, (
        f"a negative residue must be flagged in words; notes were {res.notes!r}"
    )


def test_residue_is_not_silently_clamped_to_zero():
    """Flagging must not turn into clamping -- the instrument's value stays.

    The fixture's own smoothing shifts the endpoint slightly (a synthetic
    ramp is not what the instrument wrote), so the assertion is on the sign
    and rough magnitude, which is what "not clamped" means. Clamping would
    give exactly 0.0.
    """
    T, m = _trace(end_pct=-1.41)
    res = analyse_tga(T, m)
    assert res.residue_pct < -0.5, (
        "the reader must not rewrite the instrument's number into a plausible "
        f"one; got {res.residue_pct}"
    )


def test_healthy_trace_is_not_flagged():
    """A trace that ends near zero must stay quiet -- no false alarm."""
    T, m = _trace(end_pct=0.04)
    res = analyse_tga(T, m)
    joined = " ".join(res.notes).lower()
    assert "negative" not in joined, (
        f"a physically sound trace must not be flagged; notes were {res.notes!r}"
    )


def test_high_residue_is_flagged():
    """A residue above the starting mass is also not a measurement."""
    T, m = _trace(end_pct=108.0)
    res = analyse_tga(T, m)
    joined = " ".join(res.notes).lower()
    assert "above the starting" in joined or "unquantified" in joined, (
        f"an impossible high residue must be flagged; notes were {res.notes!r}"
    )
