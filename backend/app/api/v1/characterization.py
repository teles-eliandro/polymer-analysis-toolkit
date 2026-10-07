"""Mechanical, rheology and structure modules."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.v1.schemas import (
    FTIRInput,
    FTIRMatch,
    FTIRResult,
    RheologyInput,
    RheologyResult,
    TensileInput,
    TensileResult,
    XRDInput,
    XRDResult,
)
from app.core.mechanical import analyse_tensile
from app.core.rheology import analyse_rheology
from app.core.structure import analyse_ftir, analyse_xrd

router = APIRouter(tags=["Mechanical, Rheology and Structure"])


@router.post(
    "/mechanical/tensile",
    response_model=TensileResult,
    summary="Tensile properties from a stress-strain curve",
    response_description="Modulus, strengths, elongations, toughness.",
)
async def tensile_endpoint(payload: TensileInput) -> TensileResult:
    """
    Compute tensile properties from an engineering stress-strain curve.

    Supply ``strain_pct`` (percent) and ``stress_MPa`` (MPa).

    The modulus is the slope of the initial linear region. Note the unit
    conversion this requires: a slope measured in MPa per *percent* strain is
    a hundred times smaller than the modulus in MPa, and reporting it without
    the correction understates E by two orders of magnitude. The strain window
    actually used for the regression is returned in ``modulus_window`` so the
    value can be checked.

    Toughness is the area under the curve, in MJ/m^3. It is a work-to-fracture
    measure and inherits every error in the strain measurement, so treat it as
    the least precise number here.
    """
    try:
        window = (
            (float(payload.modulus_window[0]), float(payload.modulus_window[1]))
            if payload.modulus_window
            else None
        )
        r = analyse_tensile(payload.strain_pct, payload.stress_MPa, modulus_window=window)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TensileResult(
        E_MPa=r.E_MPa,
        stress_break_MPa=r.stress_break_MPa,
        strain_break_pct=r.strain_break_pct,
        stress_max_MPa=r.stress_max_MPa,
        strain_max_pct=r.strain_max_pct,
        stress_yield_MPa=r.stress_yield_MPa,
        strain_yield_pct=r.strain_yield_pct,
        toughness_MJ_m3=r.toughness_MJ_m3,
        yielded=r.yielded,
        brittle=r.brittle,
        modulus_window=list(r.modulus_window) if r.modulus_window else None,
        strain_pct=r.strain_pct,
        stress_MPa=r.stress_MPa,
    )


@router.post(
    "/rheology/sweep",
    response_model=RheologyResult,
    summary="Analyse a frequency sweep",
    response_description="Crossover, plateau modulus, terminal slopes, gel test.",
)
async def rheology_endpoint(payload: RheologyInput) -> RheologyResult:
    """
    Analyse a small-amplitude oscillatory shear frequency sweep.

    Supply ``omega`` (rad/s), ``G_prime`` and ``G_double_prime`` (Pa).

    Useful cross-checks on the measurement itself:

    * ``terminal_slope_Gprime`` and ``terminal_slope_Gpp`` should approach 2
      and 1 for a narrow-distribution linear melt in the terminal zone. Values
      well below that mean the sweep did not reach the terminal regime, so
      ``zero_shear_viscosity_Pas`` and ``plateau_modulus_G0`` are not
      meaningful for it.
    * ``gel_point_detected`` reports whether tan(delta) is frequency
      independent, the Winter-Chambon criterion for a critical gel. It is a
      diagnostic, not a proof: a filled or inhomogeneous melt can also show a
      flat tan(delta).
    """
    try:
        r = analyse_rheology(
            payload.omega,
            payload.G_prime,
            payload.G_double_prime,
            gel_tolerance=payload.gel_tolerance,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RheologyResult(
        cross_over_freq=r.cross_over_freq,
        cross_over_modulus=r.cross_over_modulus,
        solid_like_at_low_freq=r.solid_like_at_low_freq,
        plateau_modulus_G0=r.plateau_modulus_G0,
        relaxation_time_s=r.relaxation_time_s,
        terminal_slope_Gprime=r.terminal_slope_Gprime,
        terminal_slope_Gpp=r.terminal_slope_Gpp,
        zero_shear_viscosity_Pas=r.zero_shear_viscosity_Pas,
        gel_point_detected=r.gel_point_detected,
        tan_delta_spread=r.tan_delta_spread,
        omega=r.omega,
        G_prime=r.G_prime,
        G_double_prime=r.G_double_prime,
        tan_delta=r.tan_delta,
    )


@router.post(
    "/structure/xrd",
    response_model=XRDResult,
    summary="Index an X-ray diffraction pattern",
    response_description="Peak positions, d-spacings and crystallite sizes.",
)
async def xrd_endpoint(payload: XRDInput) -> XRDResult:
    """
    Detect diffraction peaks, index them, and estimate crystallite size.

    Crystallite size comes from the Scherrer equation. Two corrections are
    applied that are easy to omit and both bias the answer low if missed: the
    peak width is converted from degrees to radians, and the instrumental
    broadening is subtracted in quadrature. Supply
    ``instrumental_fwhm_deg`` measured on a standard such as LaB6 or silicon;
    leaving it at zero makes every size an underestimate.

    ``crystallinity_pct`` is the crystallinity *index* - crystalline peak area
    over total area for this particular scan. It is not the absolute degree of
    crystallinity and is comparable only between samples measured with the
    same range, baseline and slits.
    """
    try:
        r = analyse_xrd(
            payload.two_theta,
            payload.intensity,
            wavelength_angstrom=payload.wavelength_angstrom,
            K=payload.K,
            instrumental_fwhm_deg=payload.instrumental_fwhm_deg,
            prominence_frac=payload.prominence_frac,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return XRDResult(
        peaks_two_theta=r.peaks_two_theta,
        d_spacing_angstrom=r.d_spacing_angstrom,
        crystallite_size_nm=r.crystallite_size_nm,
        fwhm_deg=r.fwhm_deg,
        crystallinity_pct=r.crystallinity_pct,
        wavelength_angstrom=r.wavelength_angstrom,
        two_theta=r.two_theta,
        intensity=r.intensity,
    )


@router.post(
    "/structure/ftir",
    response_model=FTIRResult,
    summary="Match infrared bands to functional groups",
    response_description="Detected bands with every candidate assignment.",
)
async def ftir_endpoint(payload: FTIRInput) -> FTIRResult:
    """
    Detect absorption bands and match them against a reference table.

    Supply ``wavenumber`` (cm^-1, either direction is accepted) and
    ``absorbance``. Convert transmittance with A = -log10(T) first.

    Every reference band whose window contains an observed peak is returned as
    a candidate, rather than a single best guess. This is deliberate: a band
    at 1715 cm^-1 is a ketone or a carboxylic acid depending on whether a
    broad O-H envelope accompanies it, and choosing between them
    automatically would hide that ambiguity rather than expose it.

    This endpoint does not identify a polymer. It reports which functional
    groups could produce the observed bands.
    """
    try:
        r = analyse_ftir(
            payload.wavenumber,
            payload.absorbance,
            prominence_frac=payload.prominence_frac,
            tolerance_cm1=payload.tolerance_cm1,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FTIRResult(
        matches=[
            FTIRMatch(
                observed_cm1=m["observed_cm1"],  # type: ignore[arg-type]
                relative_height=m["relative_height"],  # type: ignore[arg-type]
                candidates=m["candidates"],  # type: ignore[arg-type]
            )
            for m in r.matches
        ],
        detected_peaks=r.detected_peaks,
        detected_peaks_rel=r.detected_peaks_rel,
        note=r.note,
    )
