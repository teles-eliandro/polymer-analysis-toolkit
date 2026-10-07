"""
Quasi-static tensile testing of polymers.

References
----------
- ISO 527-1:2019, "Plastics - Determination of tensile properties -
  Part 1: General principles".
- ISO 527-2:2012, "Plastics - Determination of tensile properties -
  Part 2: Moulding and extrusion plastics".
- ASTM D638-22, "Standard Test Method for Tensile Properties of Plastics".
- ASTM D882-18, "Standard Test Method for Tensile Properties of Thin
  Plastic Sheeting".
- Ward, I.M.; Sweeney, J. "Mechanical Properties of Solid Polymers",
  3rd ed. Wiley, 2012.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

__all__ = ["TensileResult", "analyse_tensile"]


@dataclass
class TensileResult:
    """Tensile properties. Stress in MPa, strain in percent, modulus in MPa."""

    #: Young's modulus from the initial linear region.
    E_MPa: float | None
    #: Stress at break.
    stress_break_MPa: float | None
    #: Strain at break, in percent.
    strain_break_pct: float | None
    #: Maximum stress reached (tensile strength).
    stress_max_MPa: float | None
    #: Strain at maximum stress.
    strain_max_pct: float | None
    #: Yield stress, where a yield point exists.
    stress_yield_MPa: float | None
    #: Yield strain.
    strain_yield_pct: float | None
    #: Toughness: work to fracture per unit volume, in MJ/m^3 (= J/cm^3).
    toughness_MJ_m3: float | None
    #: True when the curve shows a yield point (stress falls after a maximum
    #: before break).
    yielded: bool
    #: True when the specimen broke at the maximum stress (brittle behaviour).
    brittle: bool
    #: Engineering stress-strain curve, for plotting.
    strain_pct: list[float] = field(default_factory=list)
    stress_MPa: list[float] = field(default_factory=list)
    #: Window actually used for the modulus regression, as (strain %, stress).
    modulus_window: tuple[float, float] | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "E_MPa": self.E_MPa,
            "stress_break_MPa": self.stress_break_MPa,
            "strain_break_pct": self.strain_break_pct,
            "stress_max_MPa": self.stress_max_MPa,
            "strain_max_pct": self.strain_max_pct,
            "stress_yield_MPa": self.stress_yield_MPa,
            "strain_yield_pct": self.strain_yield_pct,
            "toughness_MJ_m3": self.toughness_MJ_m3,
            "yielded": self.yielded,
            "brittle": self.brittle,
            "strain_pct": self.strain_pct,
            "stress_MPa": self.stress_MPa,
            "modulus_window": (
                list(self.modulus_window) if self.modulus_window else None
            ),
        }


def _clean(x: Sequence[float], y: Sequence[float], xn: str, yn: str) -> tuple:
    xa = np.asarray(x, dtype=np.float64)
    ya = np.asarray(y, dtype=np.float64)
    if xa.shape != ya.shape:
        raise ValueError(f"{xn} and {yn} must have the same length.")
    if xa.size < 4:
        raise ValueError("At least 4 data points are required.")
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    if xa.size < 4:
        raise ValueError("Fewer than 4 finite data points remain.")
    order = np.argsort(xa)
    return xa[order], ya[order]


def _youngs_modulus(
    strain_pct: np.ndarray, stress: np.ndarray
) -> tuple[float | None, tuple[float, float] | None]:
    """
    Young's modulus by linear regression on the initial linear region.

    Units. Stress is in MPa and strain in percent, so the slope of the
    regression is in MPa per percent, not MPa. Since 1 % = 0.01 absolute
    strain, the modulus in MPa is the slope multiplied by 100. Omitting that
    factor under-reports E by exactly two orders of magnitude, which is the
    single easiest error to make with percent strain axes.

    Window selection. ISO 527-1 specifies the secant modulus between 0.05 %
    and 0.25 % strain as a default for stiff plastics. That window is far too
    narrow for the coarse strain resolution typical of a single test machine
    export, so this implementation finds the largest initial window whose
    coefficient of determination (r^2) stays above 0.999, then reports the
    slope of the regression through it. The window used is returned so the
    value is auditable rather than opaque.
    """
    n = strain_pct.size
    best: tuple[float, float, tuple[float, float]] | None = None

    for end in range(4, max(5, int(0.4 * n)) + 1):
        xs = strain_pct[:end]
        ys = stress[:end]
        if np.allclose(xs, xs[0]):
            continue
        slope, intercept = np.polyfit(xs, ys, 1)
        pred = slope * xs + intercept
        ss_res = float(np.sum((ys - pred) ** 2))
        ss_tot = float(np.sum((ys - np.mean(ys)) ** 2))
        if ss_tot <= 0:
            continue
        r2 = 1.0 - ss_res / ss_tot
        if r2 >= 0.999 and slope > 0:
            span = float(xs[-1] - xs[0])
            cand = (span, float(slope), (float(xs[0]), float(xs[-1])))
            if best is None or cand[0] > best[0]:
                best = cand

    if best is None:
        # Fall back to the ISO 527-1 default secant window if it exists.
        lo, hi = 0.05, 0.25
        sel = (strain_pct >= lo) & (strain_pct <= hi)
        if sel.sum() >= 2:
            slope, _ = np.polyfit(strain_pct[sel], stress[sel], 1)
            return float(slope) * 100.0, (lo, hi)
        # Last resort: first quarter, flagged by the returned window.
        end = max(4, int(0.25 * n))
        slope, _ = np.polyfit(strain_pct[:end], stress[:end], 1)
        return (
            float(slope) * 100.0,
            (float(strain_pct[0]), float(strain_pct[end - 1])),
        )

    return best[1] * 100.0, best[2]


def analyse_tensile(
    strain_pct: Sequence[float],
    stress_MPa: Sequence[float],
    modulus_window: tuple[float, float] | None = None,
) -> TensileResult:
    """
    Compute the standard tensile descriptors from an engineering
    stress-strain curve.

    Parameters
    ----------
    strain_pct : sequence
        Engineering strain in percent.
    stress_MPa : sequence
        Engineering stress in MPa.
    modulus_window : (float, float), optional
        Force the modulus regression to a strain range instead of detecting
        the linear region automatically.

    Notes
    -----
    Toughness is the area under the whole curve, computed by the trapezoid
    rule. With stress in MPa and strain in percent the result is in units of
    MPa*percent = 0.01 MJ/m^3, hence the factor of 100 in the conversion.
    """
    s, sig = _clean(strain_pct, stress_MPa, "strain_pct", "stress_MPa")
    if np.any(sig < 0):
        raise ValueError("Stress values must be non-negative for a tensile test.")

    if modulus_window is not None:
        lo, hi = modulus_window
        sel = (s >= lo) & (s <= hi)
        if sel.sum() < 2:
            raise ValueError(
                f"The requested modulus window {modulus_window} contains "
                f"{int(sel.sum())} point(s); at least 2 are required."
            )
        slope, _ = np.polyfit(s[sel], sig[sel], 1)
        # Same unit correction as in _youngs_modulus: slope is MPa per
        # percent, and E in MPa needs the factor of 100.
        E = float(slope) * 100.0
        window: tuple[float, float] | None = (float(lo), float(hi))
    else:
        E, window = _youngs_modulus(s, sig)

    idx_max = int(np.argmax(sig))
    stress_max = float(sig[idx_max])
    strain_max = float(s[idx_max])

    stress_break = float(sig[-1])
    strain_break = float(s[-1])

    # Yield point: a local maximum that is followed by a drop of more than
    # 2 % of the peak stress before the specimen breaks.
    yielded = False
    stress_yield = strain_yield = None
    if 0 < idx_max < s.size - 1:
        after = sig[idx_max:]
        if float(np.min(after)) < 0.98 * stress_max:
            yielded = True
            stress_yield = stress_max
            strain_yield = strain_max

    brittle = (not yielded) and abs(stress_break - stress_max) < 1e-9

    # Work per unit volume (toughness).
    #
    # With stress in MPa and strain as a percentage, the trapezoid integral
    # comes out in MPa*%. Convert it to MJ/m^3:
    #   1 MPa * 1 (absolute strain) = 1e6 Pa * 1 = 1e6 J/m^3 = 1 MJ/m^3
    # and 1 % strain = 0.01 absolute, so 1 MPa*% = 0.01 MJ/m^3.
    # Check: a linear ramp to 100 MPa at 5 % strain encloses
    # 0.5 * 100 * 5 = 250 MPa*%, which is therefore 2.5 MJ/m^3 - the textbook
    # value for a brittle polymer of that strength and elongation.
    area = float(np.trapezoid(sig, s))
    toughness = area * 0.01

    return TensileResult(
        E_MPa=E,
        stress_break_MPa=stress_break,
        strain_break_pct=strain_break,
        stress_max_MPa=stress_max,
        strain_max_pct=strain_max,
        stress_yield_MPa=stress_yield,
        strain_yield_pct=strain_yield,
        toughness_MJ_m3=toughness,
        yielded=yielded,
        brittle=brittle,
        strain_pct=[float(v) for v in s],
        stress_MPa=[float(v) for v in sig],
        modulus_window=window,
    )
