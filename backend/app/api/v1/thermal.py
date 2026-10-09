"""Thermal module: TGA and DSC trace analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.v1.schemas import (
    DSCResult,
    DSCTraceInput,
    FieldClaim,
    TGAResult,
    TGAStep,
    TGATraceInput,
)
from app.core.thermal import analyse_dsc, analyse_tga

router = APIRouter(prefix="/thermal", tags=["Thermal Analysis"])


@router.post(
    "/tga",
    response_model=TGAResult,
    summary="Analyse a TGA trace",
    response_description="Td at 5 % and 10 %, DTG peak, residue and decomposition steps.",
)
async def tga_endpoint(payload: TGATraceInput) -> TGAResult:
    """
    Analyse a thermogravimetric trace.

    Supply ``temperature`` (Celsius) and ``mass_pct`` (mass remaining, in
    percent). Td is reported at 5 % and 10 % mass loss, which are the
    conventional degradation-onset measures for polymers; the residue is the
    mass remaining at the end of the run.

    ``T_max_rate`` is the tallest DTG peak. When a sample decomposes in
    several steps this is the step that loses mass fastest - not necessarily
    the first one - so read it together with ``steps``.
    """
    try:
        r = analyse_tga(
            payload.temperature, payload.mass_pct, smooth_window=payload.smooth_window
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TGAResult(
        Td_5pct=r.Td_5pct,
        Td_10pct=r.Td_10pct,
        T_max_rate=r.T_max_rate,
        T_95pct=r.T_95pct,
        residue_pct=r.residue_pct,
        steps=[TGAStep(**s) for s in r.steps],
        unattributed_loss_pct=r.unattributed_loss_pct,
        notes=r.notes,
        temperature=r.temperature,
        mass_pct=r.mass_pct,
        dtg=r.dtg,
    )


@router.post(
    "/dsc",
    response_model=DSCResult,
    summary="Analyse a DSC trace",
    response_description="Tg, Tm, enthalpies and optional crystallinity.",
)
async def dsc_endpoint(payload: DSCTraceInput) -> DSCResult:
    """
    Analyse a differential scanning calorimetry trace.

    Supply ``temperature`` (Celsius) and ``heat_flow`` (W/g, endothermic up).

    * Tg is reported by the ASTM D3418 midpoint convention: the mid-point
      between the extrapolated onset and the end of the heat-capacity step.
      The melting region is excluded before the step is located, otherwise a
      sharp melting peak is mistaken for the glass transition.
    * Tm is the peak of the melting endotherm.
    * ``delta_Hm`` is in J/g and requires ``heating_rate``, because the
      enthalpy is obtained by integrating a signal in W/g over temperature and
      the conversion needs the scan rate.
    * ``crystallinity_pct`` requires ``ref_enthalpy_J_g``, the melting
      enthalpy of the same polymer in a 100 % crystalline state. Use the value
      from the literature for the specific polymorph.

    A single heating scan cannot separate the thermal history of the sample
    from its intrinsic behaviour. For a defensible Tg, run a heat-cool-heat
    cycle and use the second heating.
    """
    try:
        r = analyse_dsc(
            payload.temperature,
            payload.heat_flow,
            heating_rate=payload.heating_rate,
            ref_enthalpy_J_g=payload.ref_enthalpy_J_g,
            smooth_window=payload.smooth_window,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DSCResult(
        Tg=r.Tg,
        Tg_onset=r.Tg_onset,
        Tg_end=r.Tg_end,
        delta_cp=r.delta_cp,
        Tm=r.Tm,
        delta_Hm=r.delta_Hm,
        Tc=r.Tc,
        delta_Hc=r.delta_Hc,
        crystallinity_pct=r.crystallinity_pct,
        Tg_uncertainty_C=r.Tg_uncertainty_C,
        Tg_reliable=r.Tg_reliable,
        temperature=r.temperature,
        heat_flow=r.heat_flow,
        direction=r.direction,
        claims={
            k: FieldClaim(
                value=v.value,
                confidence=v.confidence,
                evidence=list(v.evidence),
                note=v.note,
            )
            for k, v in r.claims.items()
        },
    )
