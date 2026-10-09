"""Thermal module: TGA and DSC trace analysis."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.api.v1.schemas import (
    DSCResult,
    DSCTraceInput,
    FieldClaim,
    PropertyComparison,
    TGAResult,
    TGAStep,
    TGATraceInput,
    TraceAnalysis,
    TraceColumn,
    TracePreview,
)
from app.core.compare import compare_result
from app.core.thermal import analyse_dsc, analyse_tga
from app.core.trace_io import TraceImportError, read_trace_file, resolve_trace

router = APIRouter(prefix="/thermal", tags=["Thermal Analysis"])


#: Pontos por grau abaixo dos quais uma transição vítrea não é localizável.
#:
#: Um DSC a 10 K/min amostra tipicamente 10 a 100 pontos por grau, e o degrau
#: de uma Tg ocupa poucos graus, então há pontos suficientes para descrever a
#: forma. Um export esparso -- o arquivo de LDPE que motivou isto tem 186
#: pontos em 185 graus, isto é 1,0 ponto por grau -- não descreve o degrau: o
#: que o detector encontrar nele é a curvatura da linha de base. Um pico de
#: fusão é largo o bastante para sobreviver, então o limiar se aplica à Tg e
#: não ao arquivo inteiro.
_MIN_POINTS_PER_DEGREE = 4.0

#: O que cada módulo pede como eixo x e como sinal.
_TRACE_ROLES = {
    "tga": ("temperature", "mass"),
    "dsc": ("temperature", "heat_flow"),
}


@router.post(
    "/import",
    response_model=TracePreview,
    summary="Inspect an instrument file before analysing it",
    response_description=(
        "Every column found, its role and unit, the metadata from the "
        "instrument header, and the two series resolved onto the requested axes."
    ),
)
async def import_trace_endpoint(
    file: UploadFile = File(
        ..., description="A trace file as the instrument wrote it."
    ),
    target: str = Form(
        "dsc",
        description=(
            "Which analysis the file is for: 'dsc' (temperature + heat flow), "
            "'tga' (temperature + mass)."
        ),
    ),
) -> TracePreview:
    """
    Read an instrument file and report what was found, without analysing it.

    This is the step between the instrument's export and the analysis. A DSC
    file from a NETZSCH instrument, for example, has four columns whose second
    is *time*, a semicolon delimiter declared in the header, a latin-1 ``°``
    that breaks a naive UTF-8 read, ``#EXO:-1`` for the sign convention and the
    heating rate buried in ``#RANGE``. Reading it as "first column x, second
    column y" silently analyses the time axis.

    Call this when a result looks wrong: ``columns`` states what each column
    was taken to be, and ``notes`` lists every decision the reader made.
    """
    target_key = target.strip().lower()
    if target_key not in _TRACE_ROLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown target '{target}'. Use one of: "
                f"{', '.join(sorted(_TRACE_ROLES))}."
            ),
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # read_trace_file takes a path; the upload only exists in memory. A
    # temporary file keeps one reading path for both the API and the CLI,
    # instead of a second parser that could drift from it.
    suffix = Path(file.filename or "upload").suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        tf = read_trace_file(tmp_path)
    except TraceImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:  # pragma: no cover - filesystem, not input
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    x_role, y_role = _TRACE_ROLES[target_key]
    preview = TracePreview(
        columns=[
            TraceColumn(
                index=c.index,
                header=c.raw_header,
                role=c.role,
                unit=c.unit,
                n_values=len(c.values),
            )
            for c in tf.columns
        ],
        metadata=tf.metadata,
        sample_name=tf.sample_name,
        sample_mass_mg=tf.sample_mass_mg,
        heating_rate_K_min=tf.heating_rate,
        exothermic_direction=tf.exothermic_direction,
    )

    try:
        resolved = resolve_trace(
            tf, x_role, y_role, invert_for_endothermic_up=(target_key == "dsc")
        )
    except TraceImportError as exc:
        # Not fatal for the endpoint's purpose: the preview is still useful,
        # and the reason the trace could not be resolved is the answer to the
        # question asked. Returning 400 here would hide the column listing
        # that explains it.
        preview.notes.append(f"não resolvido: {exc}")
        return preview

    preview.temperature = resolved.x
    preview.signal = resolved.y
    preview.x_label = resolved.x_label
    preview.y_label = resolved.y_label
    preview.notes.extend(resolved.notes)
    if resolved.heating_rate is not None:
        preview.heating_rate_K_min = resolved.heating_rate

    # A densidade de amostragem decide o que a análise pode afirmar, então é
    # reportada em vez de deixada implícita. Um DSC a 10 K/min amostra dezenas
    # de pontos por grau; uma transição de alguns graus de largura sobrevive a
    # isso. Um arquivo com 186 pontos ao longo de 185 graus tem um ponto por
    # grau, e nesse caso o degrau da Tg é mais estreito que o espaçamento --
    # nenhum detector pode localizá-lo. A ferramenta deve dizer isso em vez de
    # devolver um número que parece um resultado.
    n = len(resolved.x)
    span = abs(resolved.x[-1] - resolved.x[0]) if n > 1 else 0.0
    preview.sample_size_points = n
    if span > 0:
        ppd = n / span
        preview.points_per_degree = round(ppd, 3)
        if ppd < _MIN_POINTS_PER_DEGREE:
            preview.notes.append(
                f"O traço tem {ppd:.1f} ponto(s) por grau ({n} pontos em "
                f"{span:.0f} graus). Abaixo de {_MIN_POINTS_PER_DEGREE:.0f} "
                "pontos por grau o degrau de uma transição vítrea é mais "
                "estreito que o espaçamento, e nenhum detector pode localizá-lo: "
                "um valor de Tg reportado neste arquivo é ruído da linha de "
                "base, não uma transição. O pico de fusão, que é largo, "
                "continua utilizável."
            )
    return preview


@router.post(
    "/analyse",
    response_model=TraceAnalysis,
    summary="Analyse an uploaded instrument file in one step",
    response_description="The module's result, plus the provenance of the data.",
)
async def analyse_trace_endpoint(
    file: UploadFile = File(
        ..., description="A trace file as the instrument wrote it."
    ),
    target: str = Form(
        "dsc", description="Which analysis to run: 'dsc' or 'tga'."
    ),
    ref_enthalpy_J_g: float | None = Form(
        None,
        gt=0,
        description=(
            "Melting enthalpy of a 100 % crystalline reference, for a DSC "
            "crystallinity. Omitted, the crystallinity is not reported."
        ),
    ),
) -> TraceAnalysis:
    """
    Read an instrument file and analyse it, in one call.

    This is the shortcut for ``/import`` followed by the relevant analysis
    endpoint, for callers that do not need to inspect the parse first. The
    response carries the module's result unchanged, plus what the reader
    decided -- the columns, the metadata from the instrument header, and any
    step that could not be carried out with a reason.

    The heating rate is taken from the instrument header when the file states
    it, so an enthalpy comes out in J/g rather than per degree. When the file
    does not state it, the enthalpy is still reported but the crystallinity is
    not, because it would need a rate.
    """
    target_key = target.strip().lower()
    if target_key not in _TRACE_ROLES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown target '{target}'. Use one of: "
                f"{', '.join(sorted(_TRACE_ROLES))}."
            ),
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    suffix = Path(file.filename or "upload").suffix or ".txt"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        tf = read_trace_file(tmp_path)
    except TraceImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    x_role, y_role = _TRACE_ROLES[target_key]
    try:
        resolved = resolve_trace(
            tf, x_role, y_role, invert_for_endothermic_up=(target_key == "dsc")
        )
    except TraceImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    notes = list(resolved.notes)
    refusals: list[str] = []

    if target_key == "dsc":
        if resolved.heating_rate is None:
            refusals.append(
                "O arquivo não declara a taxa de aquecimento, então a "
                "cristalinidade não foi calculada. O ΔHm é reportado em "
                "J/g apenas se a taxa for fornecida."
            )
        elif ref_enthalpy_J_g is None:
            refusals.append(
                "Nenhuma entalpia de referência foi fornecida, então a "
                "cristalinidade não foi calculada (ΔHm é reportado)."
            )
        r = analyse_dsc(
            resolved.x,
            resolved.y,
            heating_rate=resolved.heating_rate,
            ref_enthalpy_J_g=ref_enthalpy_J_g,
        )
    else:
        r = analyse_tga(resolved.x, resolved.y)

    n = len(resolved.x)
    span = abs(resolved.x[-1] - resolved.x[0]) if n > 1 else 0.0
    points_per_degree = (n / span) if span > 0 else None
    too_sparse = points_per_degree is not None and points_per_degree < _MIN_POINTS_PER_DEGREE
    if too_sparse:
        refusals.append(
            f"O traço tem {points_per_degree:.1f} ponto(s) por grau. Abaixo de "
            f"{_MIN_POINTS_PER_DEGREE:.0f} nenhuma temperatura de transição "
            "vítrea é localizável neste arquivo; um pico largo, como o de "
            "fusão, continua utilizável."
        )

    payload = r.as_dict() if hasattr(r, "as_dict") else {}

    # Retirar a Tg em vez de reportá-la com uma ressalva.
    #
    # Dizer "a amostragem é esparsa demais para localizar uma transição vítrea"
    # e ao mesmo tempo devolver `Tg: 22.9` é contraditório: o número viaja, o
    # aviso fica. Um leitor que consome a API vê o campo preenchido. Pela
    # mesma razão que o módulo se recusa a reportar uma cristalinidade sem
    # entalpia de referência, ele não deve reportar uma Tg que a densidade de
    # amostragem torna impossível — o campo sai, com o motivo em `refusals`.
    if too_sparse and payload:
        removed = [k for k in ("Tg", "Tg_onset", "Tg_end", "delta_cp") if payload.get(k) is not None]
        for key in removed:
            payload[key] = None
        if "claims" in payload and isinstance(payload["claims"], dict):
            for key in removed:
                payload["claims"].pop(key, None)
        if removed:
            refusals.append(
                "Os campos "
                + ", ".join(f"'{k}'" for k in removed)
                + " foram omitidos por não serem localizáveis neste arquivo."
            )

    return TraceAnalysis(
        target=target_key,
        result=payload,
        sample_name=resolved.sample_name,
        sample_mass_mg=resolved.sample_mass_mg,
        heating_rate_K_min=resolved.heating_rate,
        exothermic_direction=resolved.exothermic_direction,
        x_label=resolved.x_label,
        y_label=resolved.y_label,
        columns=[
            TraceColumn(
                index=c.index,
                header=c.raw_header,
                role=c.role,
                unit=c.unit,
                n_values=len(c.values),
            )
            for c in tf.columns
        ],
        notes=notes,
        refusals=refusals,
    )


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

    comparisons = compare_result(
        payload.sample_name,
        {"Tg": r.Tg, "Tm": r.Tm, "delta_Hm": r.delta_Hm},
        claims=r.claims,
    )
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
        comparisons=[PropertyComparison(**c.as_dict()) for c in comparisons],
    )
