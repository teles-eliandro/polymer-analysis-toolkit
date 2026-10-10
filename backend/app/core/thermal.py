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
from contextvars import ContextVar
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

#: Half-width, in kelvin, within which a reported glass transition is treated
#: as stable enough to quote. Between laboratories, DSC Tg values for the same
#: polymer commonly scatter by several degrees, so demanding better than this
#: would flag good data; and the resampling spread measured on the real ABS
#: trace at realistic noise is 7-14 K, which must be flagged. 2.5 K sits below
#: the scatter between operators and well under that failure mode.
_TG_RELIABLE_TOLERANCE_C = 2.5

#: Set while _tg_footing re-runs the analysis. The footing cannot be computed
#: inside its own resamples -- the call recurses without bound -- so the work
#: is switched off for the duration. A ContextVar rather than a plain flag so
#: concurrent analyses do not see each other's state.
_no_footing: ContextVar[bool] = ContextVar("_no_footing", default=False)

#: How symmetric the slopes either side of a candidate must be for it to count
#: as a step rather than the flank of a peak. A glass transition changes the
#: baseline level once, so the trace approaches and leaves it at comparable
#: rates; one wall of a melting peak does not.
#:
#: Measured on a semicrystalline trace (Tg 75 C, Tm 170 C), the slope ratio
#: either side of the true step is 0.99, while the best-scoring melting flank
#: reaches only 0.35 no matter how the window is sized (0.12 at 12 C, 0.20 at
#: 18 C, 0.31 at 24 C). Half sits in the empty gap between the two clusters.
#: Do not lower this to 0.1-0.2: at those values a flank still passes and,
#: being 30x the size of the step, it wins the ranking outright.
_MIN_TG_SYMMETRY = 0.5

#: How far the classical slope peak must stand above the trace's own median
#: gradient to count as a transition. Guards the derivative-based candidate in
#: ``_derivative_peak``: on a featureless scan the largest slope and the median
#: slope are comparable, and the ratio falls near 1, so nothing is reported. A
#: real glass transition on the figshare 24462004 traces measures 15-60x the
#: median gradient.
_MIN_DERIV_SIGNIFICANCE = 3.0

#: How many samples the trace must leave a candidate extremum before it comes
#: back, for that extremum to count as a melting or crystallisation peak. This
#: is the half-width of the search neighbourhood in ``_find_peak_temperature``.
#: Three samples is the floor that rejects single-point instrument noise while
#: still accepting a sharp endotherm; the value is capped at an eighth of the
#: scan so that a very short trace is not left with no searchable interior.
_PEAK_ORDER = 12

#: Window, in degrees Celsius, over which a melting/crystallisation peak's
#: prominence is measured. The detector's own neighbourhood (``_PEAK_ORDER``) is
#: only a dozen samples wide -- enough to tell an apex from single-point noise,
#: but far too narrow to judge how big the event is. On the figshare 24462004
#: PLA trace the melting endotherm sits on a strong downward drift: within
#: +-0.8 C it stands only 1 % proud of its neighbours, while measured over the
#: physical width of the transition it is 35-47 % of the trace range. A melting
#: endotherm on a 10 K/min scan rises and returns over roughly ten degrees, so
#: the prominence window is set in degrees and converted to samples using the
#: trace's own sampling rate.
_PEAK_QUALIFY_WINDOW_C = 10.0

#: How much of a peak's own height must still be present *after* the event, for
#: the event to count as a peak rather than a step. ``_find_peak_temperature``
#: measures the level before the candidate and the level after it; a melting
#: endotherm comes back down towards the level it started from, while a glass
#: transition settles at a permanently new level. The ratio (apex - after) /
#: (apex - before) is near 1 for a clean peak and near 0 for a clean step, and
#: this floor is what accepts the former and rejects the latter.
#:
#: This gate exists because amplitude cannot do the job: on the figshare
#: 24462004 set the amorphous PS yields a *larger* peak prominence (0.378 of the
#: trace range) than the genuinely melting PET (0.165), so a threshold on size
#: alone invents a melting endotherm for a polymer that has none.
_MIN_PEAK_RETURN = 0.35

#: Minimum width, in degrees Celsius, for a slope peak to be accepted as a
#: glass transition by ``_derivative_peak``. A real glass transition keeps the
#: slope elevated across a degree or more; the cell-switching transient at the
#: start of a scan is one or two sample points wide and reaches a gradient over
#: 1000x the trace median. Width is what separates them.
_MIN_TG_WIDTH_C = 1.0

#: How much of the scan's range the start-to-end level change must be for the
#: trace to be treated as containing a step (a glass transition) rather than a
#: peak (a melting endotherm). A melting-only scan returns to its starting
#: level, so the change is 0; a scan with a glass transition ends at a
#: different level, measuring 0.15 or more of the range on the test cases.
_MIN_STEP_PERSISTENCE = 0.05

#: How large a melting endotherm must be, as a fraction of the trace's own
#: excursion, to be reported at all. Set from the figshare 24462004 set: real
#: melting peaks measure 40-95 % of their scan's range, while the false
#: positives produced by the chord residual on amorphous traces (polystyrene,
#: which has no melting at all) sit under 10 %. Without this floor an amorphous
#: sample reports a melting temperature, and that spurious melt_range then
#: excludes the region containing the real glass transition.
_MIN_PEAK_FRACTION = 0.15

#: Half-width, in sample points, of the window used to test that a candidate
#: melting peak actually has the shape of a peak (rising on one side, falling
#: on the other). Only the sign of the mean slope on each side is used, so a
#: generous window is fine and makes the test insensitive to single-point noise.
_PEAK_FLANK_POINTS = 30

#: How much of a candidate peak's own height must appear as a rise on its
#: leading side for it to count as a melting endotherm. A decaying transient
#: never rises, so the ratio is near zero; a real melting peak rises by roughly
#: its own height. 0.3 separates them with margin on both sides.
_MIN_PEAK_RISE = 0.3

#: Degrees Celsius added to each side of the melting range before it is used to
#: exclude candidates from the glass-transition search. The bound found by the
#: excess walk sits on the melting peak's own shoulder, so a candidate just
#: outside it is still on the flank. A fixed margin, because the flank width is
#: a property of the transition and not of the peak height.
_MELT_EXCLUDE_MARGIN_C = 5.0

#: Floor on the span used to judge whether a glass transition is significant,
#: as a fraction of the whole scan's excursion. Excluding a melting peak can
#: leave an almost flat background (0.09 W/g of a 3.0 W/g scan), and measuring
#: the step against that would let noise pass as a transition. A tenth keeps the
#: yardstick tied to the trace's real scale while still allowing a small Tg to
#: be judged against the step-like background rather than against a large peak.
_MIN_BACKGROUND_FRACTION = 0.1

#: Width of the averaging window, in degrees Celsius, used to detect the glass
#: transition step. A region of interest a few degrees wide: too narrow and a
#: single-point derivative measures noise (a 0.1 C window on the real PCL scan
#: made the slope test meaningless), too wide and a narrow transition is
#: smoothed into its surroundings.
_TG_WINDOW_C = 6.0

#: How far either side of a candidate the slopes are compared, in degrees.
#: This has to stay short. It exists to sample the local background just outside
#: the transition; widen it and it reaches across a whole melting peak and
#: averages the two walls together, so a point on one wall scores as symmetric
#: (a 37 C span did exactly that on a Gaussian peak of sigma 8 C).
_TG_SPAN_C = 12.0

#: Fraction of a melting peak's height below which the excess over the fitted
#: baseline is treated as baseline error rather than peak. Used to bound the
#: region that counts as "the melting peak", both for the enthalpy integral and
#: for the range the glass-transition search must avoid. A few percent keeps the
#: whole peak while releasing the flat stretches of a scan where the local
#: baseline simply sits a little low.
_PEAK_FLOOR = 0.03


#: How much larger than the trace's own background variation a downward
#: excursion must be to count as cold crystallisation. The bound suppresses Tg
#: candidates at or above the peak, so a false positive is costly: it would
#: hide a real glass transition. The two events differ by more than an order of
#: magnitude on the traces that motivated the test (a 0.7 W/g crystallisation
#: peak against a 0.02 W/g glass-transition step), so a floor of 8 is
#: comfortably clear of both and still keeps instrument noise from qualifying.
_MIN_COLD_CRYST_SIGNIFICANCE = 8.0

#: Cold crystallisation cannot occur within this many degrees of the start of
#: the scan: the sample must first be heated through its glass transition. A
#: "peak" that close to the start is the cell-settling transient.
_COLD_CRYST_MIN_MARGIN_C = 10.0

#: Widest a cold-crystallisation peak may be, in degrees, measured at half its
#: height. It is a transition, so it is narrow; a melting ramp is not. Real
#: events in the PLLA dataset measured 3.5-4.3 C against 39 C for the melting
#: ramp that this test exists to exclude, so the threshold sits in a wide gap.
_MAX_COLD_CRYST_WIDTH_C = 15.0


#: Confidence levels attached to a reported value. The point of the ladder is
#: that the *nature* of the claim is visible, not just its number, so a reader
#: can tell "this is a property of the file" from "this is my guess".
#:
#: ``READ``    -- a property of the input file or a deterministic transform of
#:               it (time axis, sample mass, programmed method, the plotted
#:               curve). Not an interpretation; there is nothing to disagree
#:               with.
#: ``FORMULA`` -- a published formula applied to a declared input (enthalpy by
#:               integration, crystallinity from a reference enthalpy, Mw from
#:               intrinsic viscosity). Reproducible: cite the formula and the
#:               integration bounds and any competent analyst gets the same
#:               number back.
#: ``SUGGESTED`` -- an inference from the shape of the trace. This is the
#:               transition identification, and on the figshare 24462004 set it
#:               is wrong often enough that it must never be presented as a
#:               measurement. Carries the evidence that produced it.
READ = "read"
FORMULA = "formula"
SUGGESTED = "suggested"

#: Ordering for the ladder, so callers can compare or sort by confidence.
_CONFIDENCE_RANK = {READ: 0, FORMULA: 1, SUGGESTED: 2}


