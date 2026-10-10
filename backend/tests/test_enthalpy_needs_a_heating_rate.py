"""
An area in W/g·°C is not an enthalpy, and must not be reported as one.

The bug this guards
-------------------
The melting integral accumulates ``excess`` over *temperature*, giving units of
W/g·°C. Dividing by the scan rate in K/s converts it to J/g, and the code
comment at that division says exactly that: "which is why the rate is
required". The rate was not required. When it was absent the division was
skipped and the unconverted area was assigned to ``delta_Hm`` anyway, and the
crystallinity was computed from it.

On ``DSC_PLLA_10K_2nd_heating`` that produces two numbers that both look like
results and differ by a factor of six:

    with heating_rate=10   delta_Hm = 61.17 J/g   Xc = 65.8 %
    without               delta_Hm = 10.19 "J/g"  Xc = 11.0 %

10.19 is the raw area. Calling it J/g is a unit error, not a rounding error, and
the factor it is wrong by is the scan rate -- anywhere from 1 to 40 K/min, so
there is no bound to state and no correction to apply. The only defensible
answer is to withhold the enthalpy and the crystallinity that depends on it,
which is what the analysis now does.

This is the same shape as the defects in section 3.3: an input the method
requires was accepted as absent, and arithmetic that is otherwise correct
produced a number for a quantity it did not have the data to compute.
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


def _load() -> tuple[np.ndarray, np.ndarray]:
    arr = np.loadtxt(LITERATURE / TEN_K)
    return arr[:, 0], arr[:, 1]


def test_without_a_heating_rate_there_is_no_enthalpy() -> None:
    """
    No rate, no J/g. The peak position is unaffected and stays reported.

    Both halves are asserted together because the interesting failure is not
    "a number is missing" but "a number is present that should not be": a tool
    that reports Tm and a plausible enthalpy is more dangerous than one that
    reports Tm and declines to state an enthalpy.
    """
    T, hf = _load()
    r = analyse_dsc(
        T.tolist(), hf.tolist(), ref_enthalpy_J_g=93.0, polarity_known=True
    )

    assert r.Tm is not None, "the peak position does not need the rate"
    assert r.delta_Hm is None, (
        f"delta_Hm={r.delta_Hm} reported without a heating rate. The integral "
        "is in W/g.C and only becomes J/g after dividing by the rate; this "
        "value is the unconverted area."
    )
    assert r.crystallinity_pct is None, (
        f"crystallinity={r.crystallinity_pct} % computed from an enthalpy that "
        "could not be computed"
    )


def test_the_unconverted_area_would_have_been_a_sixfold_error() -> None:
    """
    Pin the magnitude, so the refusal is not mistaken for caution.

    61.17 against 10.19 is not a small discrepancy that a tolerance could
    absorb: it changes a crystallinity of 66 % into 11 %, and 11 % is a
    perfectly ordinary number for a semi-crystalline polymer. Nothing about it
    would look wrong to a reader.
    """
    T, hf = _load()
    with_rate = analyse_dsc(
        T.tolist(), hf.tolist(), heating_rate=10.0, ref_enthalpy_J_g=93.0,
        polarity_known=True,
    )
    without = analyse_dsc(
        T.tolist(), hf.tolist(), ref_enthalpy_J_g=93.0, polarity_known=True
    )

    assert with_rate.delta_Hm == pytest.approx(61.17, abs=0.1)
    assert without.delta_Hm is None
    # The factor between them is the scan rate in K/s, which is 1/6 for
    # 10 K/min -- so the unconverted area is exactly 1/6 of the enthalpy.
    assert with_rate.delta_Hm / 6.0 == pytest.approx(10.19, abs=0.05)


def test_a_rate_still_produces_the_published_enthalpy() -> None:
    """
    The refusal must not have broken the case that has the data.

    `exemples/literature/README.md` publishes 61.7 J/g for this trace.
    """
    T, hf = _load()
    r = analyse_dsc(
        T.tolist(), hf.tolist(), heating_rate=10.0, ref_enthalpy_J_g=93.0,
        polarity_known=True,
    )

    assert r.delta_Hm == pytest.approx(61.7, abs=0.6)
    assert r.crystallinity_pct == pytest.approx(66, abs=1.0)
