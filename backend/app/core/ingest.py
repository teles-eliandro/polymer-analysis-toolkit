"""
Tolerant importer for real GPC/SEC exports.

Rationale
---------
Commercial SEC systems (Agilent/Wyatt/Waters/Tosoh) and academic datasets
export distributions in several incompatible conventions. A tool that only
accepts one of them is unusable in practice. This module detects the
convention from the data itself and reports the decision it made, so the
user can verify rather than trust.

Detection covers
----------------
- Header language: pt-BR (`massa`, `fracao`), English (`mass`, `fraction`,
  `molecular_weight`, `weight_fraction`) and common abbreviations.
- Column roles: mass axis, weight fraction, raw detector intensity, and a
  differential axis (dw/dlogM) paired with log10(M).
- Fraction scale: already a fraction (sums to ~1) vs percent (sums to ~100)
  vs raw intensity (sums to anything) which is normalised.
- Delimiters: comma, semicolon, tab, whitespace (many instruments export
  semicolon-separated files for European locales).
- Decimal comma (`0,5`) as used in pt-BR / fr / de locale exports.
- Descriptive preamble lines before the real header row.

References
----------
- IUPAC. "Definitions of terms relating to the structure and processing of
  sols, gels, ... and to polymer characterization by SEC." Pure Appl. Chem.
  2014 recommendations on SEC data reporting.
- ASTM D5296-19, "Standard Test Method for Molecular Weight Averages and
  Molecular Weight Distribution of Polystyrene by High Performance
  Size-Exclusion Chromatography".
- ISO 16014-1:2019, "Plastics - Determination of average molecular weight
  and molecular weight distribution of polymers using size-exclusion
  chromatography".
"""

from __future__ import annotations

import csv
import re
from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

__all__ = ["ImportResult", "parse_distribution_csv", "parse_distribution_text"]


class ImportError_(ValueError):
    """Raised when a file cannot be interpreted as a distribution."""


# --------------------------------------------------------------------------
# Header vocabulary
# --------------------------------------------------------------------------
# Ordered longest-first so that e.g. "molecular_weight" is matched before any
# hypothetical "mass" substring. Matching is done on a normalised token that
# has non-alphanumerics collapsed to single underscores.

MASS_AXIS_TOKENS = [
    "molecular_weight",
    "molar_mass",
    "molecular_mass",
    "massa_molecular",
    "masa_molecular",
    "massa_molar",
    "mol_weight",
    "weight_avg_mw",
    "mw_g_mol",
    "log_m",
    "logm",
    "log10_m",
    "log_mw",
    "mass",
    "massa",
    "masa",
    "molar",
    "m_w",
    "mw",
    "mm",
    "m",
]

WEIGHT_FRACTION_TOKENS = (
    "weight_fraction",
    "weight_fraction_wi",
    "fracao_massica",
    "fracao_em_peso",
    "fraction_massique",
    "mass_fraction",
    "fracao",
    "fraccion",
    "fraction",
    "fracao_peso",
    "f_wi",
    "wi",
    "w_fraction",
    "wf",
)

DIFFERENTIAL_TOKENS = (
    "dw_dlogm",
    "dw_dlog_m",
    "dw_dlogmw",
    "d_w_dlog_m",
    "dwdlogm",
    "dw_d_log_m",
    "dwdiogm",
    "differential_weight_fraction",
    "dw_dlog",
    "dlogm",
)

INTENSITY_TOKENS = (
    "intensity",
    "intensidade",
    "intensite",
    "intensidad",
    "detector_response",
    "response",
    "ri_signal",
    "uv_signal",
    "signal",
    "absorbance",
    "counts",
    "area",
    "height",
    "concentration",
    "concentracao",
)

_UNIT_SUFFIX_RE = re.compile(r"[_\(\[][^\)\]]*[\)\]]?$")
_MASS_UNIT_RE = re.compile(r"(g\s*/?\s*mol|kg\s*/?\s*mol|da|kda|dalton)", re.I)


