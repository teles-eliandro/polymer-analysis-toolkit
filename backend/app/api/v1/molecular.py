"""Molecular module: molar-mass averages from a weight distribution."""

from __future__ import annotations

import numpy as np
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import ValidationError

from app.api.v1.schemas import (
    ImportPreview,
    MolecularInput,
    MolecularResult,
)
from app.core.ingest import ImportError_, parse_distribution_csv
from app.core.molar_mass import (
    DEFAULT_SUM_TOL,
    mark_houwink_viscosity_average,
    moment_averages,
)

router = APIRouter(prefix="/molecular", tags=["Molecular Analysis"])

# Accepted content types are no longer used to reject uploads: a browser
# FormData sends application/octet-stream and a curl -F sends text/csv for the
# same file. Validation is done on the parsed content instead. This constant
# is kept only to document what instruments and browsers send in practice.
CUSTOM_MIME_TYPES = [
    "text/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
    "text/plain",
    "application/csv",
]


def _build_result(
    masses: list[float],
    weight_fractions: list[float],
    normalise: bool,
    mark_houwink_a: float | None,
) -> MolecularResult:
    arr_w = np.asarray(weight_fractions, dtype=np.float64)
    fraction_sum = float(np.sum(arr_w))
    was_normalised = False

    if normalise:
        if fraction_sum <= 0:
            raise HTTPException(
                status_code=400,
                detail="Weight fractions sum to zero, so they cannot be normalised.",
            )
        weight_fractions = [float(v) / fraction_sum for v in arr_w]
        was_normalised = True

    try:
        res = moment_averages(masses, weight_fractions, tol=DEFAULT_SUM_TOL)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    Mv = None
    if mark_houwink_a is not None:
        try:
            Mv = mark_houwink_viscosity_average(
                masses, weight_fractions, mark_houwink_a, tol=DEFAULT_SUM_TOL
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MolecularResult(
        Mn=res.Mn,
        Mw=res.Mw,
        Mz=res.Mz,
        Mz_plus_1=res.Mz_plus_1,
        dispersity=res.dispersity,
        Mv=Mv,
        mark_houwink_a=mark_houwink_a,
        n_slices=len(masses),
        fraction_sum_input=fraction_sum,
        normalised=was_normalised,
    )


@router.post(
    "/calc",
    response_model=MolecularResult,
    summary="Calculate molar-mass averages",
    response_description="Mn, Mw, Mz, Mz+1, dispersity and optional Mv.",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/MolecularInput"}
                },
                "multipart/form-data": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string", "format": "binary"},
                            "normalise": {"type": "boolean", "default": False},
                            "mark_houwink_a": {"type": "number", "nullable": True},
                        },
                        "required": ["file"],
                    }
                },
            },
        }
    },
)
async def calculate_molecular_endpoint(
    request: Request,
    file: UploadFile | None = File(
        None, description="CSV or delimited text export from the SEC/GPC instrument."
    ),
    normalise: bool = Form(
        False,
        description=(
            "Divide the fractions by their sum before calculating. Use when "
            "the file holds percentages or raw intensities."
        ),
    ),
    mark_houwink_a: float | None = Form(
        None, description="Mark-Houwink exponent a, enabling the Mv calculation."
    ),
) -> MolecularResult:
    """
    Calculate Mn, Mw, Mz, Mz+1 and dispersity.

    Two ways to supply the data, and exactly one must be used:

    * **JSON body** - a ``MolecularInput`` object with ``masses`` and
      ``weight_fractions``, optionally ``normalise`` and ``mark_houwink_a``.
    * **Multipart file upload** - a ``file`` field carrying a delimited text
      export, optionally with ``normalise`` and ``mark_houwink_a`` form
      fields.

    Note on implementation: FastAPI cannot bind a Pydantic model to the JSON
    body of an operation that also declares ``File`` or ``Form`` parameters -
    the model silently degrades into another form field. That is exactly the
    bug that made JSON mode unreachable in release 0.1.0. The JSON body is
    therefore read and validated explicitly from the ``Request``, and
    ``openapi_extra`` declares both media types so the published schema
    matches what the endpoint actually accepts.

    The file importer auto-detects the delimiter, the decimal separator, the
    header language and the scale of the distribution column, logging every
    decision. Use ``/molecular/import`` to inspect those decisions without
    calculating.
    """
    content_type = request.headers.get("content-type", "")
    has_file = file is not None

    # ---- JSON body mode -----------------------------------------------------
    if "application/json" in content_type:
        if has_file:
            raise HTTPException(
                status_code=400,
                detail="Provide either a JSON body or a file upload, not both.",
            )
        try:
            raw = await request.json()
        except Exception as exc:  # malformed JSON
            raise HTTPException(
                status_code=400, detail=f"Invalid JSON body: {exc}"
            ) from exc
        try:
            payload = MolecularInput.model_validate(raw)
        except ValidationError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON input: {exc.errors()}",
            ) from exc
        return _build_result(
            payload.masses,
            payload.weight_fractions,
            payload.normalise,
            payload.mark_houwink_a,
        )

    # ---- file mode ----------------------------------------------------------
    if not has_file:
        raise HTTPException(
            status_code=400,
            detail=(
                "No input provided. Send a JSON body with 'masses' and "
                "'weight_fractions', or upload a file in the 'file' field."
            ),
        )

    assert file is not None  # guaranteed above
    blob = await file.read()
    if not blob:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    # Guard against a request that carries both a file and a JSON body. The
    # framework routes such a request to multipart and would otherwise ignore
    # the JSON silently, so the contradiction is detected here and refused.
    form = await request.form()
    stray_json_keys = {"masses", "weight_fractions", "normalise", "mark_houwink_a"}
    unexpected = [k for k in form.keys() if k in stray_json_keys and k != "normalise"]
    if unexpected:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide either a JSON body or a file upload, not both. "
                f"Unexpected field(s) alongside the file: {sorted(unexpected)}."
            ),
        )

    try:
        imported = parse_distribution_csv(blob)
    except ImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # A file whose fractions already sum to 1 must not be renormalised by the
    # form flag alone; only normalise when the user asked OR the importer had
    # to rescale a percentage/intensity column.
    effective_normalise = bool(normalise) or imported.normalised

    return _build_result(
        imported.masses,
        imported.weight_fractions,
        effective_normalise,
        mark_houwink_a,
    )


