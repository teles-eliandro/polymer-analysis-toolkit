"""
Oscillatory shear rheology: storage and loss moduli.

References
----------
- Macosko, C.W. "Rheology: Principles, Measurements and Applications".
  Wiley-VCH, 1994. (Small-amplitude oscillatory shear, time-temperature
  superposition.)
- Ferry, J.D. "Viscoelastic Properties of Polymers", 3rd ed. Wiley, 1980.
- Rubinstein, M.; Colby, R.H. "Polymer Physics". Oxford, 2003. Ch. 7-8
  (reptation, plateau modulus, tube theory).
- Winter, H.H.; Chambon, F. "Analysis of linear viscoelasticity of a
  crosslinking polymer at the gel point." J. Rheol. 30, 367 (1986).
  doi:10.1122/1.549853  (gel point criterion G' ~ G'' ~ omega^n)
- ASTM D4440-15, "Standard Test Method for Plastics: Dynamic Mechanical
  Properties Melt Rheology".
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "RheologyResult",
    "analyse_rheology",
    "cross_over_point",
    "plateau_modulus",
    "relaxation_time",
]


@dataclass
class RheologyResult:
    """Oscillatory shear results. Moduli in Pa, frequency in rad/s."""

    #: Frequency at which G' crosses G'' (terminal relaxation crossover).
    cross_over_freq: float | None
    #: Modulus at the crossover point.
    cross_over_modulus: float | None
    #: Whether G' is already above G'' at the lowest measured frequency
    #: (indicating a solid-like or gelled sample).
    solid_like_at_low_freq: bool
    #: Plateau modulus estimated as G' at the minimum of tan(delta).
    plateau_modulus_G0: float | None
    #: Longest relaxation time lambda = 1/omega_cross, in seconds.
    relaxation_time_s: float | None
    #: Power-law exponent of G' in the terminal region (log-log slope).
    terminal_slope_Gprime: float | None
    #: Power-law exponent of G'' in the terminal region.
    terminal_slope_Gpp: float | None
    #: Zero-shear viscosity estimated from the terminal region, in Pa.s.
    zero_shear_viscosity_Pas: float | None
    #: Gel-point test (Winter-Chambon): frequency-independent tan(delta) in
    #: the terminal region indicates a critical gel.
    gel_point_detected: bool
    #: tan(delta) values used for the gel test and their spread.
    tan_delta_spread: float | None
    #: Curve data for plotting.
    omega: list[float] = field(default_factory=list)
    G_prime: list[float] = field(default_factory=list)
    G_double_prime: list[float] = field(default_factory=list)
    tan_delta: list[float] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "cross_over_freq": self.cross_over_freq,
            "cross_over_modulus": self.cross_over_modulus,
            "solid_like_at_low_freq": self.solid_like_at_low_freq,
            "plateau_modulus_G0": self.plateau_modulus_G0,
            "relaxation_time_s": self.relaxation_time_s,
            "terminal_slope_Gprime": self.terminal_slope_Gprime,
            "terminal_slope_Gpp": self.terminal_slope_Gpp,
            "zero_shear_viscosity_Pas": self.zero_shear_viscosity_Pas,
            "gel_point_detected": self.gel_point_detected,
            "tan_delta_spread": self.tan_delta_spread,
            "omega": self.omega,
            "G_prime": self.G_prime,
            "G_double_prime": self.G_double_prime,
            "tan_delta": self.tan_delta,
        }


def _clean3(w, g1, g2) -> tuple:
    omega = np.asarray(w, dtype=np.float64)
    gp = np.asarray(g1, dtype=np.float64)
    gpp = np.asarray(g2, dtype=np.float64)
    if not (omega.shape == gp.shape == gpp.shape):
        raise ValueError("omega, G_prime and G_double_prime must have the same length.")
    if omega.size < 4:
        raise ValueError("At least 4 frequency points are required.")
    mask = np.isfinite(omega) & np.isfinite(gp) & np.isfinite(gpp)
    omega, gp, gpp = omega[mask], gp[mask], gpp[mask]
    if omega.size < 4:
        raise ValueError("Fewer than 4 finite points remain after cleaning.")
    if np.any(omega <= 0) or np.any(gp <= 0) or np.any(gpp <= 0):
        raise ValueError(
            "Frequencies and moduli must be strictly positive to convert to "
            "logarithmic space."
        )
    order = np.argsort(omega)
    return omega[order], gp[order], gpp[order]


def cross_over_point(omega: np.ndarray, gp: np.ndarray, gpp: np.ndarray):
    """
    Frequency and modulus where G' = G'', by linear interpolation in log-log
    space between the bracketing points.

    Returns (None, None) when the curves do not cross inside the measured
    range, which is itself a reportable result (see
    ``solid_like_at_low_freq``).
    """
    diff = gp - gpp
    sign_change = np.where(np.diff(np.sign(diff)))[0]
    if sign_change.size == 0:
        return None, None
    i = int(sign_change[0])
    lw1, lw2 = math.log10(omega[i]), math.log10(omega[i + 1])
    lg1a, lg1b = math.log10(gp[i]), math.log10(gp[i + 1])
    lg2a, lg2b = math.log10(gpp[i]), math.log10(gpp[i + 1])

    # Solve for the log-frequency where the two log-linear segments meet.
    d_a = lg1a - lg2a
    d_b = lg1b - lg2b
    if d_a == d_b:
        lw = lw1
    else:
        lw = lw1 + (lw2 - lw1) * (0.0 - d_a) / (d_b - d_a)
    lg = lg1a + (lg1b - lg1a) * (lw - lw1) / (lw2 - lw1)
    return float(10.0**lw), float(10.0**lg)


def plateau_modulus(omega: np.ndarray, gp: np.ndarray, gpp: np.ndarray):
    """
    Plateau modulus G0^0 estimated as G' at the frequency where tan(delta) is
    minimum, following the operational definition discussed in
    Ferry (1980) and in Rubinstein & Colby (2003), Ch. 7.

    The true plateau modulus from ``G0 = (2/pi) * integral(G'' d ln omega)``
    requires the full relaxation spectrum; the tan(delta) minimum is the
    standard proxy when only a frequency sweep is available, and it is
    slightly biased low. Reported as an estimate, not a measurement.
    """
    tan_d = gpp / gp
    idx = int(np.argmin(tan_d))
    return float(gp[idx])


def relaxation_time(omega_cross: float | None) -> float | None:
    """
    Longest (reptation) relaxation time lambda = 1 / omega_cross, in seconds.

    Source: Rubinstein & Colby, Ch. 8; the crossover of G' and G'' marks the
    inverse of the terminal relaxation time for a monodisperse melt.
    """
    if omega_cross is None or omega_cross <= 0:
        return None
    return float(1.0 / omega_cross)


def _terminal_slopes(
    omega: np.ndarray, gp: np.ndarray, gpp: np.ndarray, fraction: float = 0.3
):
    """
    Log-log slopes of G' and G'' over the lowest-frequency ``fraction`` of
    the sweep. For a Maxwellian terminal region the theory requires slopes of
    2 and 1 respectively (Ferry, 1980), so these values are diagnostic of how
    far into the terminal regime the measurement reached.
    """
    n = max(2, int(fraction * omega.size))
    n = min(n, omega.size)
    if n < 2:
        return None, None
    lw = np.log10(omega[:n])
    if np.allclose(lw, lw[0]):
        return None, None
    s1, _ = np.polyfit(lw, np.log10(gp[:n]), 1)
    s2, _ = np.polyfit(lw, np.log10(gpp[:n]), 1)
    return float(s1), float(s2)


def analyse_rheology(
    omega: Sequence[float],
    G_prime: Sequence[float],
    G_double_prime: Sequence[float],
    gel_tolerance: float = 0.15,
) -> RheologyResult:
    """
    Compute the standard descriptors of a small-amplitude oscillatory shear
    frequency sweep.

    Parameters
    ----------
    omega : sequence
        Angular frequency in rad/s.
    G_prime, G_double_prime : sequence
        Storage and loss moduli in Pa.
    gel_tolerance : float
        Relative spread of tan(delta) across the measured range below which
        the Winter-Chambon critical-gel criterion is considered satisfied at
        the frequency range probed.

    Notes
    -----
    The Winter-Chambon criterion states that at the gel point both moduli
    follow the same power law, G' ~ G'' ~ omega^n, so tan(delta) = G''/G' is
    independent of frequency. A frequency-independent tan(delta) is therefore
    evidence of a critical gel. The ``gel_tolerance`` used here is an
    operational choice; the literature reports n values from about 0.2 to 0.8
    depending on the system (Winter & Chambon, 1986).
    """
    om, gp, gpp = _clean3(omega, G_prime, G_double_prime)

    x_freq, x_mod = cross_over_point(om, gp, gpp)
    solid_like = bool(gp[0] > gpp[0])
    g0 = plateau_modulus(om, gp, gpp)
    lam = relaxation_time(x_freq)
    s1, s2 = _terminal_slopes(om, gp, gpp)

    tan_d = gpp / gp
    spread = float((np.max(tan_d) - np.min(tan_d)) / np.mean(tan_d))
    gel = bool(spread <= gel_tolerance)

    # Zero-shear viscosity from the terminal region.
    # For a Maxwell fluid G'' = eta0 * omega at low frequency, so the
    # intercept of log(G'') vs log(omega) gives eta0. Using the loss modulus
    # is more robust than G'/omega because it does not require the slope to
    # be exactly 2.
    eta0 = None
    n = max(2, min(int(0.3 * om.size), om.size))
    if n >= 2:
        lw = np.log10(om[:n])
        if not np.allclose(lw, lw[0]):
            slope, intercept = np.polyfit(lw, np.log10(gpp[:n]), 1)
            # eta0 = G''/omega at omega -> 0 with a slope-1 assumption.
            # Compute directly at the lowest frequency with slope correction.
            eta0 = float(gpp[0] / (om[0] ** min(slope, 1.0))) if slope > 0 else None
            if eta0 is not None and not math.isfinite(eta0):
                eta0 = None

    return RheologyResult(
        cross_over_freq=x_freq,
        cross_over_modulus=x_mod,
        solid_like_at_low_freq=solid_like,
        plateau_modulus_G0=g0,
        relaxation_time_s=lam,
        terminal_slope_Gprime=s1,
        terminal_slope_Gpp=s2,
        zero_shear_viscosity_Pas=eta0,
        gel_point_detected=gel,
        tan_delta_spread=spread,
        omega=[float(v) for v in om],
        G_prime=[float(v) for v in gp],
        G_double_prime=[float(v) for v in gpp],
        tan_delta=[float(v) for v in tan_d],
    )