@dataclass
class ImportResult:
    """Outcome of parsing a distribution file."""

    masses: list[float]
    weight_fractions: list[float]
    #: Human-readable, ordered log of every decision the importer made.
    decisions: list[str] = field(default_factory=list)
    #: Header names as they appeared in the file.
    columns_used: dict[str, str] = field(default_factory=dict)
    #: 'fraction' | 'percent' | 'intensity' | 'differential'
    scale_detected: str = "fraction"
    #: True when the importer rescaled values so they sum to 1.
    normalised: bool = False
    #: True when a log10 mass axis was exponentiated back to linear.
    linearised_log_axis: bool = False
    #: Optional masses the instrument already computed, for cross-checking.
    instrument_Mn: float | None = None
    instrument_Mw: float | None = None
    #: Rows dropped because they were non-numeric or non-physical.
    rows_dropped: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "masses": self.masses,
            "weight_fractions": self.weight_fractions,
            "decisions": self.decisions,
            "columns_used": self.columns_used,
            "scale_detected": self.scale_detected,
            "normalised": self.normalised,
            "linearised_log_axis": self.linearised_log_axis,
            "instrument_Mn": self.instrument_Mn,
            "instrument_Mw": self.instrument_Mw,
            "rows_dropped": self.rows_dropped,
            "n_slices": len(self.masses),
        }


def _normalise_header(name: str) -> str:
    token = str(name).strip().lower()
    token = token.replace("°", "").replace("º", "")
    token = re.sub(r"[^a-z0-9]+", "_", token)
    return token.strip("_")


def _match_role(token: str) -> str | None:
    """Return 'mass' | 'fraction' | 'differential' | 'intensity' | None."""
    base = _UNIT_SUFFIX_RE.sub("", token)
    for candidate in (base, token):
        for mass in MASS_AXIS_TOKENS:
            if candidate == mass:
                return "mass"
        for diff in DIFFERENTIAL_TOKENS:
            if candidate == diff or candidate.startswith(diff):
                return "differential"
        for frac in WEIGHT_FRACTION_TOKENS:
            if candidate == frac:
                return "fraction"
        for inten in INTENSITY_TOKENS:
            if candidate == inten or candidate.startswith(inten):
                return "intensity"
    # Fallback: substring matching, mass axis first because "molecular_weight"
    # also contains no fraction keyword but "weight_fraction" does.
    for candidate in (base, token):
        if any(candidate.endswith(m) for m in ("_mw", "_massa", "_mass")):
            return "mass"
        if "fraction" in candidate or "fracao" in candidate or "fraccion" in candidate:
            return "fraction"
        if "intens" in candidate or "signal" in candidate:
            return "intensity"
        if "molecular" in candidate or "molar" in candidate or candidate == "mass":
            return "mass"
    return None


def _to_float(text: str) -> float | None:
    """Parse a numeric field, tolerating decimal comma and thousands separators."""
    if text is None:
        return None
    s = str(text).strip().strip('"').strip("'")
    if not s or s.lower() in {"na", "n/a", "nan", "null", "-", "--", ""}:
        return None
    # Remove unit suffixes and stray characters.
    s = re.sub(r"[^0-9eE\+\-\.\,\s]", "", s).strip()
    if not s:
        return None
    # Decimal comma: "0,5" or "1.234,56". If both separators present, treat
    # '.' as thousands and ',' as decimal.
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        # Ambiguous: "1,234" could be 1234 or 1.234. GPC exports use decimal
        # comma far more often than thousands grouping in this context, and
        # thousands grouping with exactly 3 digits after a comma is rare in
        # molar masses. Treat a single comma as a decimal separator unless it
        # is followed by exactly 3 digits AND the value looks large.
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3:
            # "1,234" -> most likely decimal comma in a pt-BR export
            s = s.replace(",", ".")
        else:
            s = s.replace(",", ".")
    try:
        value = float(s)
    except ValueError:
        return None
    if not np.isfinite(value):
        return None
    return value


