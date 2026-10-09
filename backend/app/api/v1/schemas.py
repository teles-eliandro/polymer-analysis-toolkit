"""Pydantic schemas for the PAT API."""

from __future__ import annotations

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Molecular
# --------------------------------------------------------------------------


class MolecularInput(BaseModel):
    """Direct JSON input for the molecular module."""

    masses: list[float] = Field(
        ...,
        min_length=2,
        description="Molar masses in g/mol. All values must be > 0.",
        examples=[[1000.0, 2000.0, 5000.0]],
    )
    weight_fractions: list[float] = Field(
        ...,
        min_length=2,
        description=(
            "Weight fractions, one per mass. Must be non-negative and sum to "
            "1.0 unless normalise=true."
        ),
        examples=[[0.2, 0.5, 0.3]],
    )
    normalise: bool = Field(
        False,
        description=(
            "Divide the fractions by their sum before calculating. Set true "
            "when the values are percentages or raw intensities."
        ),
    )
    mark_houwink_a: float | None = Field(
        None,
        gt=0,
        description=(
            "Mark-Houwink-Sakurada exponent a. When supplied, the "
            "viscosity-average molar mass Mv is also computed. The value is "
            "specific to the polymer/solvent/temperature system and must come "
            "from the Polymer Handbook or the relevant paper."
        ),
    )


class MolecularResult(BaseModel):
    Mn: float = Field(description="Number-average molar mass, g/mol.")
    Mw: float = Field(description="Weight-average molar mass, g/mol.")
    Mz: float = Field(description="Z-average molar mass, g/mol.")
    Mz_plus_1: float = Field(description="Z+1-average molar mass, g/mol.")
    dispersity: float = Field(
        description=(
            "Dispersity D = Mw/Mn (IUPAC 2009). Formerly called the "
            "polydispersity index, PDI."
        )
    )
    Mv: float | None = Field(
        None, description="Viscosity-average molar mass, g/mol. Requires mark_houwink_a."
    )
    mark_houwink_a: float | None = None
    #: Number of slices used in the calculation.
    n_slices: int
    #: Sum of the weight fractions as supplied by the user.
    fraction_sum_input: float
    #: True when the fractions were rescaled before calculating.
    normalised: bool


# --------------------------------------------------------------------------
# Importer
# --------------------------------------------------------------------------


class ImportPreview(BaseModel):
    """Everything the importer decided while reading a file."""

    masses: list[float]
    weight_fractions: list[float]
    decisions: list[str] = Field(
        description="Ordered log of every interpretation decision made."
    )
    columns_used: dict
    scale_detected: str = Field(
        description="'fraction', 'percent', 'intensity' or 'differential'."
    )
    normalised: bool
    linearised_log_axis: bool
    instrument_Mn: float | None = None
    instrument_Mw: float | None = None
    rows_dropped: int
    n_slices: int


# --------------------------------------------------------------------------
# Thermal
# --------------------------------------------------------------------------


class TGAStep(BaseModel):
    onset_C: float
    end_C: float
    loss_pct: float


class TGAResult(BaseModel):
    Td_5pct: float | None = Field(None, description="Temperature at 5 % mass loss, Celsius.")
    Td_10pct: float | None = Field(None, description="Temperature at 10 % mass loss, Celsius.")
    T_max_rate: float | None = Field(
        None, description="Temperature of the tallest DTG peak, Celsius."
    )
    T_95pct: float | None = Field(None, description="Temperature at 95 % mass loss, Celsius.")
    residue_pct: float = Field(description="Residue at the end of the run, percent.")
    steps: list[TGAStep]
    unattributed_loss_pct: float = Field(
        0.0,
        description=(
            "Mass lost that no reported step accounts for, percent. Non-zero "
            "when a loss is spread too gradually for its rate to stand out "
            "against the noise, so it cannot be separated into a step."
        ),
    )
    notes: list[str] = Field(
        default_factory=list,
        description="What the analysis could and could not resolve.",
    )
    temperature: list[float]
    mass_pct: list[float]
    dtg: list[float]


class TGATraceInput(BaseModel):
    temperature: list[float] = Field(..., min_length=3)
    mass_pct: list[float] = Field(..., min_length=3, description="Mass remaining, percent.")
    smooth_window: int = Field(11, ge=1, le=101)


