"""
Molar-mass averages from a molecular-weight distribution.

References
----------
- IUPAC. "Dispersity" in polymer science (Recommendations 2009).
  Pure Appl. Chem. 81(2), 351-353 (2009). doi:10.1351/PAC-REC-08-05-02
- IUPAC. Compendium of Macromolecular Nomenclature (Purple Book), 1991.
  Definitions of Mn, Mw, Mz, Mv.
- Rudin, A. "The Elements of Polymer Science and Engineering", 3rd ed.,
  Ch. 2 (Molecular Weight and Its Distribution). Academic Press, 2012.
- Hiemenz, P.C.; Lodge, T.P. "Polymer Chemistry", 2nd ed., Ch. 1.
  CRC Press, 2007.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

__all__ = [
    "MolarMassResult",
    "moment_averages",
    "mark_houwink_viscosity_average",
    "log_normal_moments",
]

# Relative tolerance for the sum of weight fractions. 1e-3 is deliberately
# loose: GPC/SEC slice data is exported with 3-4 significant figures and
# rounding to 3 dp routinely leaves a residual of a few 1e-4.
DEFAULT_SUM_TOL = 1e-3

# Below this value of K, Mv is numerically indistinguishable from Mw for the
# purposes of a laboratory report (MacroFlux convention, see MWC docs).
_MV_EQUALS_MW_REL_TOL = 1e-4


@dataclass(frozen=True)
class MolarMassResult:
    """Averages and derived quantities. All masses in g/mol."""

    Mn: float
    Mw: float
    Mz: float
    Mz_plus_1: float
    dispersity: float
    kuhn_mass: float

    def as_dict(self) -> dict[str, float]:
        return {
            "Mn": self.Mn,
            "Mw": self.Mw,
            "Mz": self.Mz,
            "Mz_plus_1": self.Mz_plus_1,
            "dispersity": self.dispersity,
            "kuhn_mass": self.kuhn_mass,
        }


def _as_float_array(values, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional.")
    if arr.size == 0:
        raise ValueError(f"{name} cannot be empty.")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values (NaN or inf).")
    return arr


def _validate_weights(weight_fractions: Sequence[float], tol: float) -> np.ndarray:
    w = _as_float_array(weight_fractions, "weight_fractions")
    if np.any(w < 0):
        raise ValueError("Weight fractions must be non-negative.")
    total = float(np.sum(w))
    if total <= 0:
        raise ValueError("Weight fractions sum to zero.")
    if abs(total - 1.0) > tol:
        raise ValueError(
            f"Weight fractions must sum to 1.0 (within tolerance {tol:g}). "
            f"Got {total:.6f}."
        )
    return w


def moment_averages(
    masses: Sequence[float],
    weight_fractions: Sequence[float],
    tol: float = DEFAULT_SUM_TOL,
) -> MolarMassResult:
    """
    Compute Mn, Mw, Mz and Mz+1 from a discrete weight distribution.

    Using weight fractions w_i summing to 1, the number average is the
    harmonic mean

        Mn = 1 / sum(w_i / M_i)

    and the higher averages are the moments of the weight distribution

        Mw = sum(w_i * M_i)
        Mz = sum(w_i * M_i^2) / sum(w_i * M_i)
        Mz+1 = sum(w_i * M_i^3) / sum(w_i * M_i^2)

    The general moment definition (IUPAC Purple Book) is

        M_k = sum(w_i * M_i^k) / sum(w_i * M_i^(k-1))

    which reduces to Mw for k=1, Mz for k=2 and Mz+1 for k=3.

    Raises
    ------
    ValueError
        If lengths differ, masses are non-positive, fractions are negative,
        values are non-finite, or fractions do not sum to 1 within ``tol``.
    """
    m = _as_float_array(masses, "masses")
    w = _validate_weights(weight_fractions, tol)

    if m.shape != w.shape:
        raise ValueError("Masses and weight fractions must have the same length.")
    if np.any(m <= 0):
        raise ValueError("All masses must be positive.")

    reciprocal = float(np.sum(w / m))
    if reciprocal <= 0:
        raise ValueError("Invalid distribution: sum(w/M) is not positive.")

    Mn = 1.0 / reciprocal
    sum_wm = float(np.sum(w * m))
    sum_wm2 = float(np.sum(w * m**2))
    sum_wm3 = float(np.sum(w * m**3))

    Mw = sum_wm
    Mz = sum_wm2 / sum_wm
    Mz_plus_1 = sum_wm3 / sum_wm2

    # Kuhn-Mark-Houwink-Sakurada "mass average" (a.k.a. viscosity average)
    # in the limit a = 1, which is exactly Mw. Exposed so that the UI can
    # show the reference point the MWC parameter interpolates from.
    kuhn_mass = Mw

    return MolarMassResult(
        Mn=float(Mn),
        Mw=float(Mw),
        Mz=float(Mz),
        Mz_plus_1=float(Mz_plus_1),
        dispersity=float(Mw / Mn),
        kuhn_mass=float(kuhn_mass),
    )


def mark_houwink_viscosity_average(
    masses: Sequence[float],
    weight_fractions: Sequence[float],
    a: float,
    tol: float = DEFAULT_SUM_TOL,
) -> float:
    """
    Viscosity-average molar mass Mv from the Mark-Houwink-Sakurada exponent a.

        Mv = [ sum(w_i * M_i^a) ]^(1/a)

    Source: Rudin, "The Elements of Polymer Science and Engineering",
    3rd ed., Eq. 2.33; also IUPAC Purple Book entry for Mv.

    Limits
    ------
    a -> 1 gives Mv -> Mw. a -> 0 is singular: the expression degenerates
    into the geometric mean, which for a weight distribution is not a
    measured quantity, so ``a`` must be strictly positive.

    The value of ``a`` is solvent/polymer/temperature specific and is
    tabulated in the Polymer Handbook (Brandrup, Immergut, Grulke, 5th ed.,
    Ch. VII). It is NOT a property of the tool.

    Raises
    ------
    ValueError
        If ``a`` <= 0, or if the distribution is invalid.
    """
    if not math.isfinite(a) or a <= 0:
        raise ValueError("Mark-Houwink exponent a must be finite and > 0.")

    m = _as_float_array(masses, "masses")
    w = _validate_weights(weight_fractions, tol)
    if m.shape != w.shape:
        raise ValueError("Masses and weight fractions must have the same length.")
    if np.any(m <= 0):
        raise ValueError("All masses must be positive.")

    power = float(np.sum(w * m**a))
    if power <= 0:
        raise ValueError("Invalid distribution: sum(w * M^a) is not positive.")

    return float(power ** (1.0 / a))


def log_normal_moments(
    Mn: float,
    dispersity: float,
    n_points: int = 2000,
    n_sigma: float = 4.0,
) -> dict[str, float]:
    """
    Populate a log-normal MWD (the standard SEC calibration standard shape)
    and return its averages. Used by the UI to show what a given dispersity
    looks like as a distribution, and by the test-suite as an independent
    check on ``moment_averages``.

    For a log-normal distribution parameterised by ln(M) ~ N(mu, sigma^2):

        Mw / Mn = exp(sigma^2)
        Mz / Mw = exp(sigma^2)

    Source: Rudin, 3rd ed., Section 2.5; Hiemenz & Lodge, Ch. 1.

    Returns a dict with Mn, Mw, Mz, Mz_plus_1 and dispersity as recovered
    from the discretised distribution (so it can be compared against the
    analytic values).
    """
    if not math.isfinite(Mn) or Mn <= 0:
        raise ValueError("Mn must be finite and positive.")
    if not math.isfinite(dispersity) or dispersity < 1.0:
        raise ValueError("Dispersity must be finite and >= 1.")
    if n_points < 10:
        raise ValueError("n_points must be at least 10.")
    if n_sigma <= 0:
        raise ValueError("n_sigma must be positive.")

    sigma = math.sqrt(math.log(dispersity))
    mu = math.log(Mn) + 0.5 * sigma**2  # so that E[ln M] shifted gives Mn

    # Integrate in ln(M) so the grid is uniform in the natural variable.
    lo = mu - n_sigma * sigma
    hi = mu + n_sigma * sigma
    ln_m = np.linspace(lo, hi, n_points)
    m = np.exp(ln_m)
    pdf = np.exp(-0.5 * ((ln_m - mu) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    w = pdf * (hi - lo) / (n_points - 1)
    w = w / np.sum(w)

    result = moment_averages(m, w)
    return result.as_dict()