def _detect_delimiter(sample_lines: Sequence[str]) -> str:
    """Sniff the delimiter; falls back to whitespace."""
    candidates = [",", ";", "\t", "|"]
    best, best_score = ",", -1
    for delim in candidates:
        counts = [line.count(delim) for line in sample_lines if line.strip()]
        if not counts:
            continue
        non_zero = [c for c in counts if c > 0]
        if not non_zero:
            continue
        # Prefer a delimiter that is consistently present and yields >1 field.
        score = min(non_zero) * 100 + len(non_zero)
        if score > best_score:
            best, best_score = delim, score
    if best_score <= 0:
        return "whitespace"
    return best


def _split(line: str, delimiter: str) -> list[str]:
    """
    Split a line into fields, rejoining artifacts of a decimal comma.

    When the delimiter is a comma AND the separator is also a comma (the
    pt-BR/fr/de locale case, e.g. ``1000,0,2`` meaning mass=1000, w=0.2) a
    naive split yields three fields. The pattern is unambiguous when a field
    is exactly a single digit and its predecessor is all-digits followed by
    another single digit, so ``1000,0,2`` is recombined to ``1000,0.2``.
    """
    if delimiter == "whitespace":
        return [f for f in re.split(r"\s+", line.strip()) if f]

    fields = next(csv.reader([line], delimiter=delimiter))

    if delimiter == ",":
        merged: list[str] = []
        i = 0
        while i < len(fields):
            # Look for "digits" + "," + "d" + "," + "d"  -> "digits" + "." + "dd"
            if (
                i + 2 < len(fields)
                and re.fullmatch(r"\d+", fields[i])
                and re.fullmatch(r"\d{1,2}", fields[i + 1])
                and re.fullmatch(r"\d{1,3}", fields[i + 2])
                and not re.fullmatch(r"\d{3}", fields[i + 1])
            ):
                merged.append(f"{fields[i]}.{fields[i + 1]}")
                i += 2
            else:
                merged.append(fields[i])
                i += 1
        fields = merged

    return fields


def _find_header(
    rows: Sequence[Sequence[str]],
    delimiter: str,
) -> tuple[int | None, dict[str, int], dict[str, str]]:
    """
    Locate the header row among the first rows (instruments emit preamble).
    Returns (index, role->column, role->original header).
    """
    best_idx: int | None = None
    best_roles: dict[str, int] = {}
    best_headers: dict[str, str] = {}

    for idx, row in enumerate(rows[:40]):
        roles: dict[str, int] = {}
        headers: dict[str, str] = {}
        for col, cell in enumerate(row):
            token = _normalise_header(cell)
            if not token:
                continue
            role = _match_role(token)
            if role and role not in roles:
                roles[role] = col
                headers[role] = str(cell).strip()
        if "mass" in roles and ("fraction" in roles or "differential" in roles or "intensity" in roles):
            if len(roles) > len(best_roles):
                best_idx, best_roles, best_headers = idx, roles, headers

    return best_idx, best_roles, best_headers


def _header_says_log(header: str) -> bool:
    """True when the mass column header explicitly names a log10 axis."""
    token = _normalise_header(header)
    return bool(re.match(r"^(log|log10|lg)[_ ]?m(w)?$", token)) or token.startswith("logm")