@router.post(
    "/import",
    response_model=ImportPreview,
    summary="Inspect how a file will be interpreted",
    response_description="The parsed distribution plus every decision the importer made.",
)
async def import_preview_endpoint(
    file: UploadFile = File(..., description="The file to inspect."),
) -> ImportPreview:
    """
    Parse a file without calculating anything, and return the decisions.

    Call this when a calculation gives an unexpected answer: the ``decisions``
    list states which delimiter, header, scale and axis convention the
    importer chose, so any misinterpretation is visible rather than silent.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    try:
        imported = parse_distribution_csv(content)
    except ImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImportPreview(
        masses=imported.masses,
        weight_fractions=imported.weight_fractions,
        decisions=imported.decisions,
        columns_used=imported.columns_used,
        scale_detected=imported.scale_detected,
        normalised=imported.normalised,
        linearised_log_axis=imported.linearised_log_axis,
        instrument_Mn=imported.instrument_Mn,
        instrument_Mw=imported.instrument_Mw,
        rows_dropped=imported.rows_dropped,
        n_slices=len(imported.masses),
    )


@router.post(
    "/log-normal",
    response_model=MolecularResult,
    summary="Synthesise a log-normal distribution",
    response_description="The averages of a log-normal MWD with the requested Mn and dispersity.",
)
async def log_normal_endpoint(
    Mn: float = Form(..., gt=0, description="Target number-average molar mass, g/mol."),
    dispersity: float = Form(
        ..., ge=1.0, description="Target dispersity Mw/Mn. Must be >= 1."
    ),
    n_points: int = Form(2000, ge=10, le=20000),
) -> MolecularResult:
    """
    Build a log-normal molecular-weight distribution and return its averages.

    Provided as a reference case: a log-normal MWD is the shape most closely
    approached by a well-controlled radical polymerisation, and its analytic
    relation Mz/Mw = Mw/Mn = exp(sigma^2) makes it a useful check on any
    measured distribution. Values recovered from the discretised curve differ
    from the analytic ones by the discretisation error, which is returned as
    given rather than corrected.
    """
    from app.core.molar_mass import log_normal_moments

    try:
        d = log_normal_moments(Mn, dispersity, n_points=n_points)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MolecularResult(
        Mn=d["Mn"],
        Mw=d["Mw"],
        Mz=d["Mz"],
        Mz_plus_1=d["Mz_plus_1"],
        dispersity=d["dispersity"],
        Mv=None,
        mark_houwink_a=None,
        n_slices=n_points,
        fraction_sum_input=1.0,
        normalised=False,
    )
