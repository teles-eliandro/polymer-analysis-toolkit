"""
Importer: every file convention a real SEC/GPC instrument produces.

Each test names the convention it protects and asserts the recovered
distribution, not merely that parsing did not raise. A parser that silently
misreads a percent column as a fraction returns a wrong answer without error,
which is the failure mode that matters.
"""

from __future__ import annotations

import pytest

from app.core.ingest import ImportError_, parse_distribution_csv
from app.core.molar_mass import moment_averages

# Hand-checked reference: Mn = 1960.784313..., Mw = 2700, D = 1.377
MN_REF = 1.0 / (0.2 / 1000 + 0.5 / 2000 + 0.3 / 5000)
MW_REF = 2700.0


def _averages(blob: bytes):
    r = parse_distribution_csv(blob)
    return moment_averages(r.masses, r.weight_fractions), r


@pytest.mark.parametrize(
    "label,blob",
    [
        ("pt-BR headers", b"massa,fracao\n1000,0.2\n2000,0.5\n5000,0.3\n"),
        ("English headers", b"mass,fraction\n1000,0.2\n2000,0.5\n5000,0.3\n"),
        ("long English names", b"molecular_weight,weight_fraction\n1000,0.2\n2000,0.5\n5000,0.3\n"),
        ("single-letter M/Wf", b"M\tWf\n1000\t0.2\n2000\t0.5\n5000\t0.3\n"),
        ("headerless", b"1000,0.2\n2000,0.5\n5000,0.3\n"),
    ],
)
def test_header_conventions_all_recover_the_same_distribution(label, blob):
    res, _ = _averages(blob)
    assert res.Mn == pytest.approx(MN_REF, rel=1e-9), label
    assert res.Mw == pytest.approx(MW_REF, rel=1e-9), label


def test_percent_scale_is_detected_and_divided():
    """A column summing to 100 is percent, not a fraction."""
    res, r = _averages(b"mass,fraction\n1000,20\n2000,50\n5000,30\n")
    assert r.scale_detected == "percent"
    assert r.normalised is True
    assert r.weight_fractions == pytest.approx([0.2, 0.5, 0.3], rel=1e-9)
    assert res.Mn == pytest.approx(MN_REF, rel=1e-9)


def test_raw_intensity_is_normalised():
    res, r = _averages(b"mass,intensity\n1000,120\n2000,300\n5000,180\n")
    assert r.scale_detected == "intensity"
    assert r.normalised is True
    assert res.Mn == pytest.approx(MN_REF, rel=1e-9)


def test_semicolon_delimiter_with_decimal_comma():
    """European locale export: ';' separates fields, ',' is the decimal mark."""
    res, r = _averages(b"mass;fraction\n1000;0,2\n2000;0,5\n5000;0,3\n")
    assert r.normalised is False
    assert res.Mn == pytest.approx(MN_REF, rel=1e-9)


def test_comma_delimiter_with_decimal_comma_recombined():
    """
    The hardest case: ',' is both the field separator and the decimal mark,
    as in a pt-BR export of '1000,0,2'. A naive split yields three fields.
    """
    res, r = _averages(b"massa,fracao\n1000,0,2\n2000,0,5\n5000,0,3\n")
    assert len(r.masses) == 3
    assert r.weight_fractions == pytest.approx([0.2, 0.5, 0.3], rel=1e-9)
    assert res.Mn == pytest.approx(MN_REF, rel=1e-9)


def test_instrument_preamble_is_skipped():
    blob = (
        b"Agilent GPC/SEC Report\n"
        b"Sample: PS-1140\n"
        b"Operator: Materials Lab\n"
        b"\n"
        b"M\tWf\n"
        b"1000\t0.2\n2000\t0.5\n5000\t0.3\n"
    )
    res, r = _averages(blob)
    assert r.masses[0] == pytest.approx(1000.0)
    assert res.Mw == pytest.approx(MW_REF, rel=1e-9)


def test_log_axis_header_triggers_exponentiation():
    """A column named logM holds log10 values and must be exponentiated."""
    r = parse_distribution_csv(b"logM,dw/dlogM\n3.000,0.2\n3.301,0.5\n3.699,0.3\n")
    assert r.linearised_log_axis is True
    # 10^3.000 = 1000, 10^3.301 = 2000.0 (approx), 10^3.699 = 5001
    assert r.masses[0] == pytest.approx(1000.0, rel=1e-6)
    assert r.masses[1] == pytest.approx(2000.0, rel=1e-3)
    assert r.masses[2] == pytest.approx(5000.0, rel=1e-3)