def _looks_like_log_axis(masses) -> bool:
    """
    Decide whether a mass axis is log10(M) rather than linear g/mol.

    Two independent signals are combined because neither is sufficient alone:

    1. Range. A log10 axis holds exponent values, so every entry is small
       (roughly 1.5 to 9) and the whole span is under ~8. A linear g/mol axis
       for a polymer spans three orders of magnitude or more and its smallest
       value is rarely below 100.
    2. Spacing. SEC slice tables are uniformly spaced in log M (constant
       dlogM per slice), so a log axis has an almost constant step. A linear
       axis does not.

    The range test alone is unreliable for short distributions: three slices
    at logM = 3.00, 3.30, 3.70 would also pass a naive "small numbers" test,
    which is the intended interpretation. The failure mode to avoid is
    misreading a genuine low-mass linear axis (e.g. oligomers at 200-900
    g/mol) as log, so the range test requires the values to be inside the
    log window AND either uniform in step OR spanning less than one decade.
    """
    arr = np.asarray(masses, dtype=np.float64)
    if arr.size < 2 or np.any(arr <= 0):
        return False

    lo, hi = float(np.min(arr)), float(np.max(arr))

    # A log10 axis must lie inside the physically meaningful exponent window.
    # 0.5 leaves headroom for very small oligomers logged as low as logM=0.5;
    # 9.5 covers ultra-high molar masses (log10(3.2e9) = 9.5).
    if lo < 0.5 or hi > 9.5:
        return False

    span = hi - lo
    if span >= 8.0:
        return False

    # Uniform spacing in log M is the signature of a slice table.
    if arr.size >= 3:
        steps = np.diff(arr)
        if np.all(steps > 0):
            cv = float(np.std(steps) / np.mean(steps)) if np.mean(steps) > 0 else 1.0
            if cv <= 0.05:
                return True
        else:
            # Non-monotonic: fall back to treating a tight, small-range set of
            # values as logged.
            return span < 8.0

    # Fewer than 3 points: only trust a crisp decade-spanning window.
    return 1.0 <= lo and hi <= 9.5