@dataclass
class FieldClaim:
    """A reported value together with why the reader should believe it.

    ``value`` is the number as reported (may be ``None`` when the analysis
    declined to answer). ``confidence`` is one of ``READ``/``FORMULA``/
    ``SUGGESTED``. ``evidence`` is the short list of measured facts that
    produced the value -- for a suggested transition, the observations that
    make it a candidate at all. ``note`` carries the caveat a reader needs to
    act correctly on it.
    """

    value: float | None = None
    confidence: str = SUGGESTED
    evidence: list[str] = field(default_factory=list)
    note: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "note": self.note,
        }


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
    #: Mass lost that no reported step accounts for, in percent. Non-zero when
    #: a decomposition is spread so thinly that its rate never stands out
    #: against the noise, so it cannot be separated into a step. Reporting it
    #: is the point: silently dropping it makes the steps look
    #: authoritative when they are not the whole story.
    unattributed_loss_pct: float = 0.0
    #: Human-readable notes about what the analysis could and could not
    #: resolve. Never empty in the pathological cases.
    notes: list[str] = field(default_factory=list)
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
            "unattributed_loss_pct": self.unattributed_loss_pct,
            "notes": self.notes,
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
    #: Why a crystallinity was not reported even though a reference enthalpy
    #: was supplied. Set when the computed value exceeded 100 %, which is
    #: physically impossible and means the reference does not match the
    #: sample. Reporting the impossible number would be worse than reporting
    #: nothing, so the field above stays None and the reason lives here.
    crystallinity_refusal: str | None = None
    #: How much the reported Tg moves when the trace is resampled, in K. This
    #: is the method's own sensitivity to the sampling of *this* trace -- not
    #: an accuracy claim against a certified reference, which would need one.
    #: None when no Tg was found.
    Tg_uncertainty_C: float | None = None
    #: True when Tg is stable to better than Tg_RELIABLE_TOLERANCE_C. A
    #: researcher should treat a False value as "not publishable as a number"
    #: and go back to the instrument, not as a slightly worse value.
    Tg_reliable: bool | None = None
    #: Curve data for plotting.
    temperature: list[float] = field(default_factory=list)
    heat_flow: list[float] = field(default_factory=list)
    #: Warming steps applied and which one the results came from.
    direction: str = "heating"
    #: Per-transition claims with their confidence and supporting evidence.
    #: Keys are the field names above ("Tg", "Tm", "delta_Hm", ...). Anything
    #: absent from this mapping was not reported at all. This is the honest
    #: interface: the bare floats above are the numbers, these say what they
    #: are worth. See ``FieldClaim``.
    claims: dict[str, FieldClaim] = field(default_factory=dict)

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
            "crystallinity_refusal": self.crystallinity_refusal,
            "Tg_uncertainty_C": self.Tg_uncertainty_C,
            "Tg_reliable": self.Tg_reliable,
            "temperature": self.temperature,
            "heat_flow": self.heat_flow,
            "direction": self.direction,
            "claims": {k: v.as_dict() for k, v in self.claims.items()},
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


