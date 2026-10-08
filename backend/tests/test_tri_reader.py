"""
Tests for the TA Instruments Trios ``.tri`` reader.

The format is proprietary and undocumented; the layout was recovered from the
raw files themselves (figshare 10.6084/m9.figshare.24462004, 59 DSC runs of 20
polymers). These tests pin the properties that were actually verified against
the instrument's own metadata, so a regression in the byte layout is caught
here rather than producing silently wrong curves downstream.

The files are large (10-33 MB each) and are not committed. A trimmed fixture
carrying the head of one real file plus its decoded expectations is used
instead; the full-file checks are skipped when the dataset is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.io.tri_reader import read_tri

FIXTURES = Path(__file__).parent / "fixtures"
#: Trimmed real file: the first ABS run of figshare 24462004.
TRI_FIXTURE = FIXTURES / "tri_abs3_ar_head.bin"
TRI_EXPECT = FIXTURES / "tri_abs3_ar_expect.json"


def _have_fixture() -> bool:
    return TRI_FIXTURE.exists() and TRI_EXPECT.exists()


@pytest.mark.skipif(not _have_fixture(), reason="tri fixture not present")
def test_metadata_matches_the_instrument_record():
    """Sample name, mass and procedure come out of the metadata block."""
    expect = json.loads(TRI_EXPECT.read_text())
    tri = read_tri(str(TRI_FIXTURE))
    assert tri.sample_name == expect["sample_name"]
    assert tri.sample_mass_mg == pytest.approx(expect["mass_mg"])
    assert "Ramp 10.00" in (tri.procedure or "")


@pytest.mark.skipif(not _have_fixture(), reason="tri fixture not present")
def test_signal_names_are_clean():
    """
    Signal names are stored length-prefixed, so a naive split leaves a control
    byte glued to the first name ("\\x01Time"). That byte made name lookups
    fail on the real dataset, so it is worth a test of its own.
    """
    tri = read_tri(str(TRI_FIXTURE))
    assert tri.signal_names[0] == "Time"
    assert all(not n[0].isspace() and ord(n[0]) >= 32 for n in tri.signal_names)


@pytest.mark.skipif(not _have_fixture(), reason="tri fixture not present")
def test_channels_decode_to_physically_consistent_curves():
    """
    The recovered channels must be the real signals: temperature in the range
    the method programmed, heat flow in mW of the right magnitude, and one
    channel per declared signal.
    """
    expect = json.loads(TRI_EXPECT.read_text())
    tri = read_tri(str(TRI_FIXTURE))
    assert len(tri.channels) == expect["n_channels"]
    assert tri.sample_count == expect["n_samples"]

    t = tri.temperature
    assert t is not None
    assert min(t) == pytest.approx(expect["t_min"], abs=0.5)
    assert max(t) == pytest.approx(expect["t_max"], abs=0.5)

    hf = tri.heat_flow
    assert hf is not None
    assert abs(min(hf)) < 1.0, "heat flow should be milliwatts, not raw counts"


@pytest.mark.skipif(not _have_fixture(), reason="tri fixture not present")
def test_ramp_rate_recovered_from_the_trace():
    """
    The method says 10.00 C/min. The decoded trace must reproduce that rate,
    which is the end-to-end check that the time and temperature channels are
    both correct and correctly paired.
    """
    tri = read_tri(str(TRI_FIXTURE))
    temp = tri.temperature
    clock = tri.channel("Time")
    assert temp is not None and clock is not None
    tvals, secs = temp, clock.values
    # Use the rising portion of the heating ramp.
    span = max(tvals) - min(tvals)
    lo, hi = min(tvals) + 0.2 * span, min(tvals) + 0.8 * span
    idx = [i for i, v in enumerate(tvals) if lo <= v <= hi]
    minutes = (secs[idx[-1]] - secs[idx[0]]) / 60.0
    rate = (tvals[idx[-1]] - tvals[idx[0]]) / minutes
    assert rate == pytest.approx(10.0, rel=0.05)
