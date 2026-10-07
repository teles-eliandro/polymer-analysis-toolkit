"""
Thermal analysis: TGA and DSC.

References
----------
- ASTM E1131-20, "Standard Test Method for Compositional Analysis by
  Thermogravimetry".
- ASTM E2550-21, "Standard Test Method for Thermal Stability by
  Thermogravimetry".
- ISO 11358-1:2022, "Plastics - Thermogravimetry (TG) of polymers -
  Part 1: General principles".
- ASTM D3418-21, "Standard Test Method for Transition Temperatures and
  Enthalpies of Fusion and Crystallization of Polymers by DSC".
- ISO 11357-2:2020, "Plastics - Differential scanning calorimetry (DSC) -
  Part 2: Determination of glass transition temperature".
- Ehrenstein, G.W.; Riedel, G.; Trawiel, P. "Thermal Analysis of Plastics:
  Theory and Practice". Hanser, 2004.
- Gabbott, P. (ed.) "Principles and Applications of Thermal Analysis".
  Blackwell, 2008.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "TGAResult",
    "DSCResult",
    "analyse_tga",
    "analyse_dsc",
    "onset_temperature",
    "inflection_temperature",
]

#: Minimum size of a candidate step, as a fraction of the total signal range,
#: for it to be accepted as a glass transition. A real Tg changes the heat
#: capacity by a few tenths of a J/(g.K), which on a trace also containing a
#: melting peak is a small but clearly non-zero fraction of the excursion.
#: Setting this too low lets instrument drift be reported as Tg; too high
#: discards weak transitions in highly crystalline samples. 3 % is a
#: deliberately conservative floor: it rejects curvature on a melt-only trace
#: while accepting every Tg that would be visible to an analyst.
_MIN_TG_STEP_FRACTION = 0.03


@dataclass
class TGAResult:
    """Thermogravimetric results. Temperatures in degrees Celsius."""

    #: Temperature at which 5 % mass loss has occurred (TGA "degradation
    #: onset" per ASTM E2550 convention, widely used for polymer stability).
    Td_5pct: float | None
    #: Temperature at which 10 % mass loss has occurred.
    Td_10pct: float | None
    #: Temperature of the global maximum rate of mass loss (the tallest DTG
    #: peak). NOTE: with several decomposition steps this is the step that
    #: loses mass fastest, not necessarily the first one. Per-step peaks are
    #: reported in ``steps``.
    T_max_rate: float | None
    #: Residue remaining at the end of the run, in percent.
    residue_pct: float
    #: Full decomposition point: temperature where 95 % of the mass is gone.
    T_95pct: float | None
    #: Step transitions detected as separate mass-loss events.
    steps: list[dict[str, float]] = field(default_factory=list)
    #: Temperatures and mass values of the curve, for plotting.
    temperature: list[float] = field(default_factory=list)
    mass_pct: list[float] = field(default_factory=list)
    dtg: list[float] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "Td_5pct": self.Td_5pct,
            "Td_10pct": self.Td_10pct,
            "T_max_rate": self.T_max_rate,
            "T_95pct": self.T_95pct,
            "residue_pct": self.residue_pct,
            "steps": self.steps,
            "temperature": self.temperature,
            "mass_pct": self.mass_pct,
            "dtg": self.dtg,
        }


@dataclass
class DSCResult:
    """Differential scanning calorimetry results. Temperatures in Celsius."""

    #: Glass transition temperature by the ASTM D3418 midpoint convention.
    Tg: float | None
    #: Extrapolated onset of the glass transition.
    Tg_onset: float | None
    #: Endpoint of the glass transition.
    Tg_end: float | None
    #: Change in heat capacity across Tg, in J/(g.K) if the signal is in W/g
    #: and the heating rate is supplied.
    delta_cp: float | None
    #: Melting peak temperature.
    Tm: float | None
    #: Melting enthalpy in J/g.
    delta_Hm: float | None
    #: Crystallization peak temperature (cooling).
    Tc: float | None
    #: Crystallization enthalpy in J/g.
    delta_Hc: float | None
    #: Degree of crystallinity in percent, if a 100 % crystalline reference
    #: enthalpy was supplied.
    crystallinity_pct: float | None
    #: Curve data for plotting.
    temperature: list[float] = field(default_factory=list)
    heat_flow: list[float] = field(default_factory=list)
    #: Warming steps applied and which one the results came from.
    direction: str = "heating"

    def as_dict(self) -> dict[str, object]:
        return {
            "Tg": self.Tg,
            "Tg_onset": self.Tg_onset,
            "Tg_end": self.Tg_end,
            "delta_cp": self.delta_cp,
            "Tm": self.Tm,
            "delta_Hm": self.delta_Hm,
            "Tc": self.Tc,
            "delta_Hc": self.delta_Hc,
            "crystallinity_pct": self.crystallinity_pct,
            "temperature": self.temperature,
            "heat_flow": self.heat_flow,
            "direction": self.direction,
        }


def _clean_curve(
    x: Sequence[float], y: Sequence[float], x_name: str, y_name: str
) -> tuple:
    xa = np.asarray(x, dtype=np.float64)
    ya = np.asarray(y, dtype=np.float64)
    if xa.shape != ya.shape:
        raise ValueError(f"{x_name} and {y_name} must have the same length.")
    if xa.size < 3:
        raise ValueError("At least 3 data points are required.")
    mask = np.isfinite(xa) & np.isfinite(ya)
    xa, ya = xa[mask], ya[mask]
    if xa.size < 3:
        raise ValueError("Fewer than 3 finite data points remain after cleaning.")
    order = np.argsort(xa)
    return xa[order], ya[order]


def _smooth(y: np.ndarray, window: int) -> np.ndarray:
    """Moving-average smoothing with reflective padding to keep the length."""
    if window <= 1:
        return y
    window = min(window, y.size)
    if window % 2 == 0:
        window -= 1
    if window <= 1:
        return y
    pad = window // 2
    padded = np.pad(y, pad, mode="edge")
    kernel = np.ones(window) / window
    return np.convolve(padded, kernel, mode="valid")


def _temperature_at_fraction(
    temperature: np.ndarray, mass_pct: np.ndarray, target_loss_pct: float
) -> float | None:
    """
    Temperature at which the sample has lost ``target_loss_pct`` percent of
    its initial mass, by linear interpolation on the TGA trace.

    The TGA convention measures loss relative to the initial mass, i.e. it
    looks for mass_pct == 100 - target_loss_pct.
    """
    target = 100.0 - target_loss_pct
    below = np.where(mass_pct <= target)[0]
    if below.size == 0:
        return None
    idx = int(below[0])
    if idx == 0:
        return float(temperature[0])
    t0, t1 = float(temperature[idx - 1]), float(temperature[idx])
    m0, m1 = float(mass_pct[idx - 1]), float(mass_pct[idx])
    if m0 == m1:
        return t1
    # Linear interpolation between the bracketing points.
    frac = (m0 - target) / (m0 - m1)
    return t0 + frac * (t1 - t0)


def onset_temperature(
    x, y, rising: bool = True, frac: float = 0.5
) -> float | None:
    """
    Extrapolated onset temperature of a step in ``y``.

    Implements the standard DSC region-of-interest construction: fit the
    tangent at the point of steepest change and intersect it with the
    extrapolated baseline before the transition. This is the construction
    required by ASTM D3418 for both Tg (onset) and Tm.

    Parameters
    ----------
    rising : bool
        True when the transition raises ``y`` (melting endotherm with the
        endothermic direction pointing up); False otherwise.
    frac : float
        Which crossing to return, as a fraction of the step height between
        the pre- and post-transition baselines. ASTM D3418 uses the midpoint
        of the step for Tg.
    """
    xa, ya = _clean_curve(x, y, "x", "y")
    dy = np.gradient(ya, xa)
    idx = int(np.argmax(dy) if rising else np.argmin(dy))

    # Baseline before the transition: mean of the first 15 % of the curve.
    n_base = max(3, int(0.15 * xa.size))
    baseline = float(np.mean(ya[:n_base]))

    slope = float(dy[idx])
    if slope == 0:
        return None
    # Tangent through the inflection point: y = y_i + slope*(x - x_i).
    x_i, y_i = float(xa[idx]), float(ya[idx])
    # Intersect with the baseline: baseline = y_i + slope*(x - x_i)
    x_cross = x_i + (baseline - y_i) / slope

    # Step height between pre-transition baseline and the post-transition
    # baseline, used for the midpoint (frac) convention.
    n_end = max(3, int(0.15 * xa.size))
    post = float(np.mean(ya[-n_end:]))
    of_interest = baseline + frac * (post - baseline)
    x_roi = x_i + (of_interest - y_i) / slope

    if rising:
        lo, hi = x_cross, x_roi
    else:
        lo, hi = x_roi, x_cross
    if not math.isfinite(x_roi):
        return float(x_cross)
    return float(max(min(x_roi, max(lo, hi)), min(lo, hi)))


def _find_step_temperature(
    T: np.ndarray, y: np.ndarray, exclude: tuple[float, float] | None = None
) -> int | None:
    """
    Index of the step-like transition in ``y`` (a change of baseline level),
    as opposed to a peak.

    A glass transition changes the *level* of the heat-flow baseline: the
    signal steps from one plateau to another. A melting endotherm returns to
    its baseline, so it is a peak, not a step. Distinguishing the two is the
    whole difficulty of automatic Tg detection, and it is why a derivative
    maximum alone always fails: the flanks of a sharp melting peak have a
    larger slope than a shallow Tg step does.

    The discriminator used here is the cumulative change: for a true step the
    difference between the mean of a window after the candidate and the mean
    of a window before it is large relative to the local noise, whereas for a
    peak those two means are similar because the signal returns.

    ``exclude`` optionally removes a temperature range (the melting region)
    from consideration.
    """
    n = T.size
    if n < 20:
        return None

    win = max(5, int(0.03 * n))
    scores = np.full(n, -np.inf)
    for i in range(win, n - win):
        t_i = float(T[i])
        if exclude is not None and exclude[0] <= t_i <= exclude[1]:
            continue
        before = float(np.mean(y[i - win : i]))
        after = float(np.mean(y[i : i + win]))
        step = abs(after - before)
        local = y[max(0, i - 2 * win) : min(n, i + 2 * win)]
        noise = float(np.std(np.diff(local))) if local.size > 2 else 0.0
        scores[i] = step / (noise + 1e-12)

    if not np.any(np.isfinite(scores)):
        return None

    best = int(np.argmax(scores))

    # A step is only a glass transition if it is a meaningful fraction of the
    # overall signal excursion. Without this test the routine always returns
    # *something*, so a sample with no glass transition (a pure melting trace)
    # gets a fabricated Tg drawn from residual curvature.
    before = float(np.mean(y[max(0, best - win) : best]))
    after = float(np.mean(y[best : best + win]))
    step_size = abs(after - before)
    total_range = float(np.max(y) - np.min(y))
    if total_range <= 0:
        return None
    if step_size / total_range < _MIN_TG_STEP_FRACTION:
        return None
    return best


def _find_peak_temperature(T: np.ndarray, y: np.ndarray) -> int | None:
    """
    Index of the most prominent *peak* (a transient excursion that returns to
    the baseline), used to locate melting and crystallisation events.

    Found on the residual after subtracting a straight line joining the ends
    of the scan, which removes the sloping baseline that a heat-capacity step
    would otherwise contribute and prevents that step from being read as a
    peak.
    """
    n = T.size
    if n < 5:
        return None
    base = np.linspace(float(y[0]), float(y[-1]), n)
    excess = y - base
    return int(np.argmax(excess))


def inflection_temperature(
    temperature: Sequence[float], signal: Sequence[float]
) -> float | None:
    """
    Temperature of the maximum first derivative, which for a DSC trace is the
    inflection point of the step and identifies Tg when the step is narrow.
    """
    xa, ya = _clean_curve(temperature, signal, "temperature", "signal")
    dy = np.abs(np.gradient(ya, xa))
    return float(xa[int(np.argmax(dy))])


def analyse_tga(
    temperature: Sequence[float],
    mass_pct: Sequence[float],
    smooth_window: int = 11,
    min_step_pct: float = 5.0,
) -> TGAResult:
    """
    Analyse a TGA trace given as (temperature / mass percent remaining).

    Reports Td at 5 % and 10 % mass loss, the DTG peak temperature, the
    residue at the end of the run, and the individual decomposition steps
    whose mass loss exceeds ``min_step_pct``.
    """
    T, m = _clean_curve(temperature, mass_pct, "temperature", "mass_pct")
    if np.any(np.diff(T) <= 0):
        # Duplicate temperature points are legal in instrument exports; keep
        # the first occurrence so the derivative stays finite.
        keep = np.concatenate(([True], np.diff(T) > 0))
        T, m = T[keep], m[keep]
    if T.size < 3:
        raise ValueError("The TGA trace needs at least 3 distinct temperatures.")

    m_smooth = _smooth(m, smooth_window)
    # DTG in %/degC: rate of mass loss, reported positive for a loss.
    dtg = -np.gradient(m_smooth, T)

    Td5 = _temperature_at_fraction(T, m_smooth, 5.0)
    Td10 = _temperature_at_fraction(T, m_smooth, 10.0)
    T95 = _temperature_at_fraction(T, m_smooth, 95.0)
    idx_peak = int(np.argmax(dtg))
    T_peak = float(T[idx_peak]) if dtg.size else None
    residue = float(m_smooth[-1])

    # Detect discrete steps as contiguous regions where the mass falls by
    # more than a threshold, separated by plateaus.
    steps: list[dict[str, float]] = []
    dm = np.diff(m_smooth)
    losing = dm < -0.01
    i = 0
    while i < losing.size:
        if losing[i]:
            j = i
            while j + 1 < losing.size and losing[j + 1]:
                j += 1
            loss = float(m_smooth[i] - m_smooth[j + 1])
            if loss >= min_step_pct:
                steps.append(
                    {
                        "onset_C": float(T[i]),
                        "end_C": float(T[j + 1]),
                        "loss_pct": loss,
                    }
                )
            i = j + 1
        else:
            i += 1

    return TGAResult(
        Td_5pct=Td5,
        Td_10pct=Td10,
        T_max_rate=T_peak,
        T_95pct=T95,
        residue_pct=residue,
        steps=steps,
        temperature=[float(v) for v in T],
        mass_pct=[float(v) for v in m_smooth],
        dtg=[float(v) for v in dtg],
    )


def analyse_dsc(
    temperature: Sequence[float],
    heat_flow: Sequence[float],
    heating_rate: float | None = None,
    ref_enthalpy_J_g: float | None = None,
    smooth_window: int = 11,
) -> DSCResult:
    """
    Analyse a DSC trace.

    Parameters
    ----------
    temperature : sequence
        Program temperature in degrees Celsius.
    heat_flow : sequence
        Heat flow in W/g (or mW normalised by mass).
    heating_rate : float, optional
        Program rate in K/min. Required to convert an enthalpy in J/g into a
        delta-Cp in J/(g.K) across the glass transition.
    ref_enthalpy_J_g : float, optional
        Enthalpy of fusion of a 100 % crystalline reference of the same
        polymer, in J/g. When given, the degree of crystallinity is computed
        per ASTM D3418 / ISO 11357-3 as
        ``Xc = 100 * delta_Hm / ref_enthalpy_J_g``.

    Notes
    -----
    Endothermic events are assumed to point upward in the supplied signal,
    which is the convention for a heat-flow DSC trace after sign correction.
    Glass transition is reported by the ASTM D3418 midpoint construction.
    """
    T, hf = _clean_curve(temperature, heat_flow, "temperature", "heat_flow")
    hf_s = _smooth(hf, smooth_window)

    result = DSCResult(
        Tg=None,
        Tg_onset=None,
        Tg_end=None,
        delta_cp=None,
        Tm=None,
        delta_Hm=None,
        Tc=None,
        delta_Hc=None,
        crystallinity_pct=None,
        temperature=[float(v) for v in T],
        heat_flow=[float(v) for v in hf_s],
    )

    # ---- Melting endotherm (found first: it defines what to exclude) --------
    # The melting peak is the largest transient excursion above the baseline
    # joining the ends of the scan.
    tm_idx = _find_peak_temperature(T, hf_s)
    melt_range: tuple[float, float] | None = None
    if tm_idx is not None:
        result.Tm = float(T[tm_idx])

        # Enthalpy by integrating the excess over the straight baseline.
        base = np.linspace(float(hf_s[0]), float(hf_s[-1]), T.size)
        excess = hf_s - base
        peak_h = float(excess[tm_idx])
        pos = excess > 0
        if pos.any() and peak_h > 0:
            # Restrict to the contiguous region around the peak so that a
            # separate event elsewhere does not contribute to this enthalpy.
            a = tm_idx
            while a > 0 and excess[a] > 0:
                a -= 1
            b = tm_idx
            while b < T.size - 1 and excess[b] > 0:
                b += 1
            if b > a + 1:
                area = float(np.trapezoid(excess[a : b + 1], T[a : b + 1]))
                if heating_rate:
                    # W/g integrated over degC, divided by the rate in K/s,
                    # gives J/g. This is exact only when the x-axis is time,
                    # which is why the rate is required.
                    area = area / (heating_rate / 60.0)
                result.delta_Hm = abs(area)
                if ref_enthalpy_J_g and ref_enthalpy_J_g > 0:
                    result.crystallinity_pct = 100.0 * result.delta_Hm / ref_enthalpy_J_g
            melt_range = (float(T[a]), float(T[b]))

    # ---- Glass transition ---------------------------------------------------
    # Searched on the signal with the melting region excluded, using the
    # step-level discriminator so that a melting peak is never reported as Tg.
    # ASTM D3418 locates Tg from the step, not from the maximum slope.
    tg_idx = _find_step_temperature(T, hf_s, exclude=melt_range)
    if tg_idx is not None:
        t_g_step = float(T[tg_idx])
        # Onset and end by the tangent construction on the step.
        n_base = max(3, int(0.10 * T.size))
        pre = float(np.mean(hf_s[:n_base]))
        post = float(np.mean(hf_s[-n_base:]))
        slope = float(np.gradient(hf_s, T)[tg_idx])

        if slope != 0:
            # ASTM D3418: the extrapolated onset is the intersection of the
            # tangent at the inflection with the pre-transition baseline, and
            # the end is the intersection with the post-transition baseline.
            onset = t_g_step + (pre - float(hf_s[tg_idx])) / slope
            end = t_g_step + (post - float(hf_s[tg_idx])) / slope
            lo_t, hi_t = min(T[0], T[-1]), max(T[0], T[-1])
            if lo_t <= onset <= hi_t:
                result.Tg_onset = float(onset)
            if lo_t <= end <= hi_t:
                result.Tg_end = float(end)

        if result.Tg_onset is not None and result.Tg_end is not None:
            # ASTM D3418 midpoint convention.
            result.Tg = 0.5 * (result.Tg_onset + result.Tg_end)
        else:
            result.Tg = t_g_step

        if heating_rate:
            result.delta_cp = (post - pre) / (heating_rate / 60.0)

    return result