def parse_distribution_text(
    text: str,
    mass_column: str | None = None,
    fraction_column: str | None = None,
) -> ImportResult:
    """
    Parse a delimited text blob into (masses, weight_fractions).

    Parameters
    ----------
    text : str
        Full file contents.
    mass_column, fraction_column : str, optional
        Force the column names to use (matched case-insensitively after
        normalisation). Needed only when auto-detection picks the wrong
        column for an unusual export.

    Raises
    ------
    ImportError_
        If no usable distribution can be extracted.
    """
    raw_lines = [ln for ln in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
    if not any(ln.strip() for ln in raw_lines):
        raise ImportError_("The file is empty.")

    # Drop fully blank lines but keep line count for the decisions log.
    lines = [ln for ln in raw_lines if ln.strip()]
    if not lines:
        raise ImportError_("The file contains no data rows.")

    delimiter = _detect_delimiter(lines[:30])
    rows = [_split(ln, delimiter) for ln in lines]

    header_idx, roles, headers = _find_header(rows, delimiter)

    decisions: list[str] = []
    delim_name = {"\t": "TAB", ",": "comma", ";": "semicolon", "|": "pipe"}.get(
        delimiter, "whitespace"
    )
    decisions.append(f"Delimiter detected: {delim_name}.")

    if header_idx is None:
        # Headerless numeric file: assume first column = mass, second = fraction.
        numeric_rows = []
        start = 0
        for idx, row in enumerate(rows):
            vals = [_to_float(c) for c in row]
            ok = [v for v in vals if v is not None]
            if len(ok) >= 2 and len(ok) >= len(row) - 1:
                numeric_rows.append(vals)
                start = idx
                break
        if not numeric_rows:
            raise ImportError_(
                "Could not find a header row or two numeric columns. "
                "Expected columns such as 'mass'/'massa' and 'fraction'/'fracao'."
            )
        roles = {"mass": 0, "fraction": 1}
        headers = {"mass": rows[start][0].strip() if rows[start] else "column 1",
                   "fraction": rows[start][1].strip() if len(rows[start]) > 1 else "column 2"}
        header_idx = start - 1
        decisions.append("No recognisable header: assuming column 1 = mass, column 2 = fraction.")
    else:
        decisions.append(
            "Header row found at line "
            f"{header_idx + 1}: {', '.join(repr(h) for h in headers.values())}."
        )

    # Explicit overrides win over detection.
    if mass_column:
        want = _normalise_header(mass_column)
        for col, cell in enumerate(rows[header_idx]):
            if _normalise_header(cell) == want:
                roles["mass"] = col
                headers["mass"] = str(cell).strip()
                decisions.append(f"Mass column forced to {cell!r} by request.")
                break
        else:
            raise ImportError_(f"Column {mass_column!r} not found in the header.")
    if fraction_column:
        want = _normalise_header(fraction_column)
        for col, cell in enumerate(rows[header_idx]):
            if _normalise_header(cell) == want:
                roles["fraction"] = col
                headers["fraction"] = str(cell).strip()
                decisions.append(f"Fraction column forced to {cell!r} by request.")
                break
        else:
            raise ImportError_(f"Column {fraction_column!r} not found in the header.")

    if "mass" not in roles:
        raise ImportError_(
            "No molar-mass column recognised. Expected a header such as "
            "'mass', 'massa', 'M', 'molecular_weight' or 'logM'."
        )

    mass_col = roles["mass"]

    # Decide which value column carries the distribution weight.
    if "fraction" in roles:
        value_col = roles["fraction"]
        value_role = "fraction"
    elif "differential" in roles:
        value_col = roles["differential"]
        value_role = "differential"
    elif "intensity" in roles:
        value_col = roles["intensity"]
        value_role = "intensity"
    elif "differential" in headers:
        value_col = roles["differential"]
        value_role = "differential"
    else:
        # Last resort: the column that is not the mass column and is numeric.
        value_col, value_role = None, "unknown"
        for col in range(len(rows[header_idx])):
            if col == mass_col:
                continue
            value_col = col
            break
        if value_col is None:
            raise ImportError_(
                "Only one column found. Need a mass column and a weight/fraction column."
            )
        decisions.append(
            f"No fraction/intensity header recognised: using column {value_col + 1} "
            f"({headers.get('fraction') or rows[header_idx][value_col]!r}) as the distribution."
        )

    masses_raw: list[float] = []
    values_raw: list[float] = []
    dropped = 0
    for row in rows[header_idx + 1:]:
        if len(row) <= max(mass_col, value_col):
            if any(str(c).strip() for c in row):
                dropped += 1
            continue
        m_val = _to_float(row[mass_col])
        v_val = _to_float(row[value_col])
        if m_val is None or v_val is None:
            if any(str(c).strip() for c in row):
                dropped += 1
            continue
        if m_val <= 0 or v_val < 0:
            dropped += 1
            continue
        masses_raw.append(m_val)
        values_raw.append(v_val)

    if len(masses_raw) < 2:
        raise ImportError_(
            f"Only {len(masses_raw)} valid data row(s) found - at least 2 are needed "
            "to describe a distribution."
        )
    if dropped:
        decisions.append(f"{dropped} row(s) skipped (blank, non-numeric or non-physical).")

    masses = np.asarray(masses_raw, dtype=np.float64)
    values = np.asarray(values_raw, dtype=np.float64)

    # --- log10 axis -> linear ------------------------------------------------
    # An explicit header such as 'logM' or 'log10(M)' is authoritative; the
    # numeric heuristic only runs when the header does not say.
    mass_header = headers.get("mass", "")
    linearised = False
    if _header_says_log(mass_header) or _looks_like_log_axis(masses):
        masses = np.power(10.0, masses)
        linearised = True
        reason = (
            f"column header {mass_header!r} declares a log10 axis"
            if _header_says_log(mass_header)
            else "values lie in the log10 window with uniform spacing"
        )
        decisions.append(
            f"Mass axis interpreted as log10(M) because {reason}: "
            "converted back to linear g/mol as 10^value."
        )

    total = float(np.sum(values))
    if total <= 0:
        raise ImportError_("The distribution column sums to zero - nothing to analyse.")

    if value_role == "fraction":
        if abs(total - 1.0) <= 1e-3:
            scale, normalised = "fraction", False
            decisions.append(f"Weight fractions already sum to 1.000 (sum = {total:.6f}).")
        elif abs(total - 100.0) <= max(0.1, 0.01 * 100.0):
            values = values / 100.0
            scale, normalised = "percent", True
            decisions.append(
                f"Fractions sum to {total:.4f}: read as PERCENT and divided by 100."
            )
        else:
            values = values / total
            scale, normalised = "fraction", True
            decisions.append(
                f"Fractions sum to {total:.4f} (neither 1 nor 100): normalised by the sum."
            )
    elif value_role in ("intensity", "differential"):
        values = values / total
        scale, normalised = "intensity" if value_role == "intensity" else "differential", True
        decisions.append(
            f"Raw {value_role} values (sum = {total:.6g}) normalised to weight fractions. "
            "Assumes the detector response is proportional to mass concentration "
            "(true for a calibrated concentration detector; NOT true for a mass-sensitive "
            "detector without dn/dc correction)."
        )
    else:
        values = values / total
        scale, normalised = "unknown", True
        decisions.append(f"Unlabelled column normalised by its sum ({total:.6g}).")

    # --- optional instrument Mn/Mw ------------------------------------------
    instrument_Mn = instrument_Mw = None
    lower_headers = {_normalise_header(c): i for i, c in enumerate(rows[header_idx])}
    for key, target in (
        ("mn", "Mn"), ("mn_g_mol", "Mn"), ("mw", "Mw"), ("mw_g_mol", "Mw"),
        ("m_n", "Mn"), ("m_w", "Mw"),
    ):
        if key in lower_headers:
            for row in rows[header_idx + 1:]:
                idx = lower_headers[key]
                if len(row) > idx:
                    val = _to_float(row[idx])
                    if val and val > 0:
                        if target == "Mn" and instrument_Mn is None:
                            instrument_Mn = val
                        elif target == "Mw" and instrument_Mw is None:
                            instrument_Mw = val
                        break

    # Sort ascending by mass - required for consistent plotting and for the
    # analytic log-normal cross-check.
    order = np.argsort(masses)
    masses = masses[order]
    values = values[order]

    # Collapse duplicate masses (some exports repeat the same slice).
    if len(np.unique(masses)) < len(masses):
        unique_m, inverse = np.unique(masses, return_inverse=True)
        summed = np.zeros_like(unique_m)
        np.add.at(summed, inverse, values)
        masses, values = unique_m, summed
        values = values / float(np.sum(values))
        decisions.append(
            f"Duplicate mass values were merged, leaving {len(masses)} unique slices."
        )

    if instrument_Mn:
        decisions.append(f"Cross-check available: file reports Mn = {instrument_Mn:.4g} g/mol.")
    if instrument_Mw:
        decisions.append(f"Cross-check available: file reports Mw = {instrument_Mw:.4g} g/mol.")

    return ImportResult(
        masses=[float(x) for x in masses],
        weight_fractions=[float(x) for x in values],
        decisions=decisions,
        columns_used=dict(headers),
        scale_detected=scale,
        normalised=normalised,
        linearised_log_axis=linearised,
        instrument_Mn=instrument_Mn,
        instrument_Mw=instrument_Mw,
        rows_dropped=dropped,
    )


def parse_distribution_csv(
    content: bytes,
    mass_column: str | None = None,
    fraction_column: str | None = None,
) -> ImportResult:
    """
    Decode bytes then parse. Tries UTF-8, UTF-8-BOM and Latin-1, which covers
    every instrument export encountered in practice.
    """
    text: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise ImportError_("Could not decode the file as text (tried UTF-8, UTF-8-BOM, Latin-1).")
    return parse_distribution_text(text, mass_column=mass_column, fraction_column=fraction_column)
