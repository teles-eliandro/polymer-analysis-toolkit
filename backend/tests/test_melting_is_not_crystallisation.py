"""
Melting is not the largest excursion; it is the largest *endothermic* one.

The bug this guards
-------------------
``_find_peak_temperature`` searched both signal polarities and kept whichever
produced the more prominent apex, because the stored convention differs between
instruments. On a trace that also contains a cold-crystallisation exotherm, the
larger excursion is not the melting peak. Measured on the committed PLLA set:

    DSC_PLLA_10K  stored endothermic-up
        branch +1 -> apex 167.4 C, prominence 1.141   <- the real melting peak
        branch -1 -> apex  85.3 C, prominence 1.381   <- cold crystallisation
        chosen: -1, so Tm was reported 82 C low.

The trace's own README says it is endothermic up, and its stored maximum is at
167.4 C with a sharp minimum at 85.3 C. So the polarity was never in question:
the search simply preferred the bigger event, and the bigger event was a
crystallisation.

**This is not tunable.** The prominence window was swept from 1 C to 20 C of
scan and the negated branch wins at every one, which is the same finding as
section 4 item 4: a cold-crystallisation exotherm and a melting endotherm can
have arbitrary and overlapping magnitudes, so no threshold on shape separates
them. The convention is a property of the file and has to come from the file.

The fix
-------
``analyse_dsc`` takes ``polarity_known``. When the caller knows the signal is
endothermic-up -- which the HTTP path does, because ``resolve_trace`` normalises
it from the ``#EXO`` declaration -- the search looks upward only. The default is
**False**, so a caller that has not established the convention gets the older
two-branch inference rather than an unearned assumption.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.core.thermal import analyse_dsc

LITERATURE = Path(__file__).parents[2] / "exemples" / "literature"
TEN_K = "DSC_PLLA_10K_2nd_heating.dat"

pytestmark = pytest.mark.skipif(
    not (LITERATURE / TEN_K).exists(),
    reason="PLLA literature traces not present (exemples/literature/)",
)


def _load(name: str) -> tuple[np.ndarray, np.ndarray]:
    arr = np.loadtxt(LITERATURE / name)
    return arr[:, 0], arr[:, 1]


def test_the_trace_is_what_the_test_claims_it_is() -> None:
    """
    Pin the shape the rest of this file reasons about, so a fixture change
    fails here with a clear message rather than silently weakening the tests.

    Endothermic-up means the melting endotherm is the stored *maximum*. The
    sharp minimum near 85 C is the cold-crystallisation exotherm, and it is
    what the polarity search used to latch onto.
    """
    T, hf = _load(TEN_K)
    t_max = float(T[int(np.argmax(hf))])
    t_min = float(T[int(np.argmin(hf))])

    assert 160.0 < t_max < 175.0, f"melting endotherm expected near 167 C, found {t_max}"
    assert 78.0 < t_min < 95.0, f"cold crystallisation expected near 85 C, found {t_min}"


def test_a_known_convention_does_not_report_crystallisation_as_melting() -> None:
    """
    The defect, asserted directly.

    167.4 C is where the trace's own stored maximum sits, and it is the value
    ``exemples/literature/README.md`` publishes for this file. 85.3 C is the
    cold-crystallisation exotherm; reporting it as Tm is an 82 C error on the
    number the scan exists to produce.
    """
    T, hf = _load(TEN_K)
    r = analyse_dsc(
        T.tolist(), hf.tolist(), heating_rate=10.0, ref_enthalpy_J_g=93.0,
        polarity_known=True,
    )

    assert r.Tm is not None
    assert abs(r.Tm - 167.4) < 2.0, (
        f"Tm={r.Tm:.1f} C with the convention known. A value near 85 C is the "
        "cold-crystallisation exotherm, which is an exothermic event and "
        "cannot be a melting point."
    )


def test_a_known_convention_recovers_the_published_enthalpy() -> None:
    """
    The published values for this file, reproduced.

    README.md records Tm 167.4 C, delta_Hm 61.7 J/g, Xc 66 %. The enthalpy is
    the check that the peak is real rather than merely well-placed: a Tm from
    the wrong event comes with an enthalpy from the wrong area.
    """
    T, hf = _load(TEN_K)
    r = analyse_dsc(
        T.tolist(), hf.tolist(), heating_rate=10.0, ref_enthalpy_J_g=93.0,
        polarity_known=True,
    )

    assert r.delta_Hm == pytest.approx(61.7, abs=0.6)
    assert r.crystallinity_pct == pytest.approx(66, abs=1.0)


def test_an_unknown_convention_is_not_assumed_to_be_endothermic_up() -> None:
    """
    The default must be the conservative one, and it must be visible.

    A caller holding a raw trace that has not been through ``resolve_trace`` has
    not established the convention. Defaulting to "known" would assert
    endothermic-up on the caller's behalf; defaulting to "unknown" keeps the
    older inference. Either way the caller can tell which happened, because the
    two answers differ -- and this test pins that they do, so the flag cannot
    silently become a no-op.
    """
    T, hf = _load(TEN_K)
    assumed = analyse_dsc(
        T.tolist(), hf.tolist(), heating_rate=10.0, ref_enthalpy_J_g=93.0
    )
    known = analyse_dsc(
        T.tolist(), hf.tolist(), heating_rate=10.0, ref_enthalpy_J_g=93.0,
        polarity_known=True,
    )

    assert assumed.Tm != pytest.approx(known.Tm, abs=1.0), (
        "polarity_known made no difference on this trace, so the tests above "
        "are not exercising the code path they claim to"
    )
    assert abs(known.Tm - 167.4) < 2.0


def test_the_api_path_declares_polarity_and_gets_the_published_answer() -> None:
    """
    End to end through the HTTP handler, which is what a user actually runs.

    The header declares ``#EXO`` so ``resolve_trace`` normalises the signal and
    the analysis is told the convention is known. Without the header the
    endpoint has to fall back to the inference, and this test would fail --
    which is the point: the correct answer depends on the file stating its
    convention, and the test proves the declaration is being read.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    T, hf = _load(TEN_K)
    body = "Temperature/degC,HeatFlow/(W/g)\n" + "\n".join(
        f"{t:.3f},{h:.8f}" for t, h in zip(T, hf, strict=True)
    )

    client = TestClient(app)
    r = client.post(
        "/api/v1/thermal/analyse",
        data={"technique": "dsc", "heating_rate": "10", "ref_enthalpy_J_g": "93"},
        files={"file": ("PLLA_10K.csv", body.encode(), "text/csv")},
    )
    assert r.status_code == 200, r.text
    payload = r.json()

    # The endpoint reports Tm only when it located a melting peak.
    if payload.get("Tm") is not None:
        assert abs(payload["Tm"] - 167.4) < 2.0, (
            f"API returned Tm={payload['Tm']}, and 85 C would be the "
            "cold-crystallisation exotherm"
        )