def _uniform_grid(
    T: np.ndarray, m: np.ndarray, step_c: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """
    Resample a trace onto a uniform temperature grid before differentiating.

    Instrument exports are unevenly spaced (here, intervals from 0.008 to
    0.29 degC), and a finite difference on an uneven axis is dominated by the
    short intervals: one noisy pair a hundredth of a degree apart yields a
    gradient of tens of percent per degree. Resampling to a fixed step makes
    the derivative comparable along the trace, at the cost of the resolution
    below ``step_c``, which a TGA cannot meaningfully resolve anyway.
    """
    if T.size < 2:
        return T, m
    step = max(float(step_c), (T[-1] - T[0]) / max(m.size - 1, 1))
    grid = np.arange(T[0], T[-1] + step * 0.5, step)
    if grid.size < 2:
        return T, m
    return grid, np.interp(grid, T, m)


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


def _local_baseline(T: np.ndarray, y: np.ndarray, peak_idx: int) -> np.ndarray:
    """
    Straight line through the signal *outside* the melting peak, which is the
    baseline a DSC analyst draws by hand.

    Why this matters: a straight line joining the two ends of the whole scan
    is not the peak baseline, because the heat capacity of the sample rises
    with temperature and the signal drifts. Integrating against the end-to-end
    chord then includes that drift as if it were melting enthalpy, and the
    result can exceed the enthalpy of a fully crystalline sample - which is
    physically impossible and is the clearest signal that the baseline is
    wrong.

    Measured on a real DSC scan of commercial polycaprolactone (Zenodo
    10.5281/zenodo.17293641, 10 K/min), the end-to-end chord gave
    340 J/g while a local baseline gave 77.5 J/g; the enthalpy of a 100 %
    crystalline PCL is 139.5 J/g, so the first value is impossible and the
    second is consistent with the published crystallinity of 40-55 %.

    The baseline is fitted on the regions flanking the peak, taken as the
    outer tenth of the scan on each side of the peak plus any part of the
    trace more than 30 K away from it, which excludes the transition itself.
    """
    n = T.size
    peak_T = float(T[peak_idx])
    # Points clearly outside the transition: more than 30 K from the peak, or
    # in the outer tenths of the scan.
    flank = np.abs(T - peak_T) > 30.0
    outer = np.zeros(n, dtype=bool)
    k = max(1, n // 10)
    outer[:k] = True
    outer[-k:] = True
    mask = flank | outer
    # A linear fit needs at least three points; fall back to the outer tenths.
    if mask.sum() < 3:
        mask = outer
    if mask.sum() < 3:
        return np.linspace(float(y[0]), float(y[-1]), n)

    try:
        coef = np.polyfit(T[mask], y[mask], 1)
    except (np.linalg.LinAlgError, ValueError):
        return np.linspace(float(y[0]), float(y[-1]), n)

    baseline = np.polyval(coef, T)
    # The baseline must not exceed the signal anywhere on the flanks, which
    # would mean the fit drifted above the data.
    if np.any(baseline[mask] > y[mask] + 0.5 * (float(np.max(y)) - float(np.min(y)))):
        return np.linspace(float(y[0]), float(y[-1]), n)
    return baseline


def _plateau_levels(
    T: np.ndarray, y: np.ndarray, tg_idx: int, width: float
) -> tuple[float, float]:
    """
    Levels of the two plateaus that flank a transition, used to measure the
    step height across it.

    The step must be read between the plateaus *adjacent* to the transition,
    not between the ends of the scan. Averaging the outer tenths of a scan
    includes whatever slope and instrument drift the trace carries: on a
    synthetic step of exactly 0.5 W/g carrying a linear drift of only
    0.0009 W/g/K, the end-to-end method returned 2.47 J/(g.K) against a true
    1.5 -- a 65 % error caused entirely by the drift, since the baseline at
    0 C and at 400 C are not the same level.

    ``width`` is the half-width of the window in degrees, taken from the
    measured width of the transition itself so that a narrow transition gets
    narrow windows and a broad one gets wide ones.
    """
    span = float(T[-1] - T[0])
    if span <= 0:
        return float(y[0]), float(y[-1])

    # Keep each plateau window inside the scan but clear of the transition.
    gap = max(width, 0.02 * span)
    half = max(width, 0.03 * span)
    t0, t1 = float(T[0]), float(T[-1])
    t_tg = float(T[tg_idx])

    lo_hi = t_tg - gap
    lo_lo = max(t0, lo_hi - half)
    hi_lo = t_tg + gap
    hi_hi = min(t1, hi_lo + half)

    lo_mask = (T >= lo_lo) & (T <= lo_hi)
    hi_mask = (T >= hi_lo) & (T <= hi_hi)
    if not lo_mask.any() or not hi_mask.any():
        return float(y[0]), float(y[-1])

    pre = float(np.mean(y[lo_mask]))
    post = float(np.mean(y[hi_mask]))
    return pre, post


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


def _step_at(T: np.ndarray, y: np.ndarray, i: int, win: int) -> float:
    """Size of the level change at index *i*, measured over +/-*win* points."""
    n = T.size
    before = float(np.mean(y[max(0, i - win) : i]))
    after = float(np.mean(y[i : min(n, i + win)]))
    return abs(after - before)


def _derivative_peak(
    T: np.ndarray,
    y: np.ndarray,
    exclude: tuple[float, float] | None = None,
    below: float | None = None,
) -> int | None:
    """Index of the fastest change of slope in the trace: the classical Tg.

    The glass transition is where the heat flow changes slope most abruptly, so
    it sits at the largest peak of ``|d(hf)/dT|``. This is the textbook
    construction and it is used here as a candidate to complement the
    window-mean ranking, which fails on traces that drift (see the caller).

    The scan opens and closes with the cell settling, and that transient is the
    largest slope change anywhere in the trace, so the first and last 5 % are
    skipped -- the same guard the window-mean search uses. ``exclude`` removes
    the melting range. The result is reported only when the slope peak stands
    clearly above the trace's own background gradient, so a featureless scan
    cannot yield a transition.
    """
    n = T.size
    if n < 20:
        return None

    grad = np.abs(np.gradient(y, T))
    margin = max(5, int(0.05 * n))
    lo, hi = margin, n - margin
    if hi <= lo:
        return None

    window = grad[lo:hi]
    if exclude is not None:
        inside = (T[lo:hi] >= exclude[0]) & (T[lo:hi] <= exclude[1])
        window = np.where(inside, 0.0, window)
    if not np.any(window > 0):
        return None

    # The start-of-scan transient is a single narrow spike: the cell is
    # switched on and the signal jumps, producing the largest gradient in the
    # whole trace. On the figshare 24462004 polystyrene trace it measures
    # 1115x the median gradient at 0.1 C while the real glass transition at
    # 105 C measures 21x -- so ranking by magnitude alone always picks the
    # transient. A margin in points is no defence: the transient sits at 0 C,
    # which on a -90..270 C scan is a quarter of the way in, well past any
    # 5 % guard.
    #
    # A real glass transition is a *wide* feature: the slope stays elevated
    # across several degrees. The switching transient is one or two points
    # wide. Measuring how far the gradient stays above half its peak separates
    # the two, so the search is restricted to candidates of physical width.
    peak = float(np.max(window))
    background = float(np.median(grad[lo:hi]))
    if background > 0 and peak / background < _MIN_DERIV_SIGNIFICANCE:
        return None
    if peak <= 0:
        return None

    # Anything this far above the background is a candidate; the threshold is
    # tied to the noise floor rather than to the strongest peak, because a
    # switching transient can be 50x the real transition and would otherwise
    # clip the search to itself.
    floor = max(background * _MIN_DERIV_SIGNIFICANCE, peak * 1e-3)
    order = np.argsort(window)[::-1]
    for k in order:
        if window[k] < floor:
            break
        i = lo + int(k)
        # Never report a point inside the excluded (melting) range. Zeroing the
        # gradient there and taking the global argmax was not enough: the
        # largest of the *remaining* values sits on the edge of the exclusion,
        # on the melting flank, which is exactly what the exclusion exists to
        # avoid. On the figshare 24462004 PET trace (Tg 78 C, Tm 237 C) that
        # returned 257 C -- the far shoulder of the melting peak.
        if exclude is not None and exclude[0] <= float(T[i]) <= exclude[1]:
            continue
        # The classical Tg construction is a candidate like any other, so it
        # obeys the same physical ordering: above the cold-crystallisation peak
        # the amorphous phase is gone and there is no glass transition left to
        # find. Filtering only the window-mean search would leave this path --
        # which is the one that wins on a trace with a strong cold-
        # crystallisation event -- free to return the impossible answer.
        if below is not None and float(T[i]) >= below:
            continue
        # Width at half of *this candidate's* height, not of the global peak.
        half = window[k] * 0.5
        left = i
        while left > lo and grad[left - 1] >= half:
            left -= 1
        right = i
        while right < hi - 1 and grad[right + 1] >= half:
            right += 1
        if float(T[right] - T[left]) >= _MIN_TG_WIDTH_C:
            candidate_ok = i if np.isfinite(grad[i]) else None
        else:
            continue
        if candidate_ok is not None and _is_step_not_peak(T, y, candidate_ok):
            return candidate_ok
    return None


def _find_cold_crystallisation(
    T: np.ndarray, y: np.ndarray, tm_idx: int | None
) -> float | None:
    """Temperature of the cold-crystallisation peak, if the trace shows one.

    On heating, a quenched or amorphous sample passes through the glass
    transition, may then crystallise (exothermic, so a *downward* excursion in
    the endothermic-up convention) and only then melts. D. Dean, "Differential
    Scanning Calorimetry" (Univ. of Alabama at Birmingham), slide 29, gives
    this sequence as the standard set of events in a DSC trace; slide 28
    defines cold crystallisation as the exothermic transition on heating from a
    solid amorphous state to a solid crystalline one.

    Returning the *temperature* rather than the index lets the caller use it as
    an upper bound: a glass transition must lie below it, so everything at or
    above it is not a Tg candidate.

    The peak is looked for only between the start of the scan and the melting
    peak, and only where it is a real excursion rather than noise: the
    downward step must be a meaningful fraction of the trace's own background
    variation. A trace with no cold crystallisation returns ``None``, which
    leaves the caller's behaviour unchanged -- this constraint can only remove
    candidates, never invent one.

    Note the sign convention is load-bearing. A DSC exported "exothermic up"
    shows cold crystallisation as an upward excursion and melting as downward;
    ``_clean_curve`` normalises to endothermic-up before this runs, so the
    downward test below is correct for both.
    """
    n = T.size
    if n < 20:
        return None

    lo = max(0, int(0.05 * n))
    hi = n - int(0.05 * n)
    if tm_idx is not None:
        # Cold crystallisation precedes melting, so nothing at or beyond the
        # melting peak can be it.
        hi = min(hi, tm_idx)
    if hi <= lo + 1:
        return None

    seg_T = T[lo:hi]
    seg_y = y[lo:hi]

    # Detrend before looking for the excursion. A cold-crystallisation peak sits
    # on a sloping heat-capacity background, and on a trace whose baseline
    # merely slopes downward the deepest point is then simply the lowest end --
    # not an event. Without this the detector fired on a clean synthetic trace
    # whose only feature is a glass-transition step (the baseline runs from
    # -0.133 to +0.09 W/g across the scan), and the resulting bound suppressed
    # the real Tg: 0 of 12 detections. Fit and remove a straight line so what
    # remains is the shape, not the slope.
    if seg_y.size > 2:
        coeffs = np.polyfit(seg_T, seg_y, 1)
        seg_y = seg_y - np.polyval(coeffs, seg_T)

    # A downward excursion: negate so a peak finder can be used directly.
    depth = -seg_y
    peak = float(np.max(depth))
    if peak <= 0:
        return None

    # Significance against the trace's own background. The glass transition is
    # a step of a few hundredths of a W/g; a genuine cold-crystallisation peak
    # on the traces that caused this problem was 0.7 W/g, more than an order of
    # magnitude larger. The floor keeps instrument noise from being read as an
    # event, because a spurious bound here would silently suppress a real Tg.
    background = float(np.percentile(np.abs(np.diff(seg_y)), 90)) if seg_y.size > 2 else 0.0
    if background > 0 and peak / background < _MIN_COLD_CRYST_SIGNIFICANCE:
        return None

    i = int(np.argmax(depth))
    t_peak = float(seg_T[i])

    # The event must be a localised excursion, not one wall of the melting ramp
    # or one end of a monotone drift. Requiring the signal to come back up on
    # BOTH sides is what distinguishes a genuine exotherm from a step's
    # shoulder. Testing only one side was not enough: on the clean synthetic
    # trace (a Tg step at 85 C and a wide melting ramp at 170 C) the descending
    # wall of the melting ramp satisfied it and a bound at 161 C was returned,
    # which then suppressed the real Tg.
    pad = max(3, min(50, len(seg_y) // 4))
    if not (pad < i < len(seg_y) - pad):
        return None
    before = float(np.mean(seg_y[i - pad : i]))
    after = float(np.mean(seg_y[i + 1 : i + 1 + pad]))
    here = float(seg_y[i])
    if not (before > here and after > here):
        return None

    # The excursion must also be *narrow*. Cold crystallisation is a transition:
    # a peak a few degrees wide, not a ramp. The width at half maximum separates
    # it from the other broad features of a scan that can look like a minimum,
    # and the gap is wide rather than marginal. Measured:
    #     real cold crystallisation (PLLA 10K/25K/50K):  3.5, 4.3, 4.1 C
    #     the melting ramp of the clean synthetic trace: 39.2 C
    # Without this test that ramp was accepted and produced a bound at 161 C,
    # which suppressed the real glass transition at 85 C on a trace that has no
    # cold crystallisation at all.
    half = peak / 2.0
    a = i
    while a > 0 and depth[a] > half:
        a -= 1
    b = i
    while b < depth.size - 1 and depth[b] > half:
        b += 1
    width = float(seg_T[b] - seg_T[a])
    if width > _MAX_COLD_CRYST_WIDTH_C:
        return None

    # Guard the physically impossible: cold crystallisation sits between the
    # glass transition and melting. A "peak" within a few degrees of the start
    # of the scan is the cell-settling transient, which is not an event.
    if t_peak - float(T[0]) < _COLD_CRYST_MIN_MARGIN_C:
        return None
    return t_peak


def _is_step_not_peak(T: np.ndarray, y: np.ndarray, i: int) -> bool:
    """Whether the signal at *i* settles at a new level (a step) or returns.

    This is the test that separates a glass transition from a melting peak once
    both have passed the magnitude and shape gates. Width does not do it: on
    synthetic traces a melting Gaussian and a tanh glass transition of the same
    height measure comparable half-widths (12.8 C against 14.0 C), so a width
    threshold cannot tell them apart.

    What does is where the signal ends up. A glass transition is a step: the
    level before it and the level after it differ. A melting endotherm is a
    peak: the signal comes back, so the scan finishes at the level it started.
    Measured on those same two traces:
        melting only ->  starts 0.500, ends 0.500   (|end - start| = 0.0000)
        Tg only      ->  starts 0.200, ends 1.000   (|end - start| = 0.8000)

    The start and end levels are medians over a tenth of the scan each, which is
    robust to the settling transient at the very beginning.
    """
    n = T.size
    span = max(5, n // 10)
    start = float(np.median(y[:span]))
    end = float(np.median(y[-span:]))
    full_range = float(np.max(y) - np.min(y))
    if full_range <= 0:
        return False
    return abs(end - start) / full_range >= _MIN_STEP_PERSISTENCE

def _find_step_temperature(
    T: np.ndarray,
    y: np.ndarray,
    exclude: tuple[float, float] | None = None,
    below: float | None = None,
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

    Two details matter on a real trace, both learned from a DSC scan of ABS
    (figshare 10.6084/m9.figshare.24462004) whose glass transition is at
    105.8 C but which was originally reported as having no Tg at all:

    * The search skips the first and last 5 % of the scan. A DSC run opens
      with the cell still settling, and that transient is the largest
      level-change anywhere in the trace -- on the ABS scan it is larger than
      the glass transition itself. Left in, it is always chosen.
    * Candidates are ranked by the size of the step, not by step over noise.
      Ranking by step/noise picks the flattest region of the trace, where the
      noise is smallest and a negligible step therefore scores highest: on the
      ABS scan it selected 46.6 C (step 0.000075) over the real transition at
      105.8 C (step 0.000171, 2.3x larger). The noise term then rejected it as
      too small a fraction of the signal, and the routine returned None. Noise
      belongs as a significance floor, not in the denominator.

    ``exclude`` optionally removes a temperature range (the melting region)
    from consideration.
    """
    n = T.size
    if n < 20:
        return None

    # Window sizes are set in degrees, then converted to points. Sizing them as
    # a fraction of the point count makes them depend on the sampling rate: a
    # trace with 6846 points over 226 C (the real PCL scan) gets a 0.1 C window,
    # which is a single-point derivative where the symmetry test measures noise
    # rather than the shape of the transition. A glass transition is a few
    # degrees wide whatever the instrument's sampling rate.
    dT = float(T[-1] - T[0])
    span = abs(dT) if dT != 0 else 1.0
    per_deg = n / span
    win = int(np.clip(round(_TG_WINDOW_C * per_deg), 5, max(5, n // 4)))
    far = int(np.clip(round(_TG_SPAN_C * per_deg), win, max(win, n // 3)))
    margin = max(win, int(0.05 * n))
    scores = np.full(n, -np.inf)

    # The gradient of the whole trace is a constant of this call, but it used
    # to be computed *inside* the loop below, once per candidate index: on a
    # 16202-point scan that is ~16000 np.gradient calls of 16000 points each,
    # which is where 36 of the 38 seconds per `.tri` file went (cProfile:
    # 11795 calls, 1.9 s self time, 34 s cumulative). Hoisting it changes no
    # arithmetic -- the same array, the same indexing -- and takes the whole
    # analysis from 38 s to 2.7 s per file.
    grad = np.gradient(y, T)

    for i in range(win, n - win):
        if i < margin or i > n - margin:
            continue
        t_i = float(T[i])
        if exclude is not None and exclude[0] <= t_i <= exclude[1]:
            continue
        # A glass transition cannot lie at or above the cold-crystallisation
        # peak: by then the amorphous phase that produces the step has
        # crystallised. See the call site for the measurement that motivates
        # this.
        if below is not None and t_i >= below:
            continue
        before = float(np.mean(y[i - win : i]))
        after = float(np.mean(y[i : i + win]))
        step = abs(after - before)

        # Reject the flank of a peak. The level change across a melting flank
        # is large -- on a semicrystalline trace it measures ~32x the glass
        # transition -- so ranking by step size alone picks the melting flank
        # over the real Tg and reports a transition 100 C too high.
        #
        # What separates them is symmetry. A glass transition is a single,
        # one-time change of level, so the trace rises into it and flattens out
        # of it at comparable rates: the slope over a window on each side comes
        # out of similar size. A peak flank is one wall of a transient event:
        # the trace is steep on the side facing the peak and nearly flat on the
        # other, and the two slopes differ by an order of magnitude.
        #
        # Measured on the semicrystalline trace below (Tg 75 C, Tm 170 C):
        # the true step gives slopes 0.00061 / 0.00060 (ratio 0.99), while the
        # melting flank at 175.7 C gives 0.00421 / 0.06217 (ratio 0.07) and the
        # best flank of the peak never exceeds 0.35 however the window is sized.
        #
        # The slopes are measured over the whole trace, NOT clipped to the
        # excluded range. Clipping cuts the window off at the edge of the
        # exclusion, so only the flat side of a peak wall is sampled and the
        # wall looks like a symmetric step -- which is how a fabricated Tg at
        # 139.7 C survived on a trace that is nothing but a melting peak.
        lo = max(0, i - far)
        hi = min(n, i + far)
        pre_slope = abs(float(np.mean(grad[lo : max(lo + 1, i - win)])))
        post_slope = abs(float(np.mean(grad[min(i + win, hi) : hi])))
        big = max(pre_slope, post_slope)
        small = min(pre_slope, post_slope)
        if big > 0 and small / big < _MIN_TG_SYMMETRY:
            continue

        # Rank by how abrupt the change is, not by its size alone.
        #
        # Symmetry alone is not sufficient. The *centre* of a tanh-shaped ramp
        # -- which is what a real melting transition looks like, not a Gaussian
        # -- has equal slopes on both sides, so it scores ~0.99 symmetric and
        # passes the test above. On a PLLA-like trace (Tg 85 C, Tm 170 C) that
        # let the melting ramp be reported as the Tg at 166-170 C: its step
        # over the 6 C window is larger than the glass transition's, so it won
        # the ranking outright.
        #
        # What separates them is abruptness. A glass transition changes level
        # over a degree or two; a melting ramp spreads over many. Measured on
        # that trace: the true Tg reaches a local gradient of 0.0200 W/g/K
        # while the melting ramp peaks at 0.0047 -- a factor of 4.3 -- even
        # though the ramp's *step* is 1.9x the step's.
        #
        # A change spread evenly over the averaging window has gradient
        # step / window; the ratio of the actual gradient to that is how much
        # sharper than "evenly spread" the transition is. Ranking by
        # step * sharpness puts the Tg first on that trace by 4.2x.
        win_span = abs(float(T[min(i + win, n - 1)] - T[i - win]))
        even_grad = step / win_span if win_span > 0 else 0.0
        local_grad = abs(float(grad[i]))
        sharpness = local_grad / even_grad if even_grad > 0 else 1.0
        scores[i] = step * sharpness

    if not np.any(np.isfinite(scores)):
        return None

    best = int(np.argmax(scores))

    # The window-mean ranking above is not sufficient on real traces.
    #
    # On the figshare 24462004 set it recovers the glass transition of PS
    # (step/noise 0.99 symmetric) but rejects PVC, PC and ABS outright: their
    # traces carry a strong baseline slope, so the window *before* the
    # transition also has a large gradient from the instrument drift alone and
    # the symmetry test -- which exists to reject a melting flank -- rejects
    # the glass transition instead. Measured symmetry at the true Tg:
    #     PS 0.99 (passes)   PC 0.39   PVC 0.29   ABS 0.16   (all rejected)
    # Detrending does not fix it either (PVC falls to 0.14).
    #
    # What does find all four is the classical construction: the glass
    # transition is where the *slope* of the trace changes fastest, i.e. the
    # peak of |d(hf)/dT|. Measured on the same traces it lands at
    #     PS 102-107   PVC 82-86   PC 144-150   ABS 100-102
    # against published values of 100, 80, 147 and 105 C.
    #
    # So the derivative peak is used as a *candidate* rather than as the
    # answer: it is scored with the same asymmetric/cumulative machinery as
    # everything else and compared against the window-mean winner. The
    # symmetry gate is not applied to it, because that gate is precisely what
    # is wrong on a drifting baseline; the significance floor still is, so a
    # flat trace with no transition cannot produce a fabricated Tg.
    deriv_i = _derivative_peak(T, y, exclude, below)
    if deriv_i is not None and deriv_i != best:
        d_step = _step_at(T, y, deriv_i, win)
        b_step = _step_at(T, y, best, win)
        if d_step > b_step:
            best = deriv_i

    # A step is only a glass transition if it is a meaningful fraction of the
    # signal excursion. Without this test the routine always returns
    # *something*, so a sample with no glass transition (a pure melting trace)
    # gets a fabricated Tg drawn from residual curvature.
    #
    # The excursion is measured over the step-like part of the trace only. Using
    # the full range lets a single large melting peak set the yardstick: on a
    # semicrystalline trace with a 1.5 W/g peak and a 0.08 W/g glass transition,
    # the true step is 0.00014 of the full range and failed a 0.03 floor, even
    # though it is unmistakable in the data. Both traces must be judged against
    # their own background, not against the largest event anywhere in the scan.
    before = float(np.mean(y[max(0, best - win) : best]))
    after = float(np.mean(y[best : best + win]))
    step_size = abs(after - before)

    # Excursion of the step-like background: exclude the excluded (melting)
    # range, then take the span of what remains.
    #
    # This must not become arbitrarily small. On a trace that is nothing but a
    # melting peak, excluding the peak leaves an almost flat background whose
    # span is ~0.09 W/g against a full range of 3.0; judging the step against
    # that would let instrument noise be significant and fabricate a Tg. The
    # background span is therefore floored at a fraction of the full excursion,
    # so it can relax the gate for a genuine small Tg on a strongly melting
    # sample without ever collapsing the yardstick to noise.
    if exclude is not None:
        keep = (T < exclude[0]) | (T > exclude[1])
    else:
        keep = np.ones(T.size, dtype=bool)
    full_range = float(np.max(y) - np.min(y))
    background = y[keep] if keep.any() else y
    background_range = float(np.max(background) - np.min(background))
    total_range = max(background_range, _MIN_BACKGROUND_FRACTION * full_range)
    if total_range <= 0:
        total_range = full_range
    if total_range <= 0:
        return None
    if step_size / total_range < _MIN_TG_STEP_FRACTION:
        return None
    return best


def _local_maxima_mask(z: np.ndarray, order: int) -> np.ndarray:
    """Boolean mask of points that are the maximum of their +-``order`` window.

    Vectorised sliding-window maximum. The nested-loop equivalent is O(n *
    order) in Python and made the 116-file sweep take minutes per trace, so the
    sweep never completed; this is O(n log order) through ``np.maximum.reduceat``
    on a strided view.

    The window is clipped at the array ends, so an end point can be a local
    maximum -- callers that must not accept a boundary as a peak check the index
    against ``order`` themselves.
    """
    n = z.size
    if n == 0 or order <= 0:
        return np.zeros(n, dtype=bool)
    # Build a (n, 2*order+1) view of the neighbourhood of every point, padded
    # with -inf so the clip at the ends cannot create false maxima.
    width = 2 * order + 1
    padded = np.full(n + 2 * order, -np.inf, dtype=float)
    padded[order : order + n] = z
    windows = np.lib.stride_tricks.sliding_window_view(padded, width)
    return z >= windows.max(axis=1)


def _find_peak_temperature(
    T: np.ndarray, y: np.ndarray, *, search_both_polarities: bool = True
) -> int | None:
    """
    Index of the most prominent *peak* (a transient excursion that returns to
    the baseline), used to locate melting and crystallisation events.

    Found on the residual after subtracting a local baseline fitted on the
    flanks of the scan, which removes both the sloping heat-capacity
    background and instrument drift. A straight chord joining the two ends of
    the scan is NOT adequate for this: it is not the peak baseline, and on a
    real PCL scan it made the melting enthalpy come out at 340 J/g against a
    physical maximum of 139.5 J/g.

    ``search_both_polarities`` is the fix for a defect that made this function
    return cold crystallisation as the melting point, and it defaults to true
    only because a direct caller may hand in a signal whose convention is
    genuinely unknown. When the caller *knows* the trace is endothermic-up --
    which ``analyse_dsc`` does, because ``resolve_trace`` normalises it from
    the file header -- searching both polarities is not a safety net, it is a
    hazard: on ``DSC_PLLA_10K_2nd_heating`` the negated branch scores the
    cold-crystallisation exotherm at 85.3 C (prominence 1.381) above the real
    melting endotherm at 167.4 C (prominence 1.141), so the melting point was
    reported 82 C low. The search found the larger excursion, and the larger
    excursion was not the melting peak.

    Narrowing the prominence window does not rescue the inference: measured at
    windows from 1 C to 20 C of scan, the negated branch wins at every one.
    That is the same finding as section 4 item 4 -- a cold-crystallisation
    exotherm and a melting endotherm have arbitrary and overlapping
    magnitudes, so no threshold separates them. The convention is a property of
    the file and has to come from the file.
    """
    n = T.size
    if n < 5:
        return None

    # Locate the candidate by shape, not by a chord residual.
    #
    # The original code used ``argmax(y - chord)`` with ``chord`` joining the
    # first and last sample. That is degenerate whenever the curve lies entirely
    # below the chord: the residual's maximum is then exactly 0.0 and occurs at
    # index 0 by construction, so the "melting temperature" came back as the
    # first sample of the ramp. On the figshare 24462004 traces this is the norm
    # rather than the exception -- the heat flow at the start of a ramp is the
    # global maximum of the series (the sample is coldest there and the
    # instrument stores exothermic-up), so the curve does sit below the chord
    # and the bug fires on PLA, EVA, PET, PBT and ABS alike:
    #
    #     PLA1-AR   Tm = -90.06   EVA2-AR  Tm = -90.06
    #     PET2-AR   Tm =  -0.06   PE-NEW   Tm = 159.43  (the last sample)
    #
    # A melting endotherm is a *local extremum that returns to its local
    # baseline*. That definition cannot degenerate: it does not reference the
    # ends of the scan at all. ``_PEAK_ORDER`` is how many samples the trace
    # must leave the extremum before coming back, which is what distinguishes a
    # real endotherm from single-point instrument noise.
    #
    # The instrument convention is exothermic-up, so melting is a *minimum* of
    # the stored heat flow (``analyse_dsc`` inverts the sign before calling
    # here, see the caller, but this function is also reachable directly from
    # tests with either convention). Both polarities are therefore tried and the
    # more prominent excursion wins, which keeps the function independent of the
    # convention at the call site.
    order = max(3, min(_PEAK_ORDER, n // 8))

    # The prominence window: the transition width, in samples. A melting
    # endotherm on a 10 K/min scan rises and returns over roughly ten degrees,
    # so the window is set in degrees and converted with the trace's own
    # sampling rate. Measuring prominence over the detector's own narrow
    # neighbourhood instead was the second half of this bug -- see below.
    rate = float(np.median(np.diff(T[n // 4 : 3 * n // 4]))) if n >= 4 else 0.0
    if rate > 0:
        hw = max(order, min(int(_PEAK_QUALIFY_WINDOW_C / rate), n // 2 - 1))
    else:
        hw = max(order, min(n // 10, n // 2 - 1))

    full_range = float(np.nanmax(y) - np.nanmin(y))
    if full_range <= 0:
        return None

    # Collect every apex of both polarities and score each one, keeping the most
    # prominent. Assigning the candidate without scoring it -- which is what the
    # first draft of this function did -- makes the answer depend on iteration
    # order, so the *last* apex in the trace wins regardless of size. On the
    # figshare PLA trace that picked a 163.6 C apex of no significance and
    # rejected it, discarding the real melting endotherm at 151.2 C that was
    # sitting in the same candidate list.
    #
    # Vectorised: a point is an apex of ``z`` when it equals the maximum of the
    # window ``[i - order, i + order]``. Doing this with a sliding-window
    # maximum is O(n); the obvious nested loop over every index is O(n * order)
    # in Python and took minutes per file on the 16 000-point traces, which is
    # why the sweep never finished.
    z_plus = y
    z_minus = -y
    best: int | None = None
    best_sign = 1.0
    best_prom = 0.0
    # Only the stored polarity when the caller knows the convention. Trying both
    # and keeping the larger excursion is an inference, and an inference about
    # polarity is what section 4 item 6 says cannot be made from shape: the
    # cold-crystallisation exotherm on the 10 K PLLA trace outscores the real
    # melting endotherm in the negated branch, so the "more prominent" rule
    # reported a crystallisation event as the melting point.
    branches = ((1.0, z_plus), (-1.0, z_minus)) if search_both_polarities else ((1.0, z_plus),)
    for sign, z in branches:
        apex_mask = _local_maxima_mask(z, order)
        for i in np.flatnonzero(apex_mask):
            if i < order or i >= n - order:
                continue
            lo = max(0, i - hw)
            hi = min(n, i + hw + 1)
            wl = z[lo:i]
            wr = z[i + 1 : hi]
            if wl.size == 0 or wr.size == 0:
                continue
            # At an apex of z, prominence is how far it stands above the higher
            # of its two shoulders: the standard topographic definition.
            prom = float(z[i] - max(np.min(wl), np.min(wr)))
            if prom > best_prom:
                best_prom = prom
                best = i
                best_sign = sign
    if best is None or best_prom <= 0:
        return None
    rough = best

    # A melting endotherm returns to its own baseline; a glass transition steps
    # to a new level and stays there. Amplitude cannot separate the two -- on
    # the figshare set the amorphous PS produces a LARGER prominence (0.378 of
    # the range) than the genuinely melting PET (0.165), so any threshold on
    # prominence reports a melting peak for a polymer that cannot melt.
    #
    # The discriminating quantity is local: measure the level just before the
    # event and just after it, on the same window used for the prominence. A
    # peak ends where it began; a step does not. Measured that way the same set
    # separates -- see the tests, which pin real melting traces as accepted and
    # amorphous ones as rejected.
    z = best_sign * y
    lo = max(0, rough - hw)
    hi = min(n, rough + hw + 1)
    edge = max(1, hw // 5)
    before = float(np.median(z[lo : lo + edge])) if lo + edge <= rough else None
    after = float(np.median(z[hi - edge : hi])) if hi - edge > rough else None
    if before is not None and after is not None and full_range > 0:
        # ``z`` is oriented so the candidate is a maximum: a pure peak comes
        # back down to ``before``, so the level *after* the event sits below
        # the level *before* it by no more than the peak's own return.
        # A step keeps climbing, so ``after`` is at or above ``before``.
        return_signal = (z[rough] - after) / max(z[rough] - before, 1e-12)
        if return_signal < _MIN_PEAK_RETURN:
            return None

    # The candidate must be a real excursion in its own trace, not the gentle
    # undulation of a featureless scan.
    if best_prom / full_range < _MIN_PEAK_FRACTION:
        return None
    # An apex at an end of the scan is not a transition, it is the boundary.
    if rough <= order or rough >= n - order - 1:
        return None

    # Refine against a baseline fitted away from the transition.
    #
    # The refinement is confined to the neighbourhood of the shape-search
    # candidate, and this is the whole point of it. Searching the entire trace
    # for the largest absolute excess -- ``nanargmax(abs(excess))`` -- makes the
    # answer depend on where the *fitted baseline* is furthest from the curve,
    # which is typically an end of the scan where the baseline is extrapolated.
    # On the figshare PET2-AR trace that returned index 0, so the reported Tm
    # went back to ``-0.06`` (the first sample of the ramp) even though the
    # shape search had already found the real endotherm at 254.0 C. That is the
    # original bug re-entering by a second door.
    baseline = _local_baseline(T, y, rough)
    excess = y - baseline
    search_lo = max(0, rough - hw)
    search_hi = min(n, rough + hw + 1)
    candidate = rough
    peak_excess = best_prom
    if not np.all(np.isnan(excess)):
        local = np.abs(excess[search_lo:search_hi])
        if local.size:
            refined = search_lo + int(np.nanargmax(local))
            if abs(float(excess[refined])) >= abs(float(excess[rough])):
                candidate = refined
                peak_excess = abs(float(excess[candidate]))

    # Shape test on the refined candidate. A melting endotherm is a peak: the
    # excess rises into it and falls away after. The switching transient at the
    # start of a scan has no apex at all -- the excess is maximal at the very
    # beginning of the scan and decays from there. On the figshare 24462004 PVC
    # trace (amorphous, glass transition at 82 C, no melting) that transient
    # gives a candidate at 14.6 C whose excess is 50 % of the trace range, so
    # the magnitude floor above lets it through.
    #
    # The window must be wide enough to see the rise. Measured over 30 points
    # around that candidate the excess is flat to 2e-7 -- neither a peak nor a
    # visible slope -- but over 10 % of the scan the decay is unmistakable.
    # So the slopes are compared over a fraction of the trace, and the test is
    # one-sided: a real peak needs a clearly rising side, and anything whose
    # excess never rises as the scan proceeds is not an endotherm.
    span = max(_PEAK_FLANK_POINTS, n // 10)
    lo = max(0, candidate - span)
    hi = min(n, candidate + span + 1)
    if hi - lo > 8:
        left = excess[lo:candidate]
        right = excess[candidate:hi]
        if left.size > 2 and right.size > 2:
            rise = float(np.nanmax(left) - np.nanmin(left))
            fall = float(np.nanmax(right) - np.nanmin(right))
            scale = max(peak_excess, 1e-12)
            # A peak of this height must show a rise of comparable size on its
            # leading side. A decaying transient shows almost none.
            if rise / scale < _MIN_PEAK_RISE:
                return None
            if fall / scale < _MIN_PEAK_RISE and rise > 0:
                # Flat-topped plateau rather than a peak: reject only when the
                # trailing side does not come back down either.
                return None
    return candidate


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


def _monotonic_temperature(
    T: np.ndarray, m: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """
    Force a strictly increasing temperature axis by sorting and averaging.

    Instrument exports are not monotonic in temperature: the furnace holds or
    overshoots, so the same set-point appears many times, and the trace can
    dip backwards. Dropping every non-increasing point deletes the rising
    limbs of a non-monotonic trace, which distorts the mass curve, and it does
    not even guarantee monotonicity afterwards. Averaging the samples that
    share a temperature keeps the mass information and makes the derivative
    finite, because the interval can no longer be zero.
    """
    order = np.argsort(T, kind="stable")
    T, m = T[order], m[order]
    # Group identical temperatures without assuming a fixed spacing.
    boundaries = np.flatnonzero(np.diff(T) != 0)
    starts = np.concatenate(([0], boundaries + 1))
    ends = np.concatenate((boundaries + 1, [T.size]))
    T_out = T[starts]
    m_out = np.array([m[a:b].mean() for a, b in zip(starts, ends, strict=True)])
    return T_out, m_out


def _dtg_peak_temperature(T: np.ndarray, dtg: np.ndarray) -> float | None:
    """
    Temperature of the tallest DTG peak, excluding the run boundaries.

    The mass trace is flat once the ramp ends, so any residual gradient there
    is noise rather than decomposition. Reporting it would name the end of the
    scan as the decomposition temperature — an artefact that looks plausible
    because it lands in a real temperature range. The first and last 2 % of
    the trace are therefore excluded from the peak search.
    """
    if dtg.size == 0:
        return None
    finite = np.isfinite(dtg)
    if not finite.any():
        return None
    margin = max(1, int(round(dtg.size * 0.02)))
    lo, hi = min(margin, dtg.size - 1), max(dtg.size - margin, 1)
    segment = dtg[lo:hi]
    if segment.size == 0:
        return None
    return float(T[lo + int(np.argmax(segment))])


#: A step's rate must rise above this fraction of the tallest interior DTG peak
#: to count as a discrete event.
#:
#: The value only decides *where* a step is; it does not set how much the step
#: lost, because the boundaries are then extended to the valley between peaks.
#: That makes the result insensitive to it: anywhere in 0.08-0.25 the four
#: synthetic traces with known losses all come out exactly right. Outside that
#: band it degrades -- at 0.05 two equal 30 % steps merge into one of 60 %,
#: because the valley between them never drops that far; at 0.35 the faint
#: moisture loss ahead of a large decomposition is missed. 0.15 sits in the
#: middle of the stable band rather than at an edge.
#:
#: On the real PEI 25000 trace the mass profile is 4.4 % over 30-150 C
#: (moisture) then 17.5 % over 250-400 C (the polymer). At 0.15 the second is
#: reported as a single 20 % step ending near 420 C, with 0.1 % unattributed.
_STEP_PROMINENCE = 0.15

#: Two regions closer than this many degrees are the same event interrupted by
#: a noise crossing, so they are joined.
_STEP_MERGE_GAP_C = 15.0

# A note on what this deliberately does not attempt: decomposing a shoulder.
#
# A blend such as PLA/PHA shows a faint early loss (the PHA, 6.7 % over
# 200-300 C) sitting on the rising flank of the main decomposition (the PLA,
# 88.3 % over 300-400 C). There is no valley between them -- the rate never
# falls -- so no threshold separates them, and that is a property of the
# signal, not of the threshold. Measured on the real PLA/PHA trace from
# Zenodo 10.5281/zenodo.18940798, using the instrument's own derivative column
# as well as a re-derived one: a single region at every threshold from 0.08 to
# 0.25.
#
# Fitting two sigmoids to recover the shoulder was tried and rejected. It fits
# better than one (RMS 0.41 against 0.90) but the split it reports is not
# stable and does not match the physical composition: from four starting
# guesses it returned first-step losses of 9.8 %, 15.6 %, 21.2 % and 40.3 %
# against a true 6.7 %, and the guess with the best RMS gave the worst answer.
# Two free sigmoids describing one peak is overfitting, and shipping it would
# put a confident, wrong composition in a report. The shoulder is therefore
# reported inside the step it belongs to, with a note naming the early loss --
# see the single-step branch in `analyse_tga`.


def _first_mass_change(mass: np.ndarray, T: np.ndarray, before: int) -> int:
    """
    Index where the trace first leaves its initial plateau, at or before `before`.

    A TGA run starts on a flat baseline while the sample equilibrates. If a
    single decomposition step is detected, its left boundary must be where the
    mass actually begins to fall, not the first data point: reporting that a
    decomposition started at 30 C because the furnace began logging there is
    plainly wrong. Threshold on the total change so far rather than on a
    per-point slope, which noise dominates over a single sample.
    """
    if before <= 0 or mass.size == 0:
        return 0
    span = abs(float(mass[0] - mass[-1]))
    if span <= 0.0:
        return 0
    # 0.5 % of the total loss is the tolerance: below that the sample is still
    # on its plateau, above it the decomposition has visibly begun.
    tolerance = max(0.005 * span, 1e-9)
    for i in range(before + 1):
        if abs(float(mass[0] - mass[i])) > tolerance:
            return i
    return before


def _last_mass_change(mass: np.ndarray, after: int) -> int:
    """
    Index at or after which the mass no longer falls, from `after` to the end.

    The mirror of `_first_mass_change`. Once the ramp ends and the residue is
    stable, the mass curve is flat, and the last step must not be reported as
    extending to the final data point.
    """
    n = mass.size
    if after >= n - 1 or n == 0:
        return n - 1
    span = abs(float(mass[0] - mass[-1]))
    if span <= 0.0:
        return n - 1
    tolerance = max(0.005 * span, 1e-9)
    final = float(mass[-1])
    for i in range(n - 1, after - 1, -1):
        if abs(float(mass[i] - final)) > tolerance:
            return i
    return after


def _decompose_steps(
    T: np.ndarray,
    m_smooth: np.ndarray,
    T_u: np.ndarray,
    m_u: np.ndarray,
    min_step_pct: float,
) -> tuple[list[dict[str, float]], float]:
    """
    Split a TGA trace into discrete decomposition steps, and say what is left.

    A step is a contiguous region where the rate of loss exceeds a fraction of
    the tallest peak. Thresholding the *rate* rather than the per-point mass
    drop is what makes this independent of how many points a ramp spans: a 3 %
    loss spread over 100 degrees has a small per-point drop but a
    distinguishable rate.

    Returns the steps and the mass loss that no step accounts for. That second
    number is the honest part. A loss can be real and still not separable: if
    its rate never rises above the noise of the derivative, no method recovers
    it, and reporting a step there would be inventing structure. Measured
    example -- a 3 % moisture loss ahead of a 72 % decomposition has a DTG peak
    of 0.054 %/degC against a derivative noise amplitude of 0.10 %/degC, a
    signal-to-noise of 0.5. It is genuinely unobservable in that trace, so it
    is reported as unattributed rather than as a step.
    """
    candidate = np.abs(np.gradient(m_u, T_u))
    if T_u.size < 3:
        total = float(m_u[0] - m_u[-1]) if m_u.size else 0.0
        return [], max(total, 0.0)

    # Exclude the run boundaries from the peak search, for the same reason
    # `_dtg_peak_temperature` does: once the ramp ends the mass is flat, so the
    # only gradient left there is noise, and `np.gradient` uses a one-sided
    # difference at the two endpoints, which doubles it. On a real trace
    # (PEI 25000) that tail noise peaks at 0.30 %/degC against a genuine
    # decomposition rate of 0.18 %/degC -- the artefact is the tallest "peak",
    # and thresholding against it discards the real step. Measure the peak on
    # the interior and apply that threshold everywhere else.
    margin = max(1, int(round(candidate.size * 0.02)))
    interior = candidate[margin : candidate.size - margin]
    peak = float(interior.max()) if interior.size else float(candidate.max())
    if peak <= 0.0:
        total = float(m_u[0] - m_u[-1]) if m_u.size else 0.0
        return [], max(total, 0.0)

    threshold = _STEP_PROMINENCE * peak
    # Clamp the boundary regions to the interior peak so a tail artefact is not
    # itself promoted to a step: it is noise, not decomposition.
    active = np.where(candidate > threshold, candidate, 0.0) > 0.0
    if margin:
        active[:margin] = False
        active[active.size - margin :] = False

    regions: list[list[int]] = []
    i = 0
    while i < active.size:
        if active[i]:
            j = i
            while j + 1 < active.size and active[j + 1]:
                j += 1
            regions.append([i, j])
            i = j + 1
        else:
            i += 1

    # Join regions separated only by a brief dip below the threshold: that is
    # one event crossed by noise, not two events.
    merged: list[list[int]] = []
    for start, end in regions:
        if merged:
            gap = T_u[start] - T_u[merged[-1][1]]
            if gap <= _STEP_MERGE_GAP_C:
                merged[-1][1] = end
                continue
        merged.append([start, end])

    # The regions live on the uniform grid the rate was computed on. The
    # threshold decides *where a step is*, not *how much it lost*: a threshold
    # on the rate level necessarily cuts the tails of a peak, and measuring the
    # loss between the crossing points therefore understates every step (on a
    # 30 %/60 % two-step trace it reports 23.8 % and 55.3 % -- a 20 % error on
    # the first). The boundaries are instead pushed out to the valleys between
    # peaks, which is where one event genuinely ends and the next begins.
    steps: list[dict[str, float]] = []
    attributed = 0.0
    for idx, (start, end) in enumerate(merged):
        # Boundaries go to the lowest rate between this step and its neighbour,
        # which is the valley separating two events. Searching for the minimum
        # in the window is what makes this robust: walking outward until the
        # rate stops falling fails when noise makes it fluctuate, and then the
        # boundary runs to the end of the trace and the step claims the whole
        # scan. The window is bounded by the neighbouring peak so the search
        # cannot wander into it.
        if idx == 0:
            # The left edge runs to the start of the run, but not before the
            # first point where the mass has begun to fall: taking the raw start
            # would report a decomposition as beginning at the first data point
            # when the sample is still dry and flat. `_first_mass_change` finds
            # where the trace actually leaves its initial plateau.
            lo = _first_mass_change(m_u, T_u, start)
        else:
            prev_peak = merged[idx - 1][1]
            gap = candidate[prev_peak : start + 1]
            lo = prev_peak + int(np.argmin(gap)) if gap.size else start
        if idx == len(merged) - 1:
            # Symmetrically, the right edge of the last step is where the mass
            # stops falling, not the end of the scan: a residue that has been
            # constant for 200 degrees is not still decomposing.
            hi = _last_mass_change(m_u, end)
        else:
            nxt_peak = merged[idx + 1][0]
            gap = candidate[end : nxt_peak + 1]
            hi = end + int(np.argmin(gap)) if gap.size else end

        t_onset = float(T_u[lo])
        t_end = float(T_u[hi])
        m_onset = float(np.interp(t_onset, T, m_smooth))
        m_end = float(np.interp(t_end, T, m_smooth))
        loss = m_onset - m_end
        if loss < min_step_pct:
            # Below the reporting floor: real, but too small to name as a step.
            attributed += max(loss, 0.0)
            continue
        steps.append(
            {"onset_C": t_onset, "end_C": t_end, "loss_pct": loss}
        )
        attributed += loss

    total_loss = float(m_smooth[0] - m_smooth[-1]) if m_smooth.size else 0.0
    unattributed = max(total_loss - attributed, 0.0)
    return steps, unattributed


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
    T, m = _monotonic_temperature(T, m)
    if T.size < 3:
        raise ValueError("The TGA trace needs at least 3 distinct temperatures.")

    m_smooth = _smooth(m, smooth_window)
    # DTG in %/degC: rate of mass loss, reported positive for a loss. The
    # derivative is taken on a uniform grid because the instrument's own
    # spacing is uneven, and non-finite values are forced to zero because
    # np.argmax returns the position of a NaN rather than the maximum.
    T_u, m_u = _uniform_grid(T, m_smooth)
    dtg_u = -np.gradient(m_u, T_u)
    dtg_u = np.where(np.isfinite(dtg_u), dtg_u, 0.0)
    dtg = np.interp(T, T_u, dtg_u)

    Td5 = _temperature_at_fraction(T, m_smooth, 5.0)
    Td10 = _temperature_at_fraction(T, m_smooth, 10.0)
    T95 = _temperature_at_fraction(T, m_smooth, 95.0)
    T_peak = _dtg_peak_temperature(T_u, dtg_u)
    residue = float(m_smooth[-1])

    # Detect discrete steps from the shape of the rate curve rather than from
    # an absolute per-point mass drop. A step is a contiguous region where the
    # rate of loss is a substantial fraction of the tallest peak; the
    # boundaries are where the rate rises above, then falls back below, that
    # fraction. The old rule (`dm < -0.01` per point) depended on how many
    # points a ramp happened to span, so a step spread over a wide window had
    # a small per-point drop and was never seen, and two overlapping steps
    # merged into one region whose total was right but whose division was
    # lost.
    steps, unattributed = _decompose_steps(T, m_smooth, T_u, m_u, min_step_pct)

    notes: list[str] = []
    if unattributed > max(1.0, 0.02 * abs(m_smooth[0] - m_smooth[-1])):
        notes.append(
            f"{unattributed:.1f} % of the mass loss is not part of any reported "
            "step. It is either spread too gradually for its rate to stand out "
            "against the noise, or spread across steps that overlap. Each "
            "reported step is real; the list is not necessarily complete."
        )
    if len(steps) == 1 and steps[0]["loss_pct"] > 10.0:
        # A single wide step can hide a second, faint event inside it: a small
        # moisture loss whose rate never rises to the detection threshold is
        # absorbed into the span of the large one. Its mass is accounted for,
        # but an analyst reading "one step of 76 %" would not know a soft
        # event is riding along, so say so with the measured numbers.
        onset, end, span = steps[0]["onset_C"], steps[0]["end_C"], steps[0]["loss_pct"]
        early = [
            float(m_smooth[i])
            for i in range(T.size)
            if onset <= T[i] <= min(onset + 0.25 * (end - onset), end)
        ]
        if early and (early[0] - early[-1]) > max(2.0, 0.05 * span):
            notes.append(
                f"One step was detected, spanning {onset:.0f}-{end:.0f} C, but "
                f"{early[0] - early[-1]:.1f} % of its loss happens in the first "
                "quarter of that range. A weak event (moisture or solvent) is "
                "probably riding on the main decomposition; it is included in "
                "this step rather than reported separately because its rate "
                "does not stand out against the noise."
            )
    if len(steps) > 1:
        notes.append(
            "Several steps were detected. T_max_rate names the fastest one, "
            "which is not necessarily the first; use the step list for "
            "per-step onsets."
        )

    # Physical plausibility of the input, which the analysis otherwise takes on
    # trust. A thermobalance cannot weigh a negative mass, and a run that
    # starts below 100 % has lost sample before the ramp -- both are real in
    # the figshare 24595695 TGA-FTIR set, where seven of 27 files end at
    # -0.35 to -1.41 % and report that as the residue. The number is passed
    # through unchanged (it is what the instrument wrote, and silently
    # clamping it to zero would hide an instrument fault the analyst needs to
    # see), but the analyst is told, because "residue = -1.4 %" is otherwise
    # accepted as a measurement when it is not one.
    if residue < 0.0:
        notes.append(
            f"The trace ends at {residue:.2f} % mass, which is negative and "
            "therefore not a physical residue. This is the instrument's own "
            "value, reported unchanged; the run either drifted or was "
            "mis-zeroed. Do not quote this as a residue."
        )
    elif residue > 105.0:
        notes.append(
            f"The trace ends at {residue:.2f} % mass, above the starting "
            "value. Buoyancy or a mis-zeroed balance is the usual cause; "
            "treat the residue as unquantified."
        )
    start_pct = float(m_smooth[0])
    if abs(start_pct - 100.0) > 5.0:
        notes.append(
            f"The trace starts at {start_pct:.1f} % rather than 100 %. It is "
            "normalised to its own first point, so the percentage axis is "
            "relative; a run that begins this far from 100 % has already lost "
            "volatiles before the ramp."
        )

    return TGAResult(
        Td_5pct=Td5,
        Td_10pct=Td10,
        T_max_rate=T_peak,
        T_95pct=T95,
        residue_pct=residue,
        steps=steps,
        unattributed_loss_pct=unattributed,
        notes=notes,
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
    polarity_known: bool = False,
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
    polarity_known : bool, default False
        Whether the caller has established that endothermic events point
        *upward* in ``heat_flow`` -- true when ``resolve_trace`` has already
        normalised the signal from the file's own declaration (``#EXO``).

        When true the melting search considers only the upward direction, which
        is the only direction a melting endotherm can be in. When false both
        directions are tried and the more prominent excursion wins, which is
        the behaviour this argument exists to make optional: on the 10 K PLLA
        trace that rule reports the cold-crystallisation exotherm at 85.3 C as
        the melting point, because its prominence (1.381) exceeds the real
        endotherm's (1.141). See section 4 item 6.

        The default is **False**, deliberately: a caller that has not
        established the convention must not be assumed to know it, and getting
        this wrong in the permissive direction risks a melting point 80 C off
        while getting it wrong in the conservative direction costs nothing
        more than the older inference. Callers that *do* know -- the HTTP path,
        which normalises through ``resolve_trace`` -- pass True explicitly.
        Callers holding a raw instrument trace that has not been through
        ``resolve_trace`` should leave it False and accept the inference,
        which is what it is.

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
    # The melting peak is the largest transient excursion *above* the baseline
    # joining the ends of the scan.
    #
    # Whether the search is allowed to consider the downward direction as well
    # is decided by ``polarity_known``, and that argument is the fix for a
    # defect that had this function reporting crystallisation as melting. The
    # signal reaching here has already been normalised to endothermic-up by
    # ``resolve_trace`` when the file declared its convention, so a melting
    # endotherm points up and only up. Searching both directions anyway means
    # choosing the larger excursion, and on ``DSC_PLLA_10K_2nd_heating`` the
    # larger excursion is the cold-crystallisation exotherm at 85.3 C
    # (prominence 1.381 against the real endotherm's 1.141): the tool reported
    # Tm 82 C low, on the number the whole scan is run to obtain.
    tm_idx = _find_peak_temperature(
        T, hf_s, search_both_polarities=not polarity_known
    )
    melt_range: tuple[float, float] | None = None
    if tm_idx is not None:
        result.Tm = float(T[tm_idx])

        # Enthalpy by integrating the excess over a baseline fitted on the
        # flanks of the transition, not over the chord joining the scan ends.
        baseline = _local_baseline(T, hf_s, tm_idx)
        excess = hf_s - baseline
        peak_h = float(excess[tm_idx])
        pos = excess > 0
        if pos.any() and peak_h > 0:
            # Restrict to the region around the peak so that a separate event
            # elsewhere does not contribute to this enthalpy.
            #
            # "Excess positive" is too generous a bound. The fitted baseline
            # dips below the signal over most of a scan, so on a semicrystalline
            # trace the positive run reached from 74 C to 185 C -- it swallowed
            # the glass transition at 75 C and every point between. That range
            # is then handed to the Tg search as the region to exclude, so the
            # real glass transition is excluded and a flank is reported instead.
            #
            # A melting peak only matters where it is a real fraction of its own
            # height. Cutting at a few percent of the peak keeps the whole peak
            # and its immediate flanks while releasing the flat regions where
            # the baseline is merely fitting low.
            #
            # The walk also stops at a real valley. A fixed fraction is not
            # enough on its own, because a glass transition sitting below the
            # melting peak is itself an excess over the fitted baseline: a step
            # of 0.02 W/g against a peak of 0.10 W/g is 20 % of the height, well
            # above a 3 % floor. The walk then ran down to 74 C on a trace whose
            # Tg is at 75 C, and that range is handed to the glass-transition
            # search as the region to avoid -- so the real transition was
            # excluded and a melting flank was reported instead.
            #
            # The valley test needs the excess to have actually fallen before a
            # valley is accepted. A shallow tanh-shaped melting transition --
            # the shape a real DSC melting ramp has -- peaks at its apex, so the
            # first step outward is already "not rising" and the naive test
            # collapsed the melt range to a single point (178.5-178.6 C),
            # leaving the whole flank exposed to the Tg search.
            thresh = _PEAK_FLOOR * peak_h
            valley_level = 0.25 * peak_h
            a = tm_idx
            while a > 1 and excess[a] > thresh:
                if (
                    excess[a] <= valley_level
                    and excess[a] < excess[a - 1]
                    and excess[a] <= excess[a + 1]
                ):
                    break
                a -= 1
            b = tm_idx
            while b < T.size - 2 and excess[b] > thresh:
                if (
                    excess[b] <= valley_level
                    and excess[b] < excess[b - 1]
                    and excess[b] <= excess[b + 1]
                ):
                    break
                b += 1
            if b > a + 1:
                area = float(np.trapezoid(excess[a : b + 1], T[a : b + 1]))
                if heating_rate:
                    # W/g integrated over degC, divided by the rate in K/s,
                    # gives J/g. This is exact only when the x-axis is time,
                    # which is why the rate is required.
                    area = area / (heating_rate / 60.0)
                    result.delta_Hm = abs(area)
                else:
                    # Without the rate the integral is an area in W/g * degC,
                    # which is NOT an enthalpy and cannot be converted into one
                    # from the trace alone. It used to be reported as
                    # ``delta_Hm`` anyway: on ``DSC_PLLA_10K_2nd_heating`` that
                    # produced "61.2 J/g" with the rate and "10.19 J/g" without
                    # it, and the crystallinity followed the same number, 66 %
                    # against 11 %. Both look like results.
                    #
                    # Refusing is the only defensible option. The value is not
                    # approximately right and there is no bound to state -- the
                    # missing factor is the scan rate, which can be anything
                    # from 1 to 40 K/min -- so reporting it either scaled or
                    # unscaled would be inventing a number. The peak position
                    # does not need the rate and is still reported, with the
                    # reason it has no enthalpy attached.
                    result.delta_Hm = None
                    result.crystallinity_pct = None
                if result.delta_Hm is not None and ref_enthalpy_J_g and ref_enthalpy_J_g > 0:
                    xc = 100.0 * result.delta_Hm / ref_enthalpy_J_g
                    result.crystallinity_pct = xc
                    if xc > 100.0:
                        # Uma cristalinidade acima de 100 % é fisicamente
                        # impossível, e o número **é reportado** assim mesmo:
                        # suprimi-lo esconderia o erro, e um campo vazio diz
                        # menos que um 124 % visível. O que falta é um sinal
                        # legível por máquina dizendo que este valor não pode
                        # estar certo, para que quem consome a API não o trate
                        # como um resultado -- sem isso, 124,5 e 45,0 chegam
                        # com a mesma aparência.
                        #
                        # As causas são poucas e conhecidas: a referência não é
                        # a deste polímero, a amostra tem mais de uma fase
                        # cristalina (blenda), ou a linha de base da integração
                        # ficou alta e inflou a área.
                        result.crystallinity_refusal = (
                            f"A cristalinidade calculada ({xc:.1f} %) é "
                            f"fisicamente impossível: o ΔHm medido "
                            f"({result.delta_Hm:.1f} J/g) excede a entalpia de "
                            f"referência de 100 % cristalino "
                            f"({ref_enthalpy_J_g:g} J/g). O valor é reportado "
                            "para inspeção, mas não pode ser usado como "
                            "resultado. Verifique se a referência é a deste "
                            "polímero, se a amostra tem uma só fase cristalina, "
                            "e se a linha de base da integração está correta."
                        )
            melt_range = (float(T[a]), float(T[b]))

    # ---- Glass transition ---------------------------------------------------
    # Searched on the signal with the melting region excluded, using the
    # step-level discriminator so that a melting peak is never reported as Tg.
    # ASTM D3418 locates Tg from the step, not from the maximum slope.
    # The melting region is widened by a margin before it is used as the
    # exclusion. The walk that bounds it stops where the excess falls to a few
    # percent of the peak, which lands on the peak's own shoulder; a candidate
    # a tenth of a degree outside that bound is still on the melting flank, and
    # the glass-transition search then reports it. On the figshare 24462004 PET
    # trace (Tg 78 C, Tm 237 C) the melt_range came out as 122.5-256.9 and the
    # detector returned 257.0 -- the far shoulder of the melting peak, and a
    # Tg 180 C too high. The margin is a fixed few degrees because the flank
    # width does not scale with the peak.
    #
    # The exclusion must also cover *cold crystallisation*, for a reason that is
    # physical rather than defensive. On heating, an amorphous or quenched
    # sample passes through the glass transition, then may crystallise
    # ("cold crystallisation", exothermic and therefore pointing DOWN in the
    # endothermic-up convention), and only then melts. D. Dean, "Differential
    # Scanning Calorimetry" (Univ. of Alabama at Birmingham), slide 29, names
    # exactly this sequence; slide 28 defines the event.
    #
    # The ordering is a constraint the search can enforce: **a glass transition
    # lies BELOW the cold-crystallisation peak**, because once the sample has
    # crystallised the amorphous phase that produces the step is gone. A
    # candidate at or above the cold-crystallisation peak cannot be a Tg.
    #
    # Without this, the cold-crystallisation peak wins outright: on the real
    # PLLA trace DSC_PLLA_50K_2nd_heating (Zenodo 17288962) its descending limb
    # reaches a gradient of -0.332 W/g/K at 90 C, twenty times the glass
    # transition's +0.017 at 55 C, so the derivative-peak candidate is chosen
    # and Tg is reported as 94.7 C -- *above* the cold-crystallisation minimum
    # at 91.8 C, which is impossible. The true Tg, visible as a step between
    # 52 and 58 C, was 55 C: the tool was wrong by 40 C. The error was the same
    # on all three PLLA traces in that dataset (87.6, 94.2 and 94.7 C reported
    # against cold-crystallisation peaks at 85.3, 90.8 and 91.8 C).
    cold_cryst_peak = _find_cold_crystallisation(T, hf_s, tm_idx)
    exclude_range = melt_range
    if melt_range is not None:
        exclude_range = (melt_range[0] - _MELT_EXCLUDE_MARGIN_C, melt_range[1] + _MELT_EXCLUDE_MARGIN_C)
    tg_idx = _find_step_temperature(
        T, hf_s, exclude=exclude_range, below=cold_cryst_peak
    )
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
            # Measure the step between the plateaus flanking the transition.
            # Reading it from the ends of the scan instead folds the baseline
            # slope into the result, and on a falling signal (an exothermic-up
            # instrument) it also produced a *negative* delta_cp. The heat
            # capacity change across a glass transition is positive by
            # definition -- the liquid has a higher cp than the glass -- so the
            # reported value is the magnitude of the step over the rate.
            #
            # The window is sized from the measured width of the transition
            # itself (onset to end), so a narrow transition gets narrow
            # windows and a broad one gets wide ones.
            if result.Tg_onset is not None and result.Tg_end is not None:
                width = abs(result.Tg_end - result.Tg_onset)
            else:
                width = 0.05 * float(T[-1] - T[0])
            pre_lvl, post_lvl = _plateau_levels(T, hf_s, tg_idx, width)
            result.delta_cp = abs(post_lvl - pre_lvl) / (heating_rate / 60.0)

    # ---- How much should this Tg be trusted? -------------------------------
    # A bare number with no footing is the most dangerous thing a tool can hand
    # a researcher: on a real ABS trace (figshare 24462004) noise at the level
    # an instrument actually carries moves the reported Tg by 7-14 K, and
    # nothing in the result said so. Resampling the trace and re-running the
    # detection measures the method's sensitivity to the sampling of *this*
    # data. It is not an accuracy claim -- that needs a certified reference --
    # but it is the part that can be known from the data in hand.
    if result.Tg is not None and not _no_footing.get():
        result.Tg_uncertainty_C = _tg_footing(T, hf, heating_rate)
        result.Tg_reliable = (
            result.Tg_uncertainty_C is not None
            and result.Tg_uncertainty_C <= _TG_RELIABLE_TOLERANCE_C
        )

    # ---- Attach the confidence ladder --------------------------------------
    # Every number above is a bare float. These claims say what each one is
    # worth, and carry the observations that produced it, so a reader can judge
    # the inference instead of having to trust it. See ``FieldClaim``.
    #
    # The transition temperatures are SUGGESTED without exception. Measured
    # against the published windows on the 116 figshare traces, the Tg lands
    # correctly on roughly 30 % of them and the Tm on 106/116 -- and "106/116"
    # flatters it, because a value can fall inside a generous window for the
    # wrong reason. Nothing in this module can tell a glass transition from a
    # melting flank with the reliability a measurement implies, so it does not
    # claim to.
    if result.Tg is not None:
        ev = []
        if result.Tg_onset is not None and result.Tg_end is not None:
            ev.append(
                f"ASTM D3418 midpoint of {result.Tg_onset:.1f} and "
                f"{result.Tg_end:.1f} C"
            )
        else:
            ev.append("step located on the heat-flow baseline")
        if result.Tg_uncertainty_C is not None:
            ev.append(
                f"moves {result.Tg_uncertainty_C:.1f} K when the trace is resampled"
            )
        note = (
            "A suggested glass transition, not a measurement. Confirm against "
            "the expected Tg for this polymer before quoting it."
        )
        if result.Tg_reliable is False:
            note = (
                "A suggested glass transition that did NOT survive the "
                "resampling test: it moves more than "
                f"{_TG_RELIABLE_TOLERANCE_C:.0f} K with the sampling of this "
                "trace. Do not quote it as a number; go back to the instrument."
            )
        result.claims["Tg"] = FieldClaim(
            value=result.Tg,
            confidence=SUGGESTED,
            evidence=ev,
            note=note,
        )
        if result.delta_cp is not None:
            result.claims["delta_cp"] = FieldClaim(
                value=result.delta_cp,
                confidence=FORMULA,
                evidence=[
                    "step between the plateaux flanking the transition, "
                    "divided by the heating rate"
                ],
                note=(
                    "Derived from the suggested Tg. If the transition "
                    "identification is wrong, this step is measuring something "
                    "else."
                ),
            )

    if result.Tm is not None:
        ev = ["endothermic excursion that returns to the local baseline"]
        if result.delta_Hm is not None:
            ev.append(f"DeltaHm = {result.delta_Hm:.1f} J/g over the fitted baseline")
        result.claims["Tm"] = FieldClaim(
            value=result.Tm,
            confidence=SUGGESTED,
            evidence=ev,
            note=(
                "A suggested melting peak, not a measurement. The detector "
                "cannot always separate a melting endotherm from a glass "
                "transition: on this dataset it has reported a melting "
                "temperature for amorphous polystyrene, which has none."
            ),
        )

    if result.delta_Hm is not None:
        result.claims["delta_Hm"] = FieldClaim(
            value=result.delta_Hm,
            confidence=FORMULA,
            evidence=[
                "integral of the excess over a baseline fitted on the flanks "
                "of the transition (ASTM D3418)"
            ],
            note=(
                "Reproducible given the integration bounds, but the bounds "
                "come from a suggested peak."
            ),
        )

    if result.crystallinity_pct is not None:
        result.claims["crystallinity_pct"] = FieldClaim(
            value=result.crystallinity_pct,
            confidence=FORMULA,
            evidence=[
                "100 * DeltaHm / DeltaHm(100 % crystalline), with the "
                "reference enthalpy supplied by the caller"
            ],
            note=(
                "Inherits the uncertainty of the suggested DeltaHm, and of the "
                "reference enthalpy chosen."
            ),
        )

    if result.Tc is not None:
        result.claims["Tc"] = FieldClaim(
            value=result.Tc,
            confidence=SUGGESTED,
            evidence=["exothermic excursion on the cooling leg"],
            note="A suggested crystallisation peak, not a measurement.",
        )

    return result


def _tg_footing(
    T: np.ndarray,
    hf: np.ndarray,
    heating_rate: float | None,
    repeats: int = 12,
    seed: int = 0,
) -> float | None:
    """
    Spread of the reported Tg when the trace is resampled.

    Bootstrap over the points: the same measurement, re-drawn. If the answer
    barely moves, the detection is founded on the shape of the data; if it
    swings, it is founded on which points happened to be sampled and should
    not be quoted. Returns the upper half-width in kelvin, or None when too
    few resamples produced a Tg to say anything.

    The resamples run with the footing switched off (see _no_footing); the
    call is recursive otherwise, since each resample would compute a footing of
    its own, and twelve resamples of twelve resamples is not a measurement
    anyone is waiting for.
    """
    n = T.size
    if n < 20:
        return None

    rng = np.random.default_rng(seed)
    found: list[float] = []
    # Perturbation model: additive noise, not resampling with replacement.
    #
    # Resampling points with replacement (`rng.integers(0, n, n)`, the usual
    # bootstrap) is the wrong model here and it broke on real data. It discards
    # ~36 % of the points and leaves the temperature axis full of holes -- on a
    # 5882-point PLLA scan, 936 gaps wider than twice the original spacing,
    # some 9x wider. The detector then reads a trace no instrument produced and
    # returns a Tg that swings by tens of degrees.
    #
    # Measured on that same PLLA_25K trace, whose Tg step has a
    # signal-to-noise of 238:
    #     destructive bootstrap -> +-35.91 K   (false alarm: "not reliable")
    #     additive noise        -> +-0.03 K    (the correct answer)
    #
    # An instrument does not re-draw which temperatures it visits; it keeps the
    # axis and adds noise to the signal. So that is what the resample does. The
    # sigma is the trace's own local noise, estimated from the point-to-point
    # difference via the median absolute deviation, which is robust to the real
    # transitions (those are smooth and affect few points).
    if n > 2:
        diffs = np.diff(hf)
        mad = float(np.median(np.abs(diffs - np.median(diffs))))
        sigma = 1.4826 * mad / np.sqrt(2.0)
        if not np.isfinite(sigma) or sigma <= 0:
            sigma = float(np.std(diffs) / np.sqrt(2.0))
    else:
        sigma = 0.0
    if not np.isfinite(sigma) or sigma <= 0:
        return None

    for _ in range(repeats):
        perturbed = hf + rng.normal(0.0, sigma, n)
        token = _no_footing.set(True)
        try:
            r = analyse_dsc(list(T), list(perturbed), heating_rate=heating_rate)
        except (ValueError, IndexError):
            continue
        finally:
            _no_footing.reset(token)
        if r.Tg is not None:
            found.append(float(r.Tg))

    if len(found) < 4:
        return None
    # Half the central spread: a robust width that one wild resample cannot
    # inflate, which matters because a single bad resample is exactly the
    # failure being measured.
    lo, hi = np.percentile(found, [10.0, 90.0])
    return float((hi - lo) / 2.0)
