"""
Structural characterisation: X-ray diffraction and infrared spectroscopy.

References
----------
- Scherrer, P. "Bestimmung der Grosse und der inneren Struktur von
  Kolloidteilchen mittels Rontgenstrahlen." Nachr. Ges. Wiss. Gottingen 26,
  98-100 (1918).  (Crystallite size from peak broadening.)
- Patterson, A.L. "The Scherrer formula for X-ray particle size
  determination." Phys. Rev. 56, 978 (1939). doi:10.1103/PhysRev.56.978
  (The constant K and its dependence on crystallite shape.)
- Alexander, L.E. "X-ray Diffraction Methods in Polymer Science".
  Wiley-Interscience, 1969. (Crystallinity index for polymers.)
- Murthy, N.S.; Minor, H. "General procedure for evaluating amorphous
  scattering and crystallinity from X-ray diffraction scans of
  semicrystalline polymers." Polymer 31, 996 (1990).
- ASTM E1426-14(2019), "Standard Test Method for Determining the X-Ray
  Elastic Strain and X-Ray Effective Instrumental Broadening".
- ISO 13779 / ASTM F2029 analogues for degree of crystallinity by DSC.
- Socrates, G. "Infrared and Raman Characteristic Group Frequencies",
  3rd ed. Wiley, 2001. (FTIR band assignments.)
- Coates, J. "Encyclopedia of Analytical Chemistry: Interpretation of
  Infrared Spectra, A Practical Approach". Wiley, 2000.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

__all__ = [
    "XRDResult",
    "FTIRResult",
    "analyse_xrd",
    "scherrer_crystallite_size",
    "analyse_ftir",
    "FTIR_REFERENCE_BANDS",
]


# --------------------------------------------------------------------------
# X-ray diffraction
# --------------------------------------------------------------------------


@dataclass
class XRDResult:
    """X-ray diffraction results. d-spacing in angstrom, size in nm."""

    #: Bragg angle (2-theta) of each detected peak, in degrees.
    peaks_two_theta: list[float] = field(default_factory=list)
    #: Interplanar spacing d = lambda / (2 sin theta), in angstrom.
    d_spacing_angstrom: list[float] = field(default_factory=list)
    #: Crystallite size per peak from the Scherrer equation, in nm. Peaks with
    #: no measurable width are dropped rather than reported as None, so this
    #: stays parallel with peaks_two_theta.
    crystallite_size_nm: list[float] = field(default_factory=list)
    #: Integral breadth of each peak (FWHM before correction), in degrees.
    fwhm_deg: list[float] = field(default_factory=list)
    #: Crystallinity index from the ratio of crystalline to total integrated
    #: intensity, in percent. See the method note in ``analyse_xrd``.
    crystallinity_pct: float | None = None
    #: Wavelength used, in angstrom.
    wavelength_angstrom: float = 1.5406
    #: Full pattern, for plotting.
    two_theta: list[float] = field(default_factory=list)
    intensity: list[float] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "peaks_two_theta": self.peaks_two_theta,
            "d_spacing_angstrom": self.d_spacing_angstrom,
            "crystallite_size_nm": self.crystallite_size_nm,
            "fwhm_deg": self.fwhm_deg,
            "crystallinity_pct": self.crystallinity_pct,
            "wavelength_angstrom": self.wavelength_angstrom,
            "two_theta": self.two_theta,
            "intensity": self.intensity,
        }


def scherrer_crystallite_size(
    two_theta_deg: float,
    fwhm_deg: float,
    wavelength_angstrom: float = 1.5406,
    K: float = 0.9,
    instrumental_fwhm_deg: float = 0.0,
) -> float | None:
    r"""
    Crystallite size from the Scherrer equation, in nanometres.

        D = K * lambda / (beta * cos(theta))

    Parameters
    ----------
    two_theta_deg : float
        Peak position as the diffraction angle 2-theta, in degrees.
    fwhm_deg : float
        Full width at half maximum of the peak, in degrees (2-theta).
    wavelength_angstrom : float
        X-ray wavelength. Defaults to Cu K-alpha1, 1.5406 angstrom.
    K : float
        Shape factor. 0.9 is the conventional value for spherical
        crystallites with cubic symmetry; Patterson (1939) showed the correct
        value depends on the crystallite shape and on how the breadth is
        defined, ranging from about 0.89 to 1.0.
    instrumental_fwhm_deg : float
        Instrumental broadening to subtract in quadrature before applying
        the equation. Ignoring it makes the reported size too small.

    Returns
    -------
    float or None
        Size in nm, or None when the peak cannot support a size (FWHM wider
        than the 2-theta range or non-positive after correction).

    Notes
    -----
    Two corrections matter and are easy to omit:
    FWHM must be converted from 2-theta degrees to radians before use, and
    the instrumental broadening must be removed. This implementation does
    both. Sizes below roughly 2-3 nm are at the reliability limit of the
    Scherrer method and should be reported as approximate.

    The uncertainty is dominated by K, which alone spans about +/- 10 %.
    """
    if not (0.0 < two_theta_deg < 180.0):
        raise ValueError("two_theta_deg must be between 0 and 180.")
    if fwhm_deg <= 0:
        raise ValueError("fwhm_deg must be positive.")
    if wavelength_angstrom <= 0:
        raise ValueError("wavelength_angstrom must be positive.")
    if K <= 0:
        raise ValueError("The Scherrer constant K must be positive.")

    beta_obs = math.radians(fwhm_deg)
    beta_inst = math.radians(instrumental_fwhm_deg)
    # Subtract instrumental broadening in quadrature (Gaussian approximation).
    beta_sq = beta_obs**2 - beta_inst**2
    if beta_sq <= 0:
        return None
    beta = math.sqrt(beta_sq)

    theta = math.radians(two_theta_deg / 2.0)
    size_angstrom = K * wavelength_angstrom / (beta * math.cos(theta))
    if not math.isfinite(size_angstrom) or size_angstrom <= 0:
        return None
    return float(size_angstrom / 10.0)


def _find_peaks(
    x: np.ndarray, y: np.ndarray, prominence_frac: float = 0.05
) -> list[int]:
    """
    Local maxima above a prominence threshold, without a scipy dependency.

    Works on either axis direction: IR spectra are conventionally plotted
    with wavenumber decreasing, so the caller is not required to reorder.
    Indices index into the arrays as supplied.
    """
    if y.size < 3:
        return []
    rng = float(np.max(y) - np.min(y))
    if rng <= 0:
        return []
    threshold = float(np.min(y)) + prominence_frac * rng
    descending = x.size >= 2 and x[-1] < x[0]
    peaks: list[int] = []
    for i in range(1, y.size - 1):
        if descending:
            # In a descending axis a peak still means y is greater than both
            # neighbours, but the "x gap" comparison below must use absolute
            # differences, which it does.
            if y[i] >= y[i + 1] and y[i] > y[i - 1] and y[i] > threshold:
                peaks.append(i)
        else:
            if y[i] >= y[i - 1] and y[i] > y[i + 1] and y[i] > threshold:
                peaks.append(i)
    if peaks:
        kept = [peaks[0]]
        # Minimum separation between reported bands, as a fraction of the
        # scanned range. The previous threshold of 2 % discarded genuine
        # doublets: the CH2 asymmetric and symmetric stretches of a
        # hydrocarbon sit at 2920 and 2850 cm^-1, only 70 cm^-1 apart, which
        # is under 2 % of a 4000-400 sweep. 0.5 % separates real overlapping
        # instrument noise from genuine neighbouring bands on any ordinary
        # IR or XRD scan.
        min_gap = max(1e-9, 0.005 * abs(float(x[-1]) - float(x[0])))
        for p in peaks[1:]:
            if abs(float(x[p]) - float(x[kept[-1]])) >= min_gap:
                kept.append(p)
        peaks = kept
    return peaks


def _fwhm_at(x: np.ndarray, y: np.ndarray, idx: int) -> float | None:
    """
    Full width at half maximum by half-maximum crossings, with linear
    interpolation on both shoulders.
    """
    peak = float(y[idx])
    base = float(min(y[max(0, idx - 5)], y[min(y.size - 1, idx + 5)]))
    half = base + 0.5 * (peak - base)

    left = None
    for i in range(idx, 0, -1):
        if y[i] <= half <= y[i - 1] or y[i] >= half >= y[i - 1]:
            if y[i] != y[i - 1]:
                frac = (half - y[i]) / (y[i - 1] - y[i])
                left = x[i] + frac * (x[i - 1] - x[i])
            else:
                left = x[i]
            break
    right = None
    for i in range(idx, y.size - 1):
        if y[i] >= half >= y[i + 1] or y[i] <= half <= y[i + 1]:
            if y[i + 1] != y[i]:
                frac = (half - y[i]) / (y[i + 1] - y[i])
                right = x[i] + frac * (x[i + 1] - x[i])
            else:
                right = x[i]
            break

    if left is None or right is None or right <= left:
        return None
    return float(right - left)


def analyse_xrd(
    two_theta: Sequence[float],
    intensity: Sequence[float],
    wavelength_angstrom: float = 1.5406,
    K: float = 0.9,
    instrumental_fwhm_deg: float = 0.0,
    prominence_frac: float = 0.05,
) -> XRDResult:
    """
    Detect diffraction peaks, index them, and estimate crystallite size.

    Crystallinity is reported as the *crystallinity index*, the ratio of the
    integrated intensity of the resolved crystalline peaks to the total
    integrated intensity of the pattern. This is NOT the absolute degree of
    crystallinity. Alexander (1969) and Murthy & Minor (1990) show the index
    depends on the angular range measured, on the background chosen and on
    the amorphous halo model, so it is comparable between samples measured
    identically but not between laboratories. Absolute crystallinity needs
    the amorphous halo to be modelled or a DSC reference; the index is what
    this method can honestly deliver.
    """
    x = np.asarray(two_theta, dtype=np.float64)
    y = np.asarray(intensity, dtype=np.float64)
    if x.shape != y.shape:
        raise ValueError("two_theta and intensity must have the same length.")
    if x.size < 10:
        raise ValueError("At least 10 points are required for a diffraction pattern.")
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    order = np.argsort(x)
    x, y = x[order], y[order]
    if x.size < 10:
        raise ValueError("Fewer than 10 finite points remain.")

    if np.any(y < 0):
        raise ValueError("Intensity values must be non-negative.")

    peaks = _find_peaks(x, y, prominence_frac)
    peak_positions: list[float] = []
    d_spacings: list[float] = []
    sizes: list[float] = []
    fwhms: list[float] = []

    # Total integrated intensity over the measured range, after a linear
    # baseline from the endpoints, for the crystallinity index.
    base = np.linspace(float(y[0]), float(y[-1]), y.size)
    excess = np.clip(y - base, 0.0, None)
    total_area = float(np.trapezoid(excess, x))

    peak_area = 0.0
    for idx in peaks:
        tw = float(x[idx])
        theta = math.radians(tw / 2.0)
        s = math.sin(theta)
        # A peak that cannot be converted to a d-spacing or does not have a
        # measurable width is dropped rather than reported as NaN. NaN is not
        # valid JSON, so emitting it crashed the endpoint with a 500 the moment
        # real instrument data arrived: traces from a Nika/DIFFRAC export carry
        # many narrow spikes whose width falls below the sampling interval.
        # Keeping the arrays parallel and shorter is the honest representation.
        if s <= 0:
            continue
        d = wavelength_angstrom / (2.0 * s)
        if not math.isfinite(d):
            continue

        fw = _fwhm_at(x, y, idx)
        if fw is None or not math.isfinite(fw) or fw <= 0:
            continue

        size = scherrer_crystallite_size(
            tw, fw, wavelength_angstrom, K, instrumental_fwhm_deg
        )
        if size is None or not math.isfinite(size):
            continue

        peak_positions.append(tw)
        d_spacings.append(float(d))
        fwhms.append(float(fw))
        sizes.append(float(size))

        # Area of this peak: integrate the excess above a local baseline
        # halfway down to the neighbouring minima.
        half = base[idx] + 0.5 * (y[idx] - base[idx])
        a = idx
        while a > 0 and y[a] > half:
            a -= 1
        b = idx
        while b < y.size - 1 and y[b] > half:
            b += 1
        if b > a:
            local_base = np.linspace(float(y[a]), float(y[b]), b - a + 1)
            peak_area += float(np.trapezoid(np.clip(y[a : b + 1] - local_base, 0, None), x[a : b + 1]))

    crystallinity = None
    if total_area > 0 and peak_area > 0:
        raw_fraction = 100.0 * peak_area / total_area
        # If the straight-line baseline sits below every measured point, the
        # whole pattern counts as crystalline and the index saturates at 100 %.
        # That happens on data whose amorphous halo decays steeply with angle
        # (a q-space profile on an arbitrary-units scale, where the intensity
        # falls by half across the range): a chord baseline cuts through the
        # halo instead of following it, and the index stops being meaningful.
        # Reported as None rather than 100 %, because a saturated index is not
        # a measurement of anything - the amorphous reference is missing.
        if raw_fraction >= 99.9 and int(np.sum(y < base)) == 0:
            crystallinity = None
        else:
            crystallinity = float(min(100.0, raw_fraction))

    return XRDResult(
        peaks_two_theta=peak_positions,
        d_spacing_angstrom=d_spacings,
        crystallite_size_nm=sizes,
        fwhm_deg=fwhms,
        crystallinity_pct=crystallinity,
        wavelength_angstrom=wavelength_angstrom,
        two_theta=[float(v) for v in x],
        intensity=[float(v) for v in y],
    )


# --------------------------------------------------------------------------
# FTIR
# --------------------------------------------------------------------------

#: Characteristic infrared absorption bands. Positions are the commonly cited
#: ranges from Socrates (2001) and Coates (2000); a band is matched when the
#: observed wavenumber falls inside the window.
FTIR_REFERENCE_BANDS: list[dict[str, object]] = [
    {"name": "O-H stretch (alcohol, phenol)", "low": 3200, "high": 3600, "intensity": "strong, broad", "note": "Broad; water contamination gives the same band."},
    {"name": "N-H stretch (amine, amide)", "low": 3300, "high": 3500, "intensity": "medium", "note": "Two bands for primary amines, one for secondary."},
    {"name": "C-H stretch (alkyne, terminal)", "low": 3260, "high": 3330, "intensity": "strong, sharp", "note": "Accompanied by C#C near 2100-2260."},
    {"name": "C-H stretch (aromatic)", "low": 3000, "high": 3100, "intensity": "medium", "note": "Often several weak bands above 3000."},
    {"name": "C-H stretch (alkane, CH3/CH2)", "low": 2850, "high": 2960, "intensity": "strong", "note": "The most common band in polyolefins."},
    {"name": "C-H stretch (alkene)", "low": 3010, "high": 3095, "intensity": "medium", "note": "Differentiate from aromatic by the 1600 ring band."},
    {"name": "C=O stretch (ester)", "low": 1735, "high": 1750, "intensity": "very strong", "note": "PET, PMMA, acrylates."},
    {"name": "C=O stretch (aldehyde)", "low": 1720, "high": 1740, "intensity": "strong", "note": "Paired with a C-H doublet near 2720-2820."},
    {"name": "C=O stretch (ketone)", "low": 1705, "high": 1725, "intensity": "very strong", "note": "Polycarbonate, PEEK."},
    {"name": "C=O stretch (carboxylic acid)", "low": 1700, "high": 1725, "intensity": "strong", "note": "Broad O-H envelope 2500-3300 accompanies."},
    {"name": "C=O stretch (amide, Amide I)", "low": 1630, "high": 1690, "intensity": "strong", "note": "Nylon, Kevlar; pair with Amide II near 1540."},
    {"name": "C=C stretch (alkene)", "low": 1620, "high": 1680, "intensity": "medium", "note": "Weak when the alkene is symmetric."},
    {"name": "C=C stretch (aromatic ring)", "low": 1450, "high": 1600, "intensity": "medium", "note": "Often two or more sharp bands."},
    {"name": "C-H bend (CH2 scissor)", "low": 1455, "high": 1475, "intensity": "medium", "note": "Present in nearly every aliphatic polymer."},
    {"name": "C-H bend (CH3 umbrella)", "low": 1375, "high": 1385, "intensity": "medium", "note": "Splits into a doublet for gem-dimethyl groups."},
    {"name": "S=O stretch (sulfone)", "low": 1150, "high": 1350, "intensity": "strong", "note": "Polysulfone, PES."},
    {"name": "C-O stretch (ester, two bands)", "low": 1150, "high": 1300, "intensity": "strong", "note": "C-O-C asymmetric and symmetric."},
    {"name": "C-O stretch (ether)", "low": 1050, "high": 1150, "intensity": "strong", "note": "PEO, POM."},
    {"name": "C-O stretch (alcohol)", "low": 1000, "high": 1260, "intensity": "strong", "note": "PVA, cellulose."},
    {"name": "C-N stretch (amine)", "low": 1020, "high": 1250, "intensity": "medium", "note": "Weak; use with the N-H band."},
    {"name": "C-Cl stretch", "low": 600, "high": 800, "intensity": "strong", "note": "PVC."},
    {"name": "C-F stretch", "low": 1000, "high": 1400, "intensity": "very strong", "note": "PTFE, PVDF."},
    {"name": "C#C stretch (alkyne)", "low": 2100, "high": 2260, "intensity": "weak", "note": "Absent when the alkyne is symmetric."},
    {"name": "C#N stretch (nitrile)", "low": 2210, "high": 2260, "intensity": "medium", "note": "PAN, ABS."},
    {"name": "N=C=O stretch (isocyanate)", "low": 2240, "high": 2280, "intensity": "very strong", "note": "Polyurethane precursors; diagnostic."},
    {"name": "O-C=O bend (ester, broad)", "low": 1180, "high": 1300, "intensity": "strong", "note": "Pairs with the 1735-1750 C=O."},
    {"name": "Si-O-Si stretch", "low": 1000, "high": 1100, "intensity": "very strong", "note": "Silicones, silica filler."},
    {"name": "N-H bend (Amide II)", "low": 1510, "high": 1570, "intensity": "strong", "note": "Confirms an amide together with Amide I."},
    {"name": "N-O stretch (nitro)", "low": 1500, "high": 1560, "intensity": "strong", "note": "Paired with 1300-1390."},
]


@dataclass
class FTIRResult:
    """FTIR band-matching result."""

    #: Bands matched, each with the reference entry and the observed peak.
    matches: list[dict[str, object]] = field(default_factory=list)
    #: Detected peak positions in wavenumber order (cm^-1), descending.
    detected_peaks: list[float] = field(default_factory=list)
    #: Detected peak heights, normalised to 1.0 at the strongest peak.
    detected_peaks_rel: list[float] = field(default_factory=list)
    #: Disclaimer carried through to the API response.
    note: str = (
        "Band assignment is indicative only. Infrared cannot identify a "
        "polymer uniquely: many polymers share the same functional groups, "
        "and additives, plasticisers and moisture contribute their own bands. "
        "Confirm any assignment against a reference spectrum of the suspected "
        "material measured on the same instrument."
    )

    def as_dict(self) -> dict[str, object]:
        return {
            "matches": self.matches,
            "detected_peaks": self.detected_peaks,
            "detected_peaks_rel": self.detected_peaks_rel,
            "note": self.note,
        }


def analyse_ftir(
    wavenumber: Sequence[float],
    absorbance: Sequence[float],
    prominence_frac: float = 0.08,
    tolerance_cm1: float = 0.0,
) -> FTIRResult:
    """
    Detect absorption bands and match them against a reference table.

    Parameters
    ----------
    wavenumber : sequence
        Wavenumbers in cm^-1. IR spectra are conventionally plotted with the
        axis decreasing left to right; either order is accepted.
    absorbance : sequence
        Absorbance (or transmittance converted to absorbance). Must be
        non-negative.
    prominence_frac : float
        Minimum peak height, as a fraction of the total absorbance range, for
        a band to be reported. Raise it for noisy spectra.
    tolerance_cm1 : float
        Extra tolerance added to each side of every reference window, to
        allow for instrument calibration differences and for shifts caused
        by hydrogen bonding. 0 uses the tabulated windows as given.

    Notes
    -----
    This is a library lookup, not a classifier. It reports which functional
    groups *could* give rise to the observed bands. It does not rank polymer
    candidates and must not be presented as an identification.
    """
    x = np.asarray(wavenumber, dtype=np.float64)
    y = np.asarray(absorbance, dtype=np.float64)
    if x.shape != y.shape:
        raise ValueError("wavenumber and absorbance must have the same length.")
    if x.size < 10:
        raise ValueError("At least 10 points are required for a spectrum.")
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if x.size < 10:
        raise ValueError("Fewer than 10 finite points remain.")
    if np.any(y < 0):
        raise ValueError(
            "Absorbance must be non-negative. Convert transmittance with "
            "A = -log10(T) first."
        )
    # Transmittance passed in place of absorbance is the commonest unit error
    # here, because the instrument exports %T and the tool asks for absorbance.
    # It used to be accepted silently and produced ~100 peaks per spectrum
    # instead of ~16: a transmittance band is a large monotonic ramp, and the
    # peak finder reads every ripple along it. Measured on the 59 real FTIR
    # spectra from figshare 24593022, 57 of 58 gave an implausible count when
    # passed as exported, against 48 of 52 once converted. A direct check on
    # PE-1: 103 peaks starting at 3998 cm^-1 as %T, against exactly the four
    # CH2 bands (2915, 2848, 1473, 730 cm^-1) as absorbance.
    #
    # What separates the two units is the scale, and it separates by a wide
    # margin. Measured across those spectra:
    #     transmittance: max 97-100, median ~94-99
    #     absorbance   : max 0.07-4.2, median 0.00-0.02
    # that is a factor of ~25 in the maximum with no overlap. A trend or slope
    # test does not work -- a synthetic %T trace with a flat baseline and a real
    # one give nearly the same trend ratio (0.074 vs 0.061), because the band
    # structure dominates it.
    #
    # The threshold is set on the maximum only. Absorbance above 4 is not
    # physically meaningful for a transmission measurement anyway (that is
    # 0.01 %T), so refusing it costs nothing real, while no plausible
    # absorbance spectrum reaches the 50 that this requires.
    if x.size >= 10 and float(np.max(y)) > 50.0:
        raise ValueError(
            "This looks like transmittance, not absorbance: the values reach "
            f"{float(np.max(y)):.1f}. Convert with A = -log10(T/100) before "
            "calling this function, and drop any saturated point where T = 0 "
            "or the logarithm is infinite."
        )
    if np.ptp(x) <= 0:
        raise ValueError("Wavenumber values must not all be identical.")

    peaks = _find_peaks(x, y, prominence_frac)
    order_desc = np.argsort([-x[p] for p in peaks])
    peaks_desc = [peaks[i] for i in order_desc]

    detected = [float(x[p]) for p in peaks_desc]
    max_h = max((float(y[p]) for p in peaks), default=1.0) or 1.0
    rel = [float(y[p]) / max_h for p in peaks_desc]

    matches: list[dict[str, object]] = []
    for idx, wn in zip(peaks_desc, detected, strict=False):
        # Report EVERY reference band whose window contains the observed peak.
        # Picking a single "best" band would imply a certainty this method
        # does not have: at 1715 cm^-1 a ketone and a carboxylic acid are
        # genuinely indistinguishable without the accompanying O-H envelope,
        # so the user is given both candidates.
        candidates: list[dict[str, object]] = []
        for band in FTIR_REFERENCE_BANDS:
            low = float(band["low"]) - tolerance_cm1  # type: ignore[arg-type]
            high = float(band["high"]) + tolerance_cm1  # type: ignore[arg-type]
            if low <= wn <= high:
                candidates.append(
                    {
                        "assignment": band["name"],
                        "reference_range_cm1": [band["low"], band["high"]],
                        "expected_intensity": band["intensity"],
                        "note": band["note"],
                    }
                )
        if candidates:
            matches.append(
                {
                    "observed_cm1": wn,
                    "relative_height": float(y[idx]) / max_h,
                    "candidates": candidates,
                }
            )

    return FTIRResult(
        matches=matches,
        detected_peaks=detected,
        detected_peaks_rel=rel,
    )