class DSCResult(BaseModel):
    Tg: float | None = Field(None, description="Glass transition, Celsius, ASTM D3418 midpoint.")
    Tg_onset: float | None = None
    Tg_end: float | None = None
    delta_cp: float | None = Field(None, description="Heat capacity step, J/(g.K).")
    Tm: float | None = Field(None, description="Melting peak, Celsius.")
    delta_Hm: float | None = Field(None, description="Melting enthalpy, J/g.")
    Tc: float | None = None
    delta_Hc: float | None = None
    crystallinity_pct: float | None = Field(
        None, description="Degree of crystallinity, percent. Requires ref_enthalpy_J_g."
    )
    Tg_uncertainty_C: float | None = Field(
        None,
        description=(
            "Half-width, in kelvin, of how much the reported Tg moves when the "
            "trace is resampled. Measures the detection's sensitivity to the "
            "sampling of this trace; it is not an accuracy claim against a "
            "certified reference. Null when no Tg was found."
        ),
    )
    Tg_reliable: bool | None = Field(
        None,
        description=(
            "True when Tg is stable on resampling. False means the value should "
            "not be quoted without repeat runs, not that it is slightly worse."
        ),
    )
    temperature: list[float]
    heat_flow: list[float]
    direction: str
    claims: dict[str, "FieldClaim"] = Field(
        default_factory=dict,
        description=(
            "What each reported number is worth, keyed by field name. Every "
            "transition temperature is 'suggested' -- an inference from the "
            "trace shape that can be wrong -- while quantities read from the "
            "file are 'read' and published formulas over declared inputs are "
            "'formula'. Absent fields were not reported at all. Clients should "
            "present the confidence alongside the value rather than the bare "
            "number."
        ),
    )
    comparisons: list[PropertyComparison] = Field(
        default_factory=list,
        description=(
            "The measured values compared against published ranges, one entry "
            "per comparable property, each carrying a tri-state verdict and the "
            "citation of the range it used. Empty when the sample name was not "
            "given or the polymer was not recognised -- both of which are "
            "reported as 'not_comparable' entries rather than omitted, so the "
            "client can say why."
        ),
    )


class FieldClaim(BaseModel):
    """A reported value with its confidence and the evidence behind it."""

    value: float | None = None
    confidence: str = Field(
        "suggested",
        description=(
            "One of 'read' (a property of the input, or a deterministic "
            "transform of it), 'formula' (a published formula over a declared "
            "input; reproducible), or 'suggested' (an inference from the trace "
            "shape; can be wrong)."
        ),
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="The measured observations that produced this value.",
    )
    note: str | None = Field(
        None, description="The caveat a reader needs to act correctly on it."
    )


class PropertyComparison(BaseModel):
    """One measured value compared against its published range."""

    property: str
    verdict: str = Field(
        ...,
        description=(
            "One of 'within', 'outside', or 'not_comparable'. The third is not "
            "an error: it is returned when the polymer was not identified, when "
            "the value is an unstable suggestion, when no published range "
            "covers this property, or when the units differ. A two-state verdict "
            "would report a detector failure as a finding about the sample."
        ),
    )
    measured: float | None = None
    unit: str | None = None
    reference_low: float | None = None
    reference_high: float | None = None
    reference_unit: str | None = None
    reference_source: str | None = None
    reference_method: str | None = None
    reference_note: str | None = None
    reason: str | None = Field(
        None, description="Why the comparison could not be made, when it could not."
    )
    polymer: str | None = Field(None, description="The polymer compared against.")


class DSCTraceInput(BaseModel):
    temperature: list[float] = Field(..., min_length=3)
    heat_flow: list[float] = Field(..., min_length=3, description="Heat flow in W/g.")
    heating_rate: float | None = Field(
        None, gt=0, description="Program rate in K/min. Required for enthalpy in J/g."
    )
    ref_enthalpy_J_g: float | None = Field(
        None,
        gt=0,
        description=(
            "Melting enthalpy of a 100 % crystalline reference of the same "
            "polymer, J/g. Required for a crystallinity value."
        ),
    )
    smooth_window: int = Field(11, ge=1, le=101)
    sample_name: str | None = Field(
        None,
        description=(
            "Name of the sample, used to identify the polymer for the "
            "comparison against published ranges. When it is absent or the "
            "polymer is not recognised, the comparison reports "
            "'not_comparable' rather than guessing -- guessing the polymer is "
            "how a comparison produces a confident wrong answer."
        ),
    )


# --------------------------------------------------------------------------
# Mechanical
# --------------------------------------------------------------------------