def test_linear_axis_is_not_mistaken_for_log():
    """A genuine g/mol axis spanning decades must stay linear."""
    blob = b"mass,fraction\n1000,0.2\n50000,0.3\n1000000,0.5\n"
    r = parse_distribution_csv(blob)
    assert r.linearised_log_axis is False
    assert r.masses == pytest.approx([1000.0, 50000.0, 1000000.0])


def test_low_mass_oligomer_axis_stays_linear():
    """
    An oligomer distribution at 200-900 g/mol is small enough to trip a naive
    'values are below 10' test. It must not be exponentiated.
    """
    blob = b"mass,fraction\n200,0.3\n500,0.4\n900,0.3\n"
    r = parse_distribution_csv(blob)
    assert r.linearised_log_axis is False
    assert r.masses == pytest.approx([200.0, 500.0, 900.0])


def test_instrument_mn_mw_are_surfaced_for_cross_check():
    blob = b"mass,fraction,Mn,Mw\n1000,0.2,1960.78,2700\n2000,0.5,,\n5000,0.3,,\n"
    r = parse_distribution_csv(blob)
    assert r.instrument_Mn == pytest.approx(1960.78)
    assert r.instrument_Mw == pytest.approx(2700.0)


def test_duplicate_masses_are_merged():
    blob = b"mass,fraction\n1000,0.1\n1000,0.1\n2000,0.5\n5000,0.3\n"
    r = parse_distribution_csv(blob)
    assert len(r.masses) == 3
    assert sum(r.weight_fractions) == pytest.approx(1.0)


def test_non_numeric_rows_are_dropped_and_counted():
    blob = b"mass,fraction\n1000,0.2\nnote,here\n2000,0.5\n5000,0.3\n"
    r = parse_distribution_csv(blob)
    assert r.rows_dropped >= 1
    assert len(r.masses) == 3


def test_utf8_bom_is_handled():
    blob = "\ufeffmass,fraction\n1000,0.2\n2000,0.5\n5000,0.3\n".encode()
    res, _ = _averages(blob)
    assert res.Mn == pytest.approx(MN_REF, rel=1e-9)


def test_latin1_encoding_is_handled():
    blob = "massa,fracao\n1000,0.2\n2000,0.5\n5000,0.3\n".encode("latin-1")
    res, _ = _averages(blob)
    assert res.Mn == pytest.approx(MN_REF, rel=1e-9)


def test_decisions_log_is_populated():
    """The importer must explain itself; a silent parse is not acceptable."""
    r = parse_distribution_csv(b"mass,fraction\n1000,20\n2000,50\n5000,30\n")
    assert len(r.decisions) >= 2
    joined = " ".join(r.decisions).lower()
    assert "percent" in joined


@pytest.mark.parametrize(
    "label,blob",
    [
        ("empty file", b""),
        ("whitespace only", b"   \n\n  \n"),
        ("single row", b"mass,fraction\n1000,0.2\n"),
        ("no numeric columns", b"a,b\nfoo,bar\nbaz,qux\n"),
        ("all zeros in value column", b"mass,fraction\n1000,0\n2000,0\n"),
    ],
)
def test_unusable_files_raise_a_clear_error(label, blob):
    with pytest.raises(ImportError_):
        parse_distribution_csv(blob)


def test_explicit_column_override():
    """When auto-detection picks the wrong column, the user can force it."""
    blob = b"weird_a,weird_b\n1000,0.2\n2000,0.5\n5000,0.3\n"
    r = parse_distribution_csv(blob, mass_column="weird_a", fraction_column="weird_b")
    assert r.masses == pytest.approx([1000.0, 2000.0, 5000.0])


def test_column_override_reports_a_missing_column():
    blob = b"mass,fraction\n1000,0.2\n2000,0.5\n5000,0.3\n"
    with pytest.raises(ImportError_, match="not found"):
        parse_distribution_csv(blob, mass_column="does_not_exist")


def test_realistic_wide_distribution_round_trip():
    """A nine-slice distribution spanning three decades, values hand-checked."""
    masses = [5000, 10000, 20000, 40000, 80000, 160000, 320000, 640000, 1280000]
    weights = [0.02, 0.05, 0.10, 0.18, 0.24, 0.19, 0.12, 0.07, 0.03]
    blob = ("mass,fraction\n" + "\n".join(f"{m},{w}" for m, w in zip(masses, weights, strict=False))).encode()
    res, r = _averages(blob)
    direct = moment_averages(masses, weights)
    assert res.Mn == pytest.approx(direct.Mn, rel=1e-9)
    assert res.Mw == pytest.approx(direct.Mw, rel=1e-9)
    # Cross-check Mw by hand: sum(w*M)
    mw_hand = sum(w * m for m, w in zip(masses, weights, strict=False))
    assert res.Mw == pytest.approx(mw_hand, rel=1e-9)