class TensileResult(BaseModel):
    E_MPa: float | None = Field(None, description="Young's modulus, MPa.")
    stress_break_MPa: float | None = None
    strain_break_pct: float | None = None
    stress_max_MPa: float | None = None
    strain_max_pct: float | None = None
    stress_yield_MPa: float | None = None
    strain_yield_pct: float | None = None
    toughness_MJ_m3: float | None = Field(None, description="Work to fracture, MJ/m^3.")
    yielded: bool
    brittle: bool
    modulus_window: list[float] | None = Field(
        None, description="Strain range (percent) used for the modulus regression."
    )
    strain_pct: list[float]
    stress_MPa: list[float]


class TensileInput(BaseModel):
    strain_pct: list[float] = Field(..., min_length=4)
    stress_MPa: list[float] = Field(..., min_length=4)
    modulus_window: list[float] | None = Field(
        None, min_length=2, max_length=2, description="[strain_low, strain_high] in percent."
    )


# --------------------------------------------------------------------------
# Rheology
# --------------------------------------------------------------------------


class RheologyResult(BaseModel):
    cross_over_freq: float | None = Field(
        None, description="Frequency where G' = G'', rad/s."
    )
    cross_over_modulus: float | None = None
    solid_like_at_low_freq: bool = Field(
        description="True when G' > G'' at the lowest measured frequency."
    )
    plateau_modulus_G0: float | None = Field(
        None, description="Estimate of G0 from the tan(delta) minimum, Pa."
    )
    relaxation_time_s: float | None = None
    terminal_slope_Gprime: float | None = Field(
        None, description="Log-log slope of G' in the terminal region (theory: 2)."
    )
    terminal_slope_Gpp: float | None = Field(
        None, description="Log-log slope of G'' in the terminal region (theory: 1)."
    )
    zero_shear_viscosity_Pas: float | None = None
    gel_point_detected: bool
    tan_delta_spread: float | None = None
    omega: list[float]
    G_prime: list[float]
    G_double_prime: list[float]
    tan_delta: list[float]


class RheologyInput(BaseModel):
    omega: list[float] = Field(..., min_length=4, description="Angular frequency, rad/s.")
    G_prime: list[float] = Field(..., min_length=4, description="Storage modulus, Pa.")
    G_double_prime: list[float] = Field(..., min_length=4, description="Loss modulus, Pa.")
    gel_tolerance: float = Field(0.15, gt=0, lt=2)


# --------------------------------------------------------------------------
# Structure
# --------------------------------------------------------------------------


class FTIRCandidate(BaseModel):
    assignment: str
    reference_range_cm1: list[float]
    expected_intensity: str
    note: str


class FTIRMatch(BaseModel):
    observed_cm1: float
    relative_height: float
    candidates: list[FTIRCandidate]


class FTIRResult(BaseModel):
    matches: list[FTIRMatch]
    detected_peaks: list[float]
    detected_peaks_rel: list[float]
    note: str


class FTIRInput(BaseModel):
    wavenumber: list[float] = Field(..., min_length=10)
    absorbance: list[float] = Field(..., min_length=10)
    prominence_frac: float = Field(0.08, gt=0, lt=1)
    tolerance_cm1: float = Field(0.0, ge=0)


class XRDResult(BaseModel):
    peaks_two_theta: list[float]
    d_spacing_angstrom: list[float]
    crystallite_size_nm: list[float | None]
    fwhm_deg: list[float]
    crystallinity_pct: float | None = Field(
        None,
        description=(
            "Crystallinity INDEX, not the absolute degree of crystallinity. "
            "Comparable only between samples measured identically."
        ),
    )
    wavelength_angstrom: float
    two_theta: list[float]
    intensity: list[float]


class XRDInput(BaseModel):
    two_theta: list[float] = Field(..., min_length=10)
    intensity: list[float] = Field(..., min_length=10)
    wavelength_angstrom: float = Field(1.5406, gt=0, description="Cu K-alpha1 by default.")
    K: float = Field(0.9, gt=0, description="Scherrer shape factor.")
    instrumental_fwhm_deg: float = Field(
        0.0,
        ge=0,
        description=(
            "Instrumental broadening (FWHM, degrees). Ignoring it makes the "
            "reported crystallite size too small."
        ),
    )
    prominence_frac: float = Field(0.05, gt=0, lt=1)


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------


class ErrorResponse(BaseModel):
    detail: str
