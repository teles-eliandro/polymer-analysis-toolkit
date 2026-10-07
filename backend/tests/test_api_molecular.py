"""
HTTP contract tests for the molecular module.

Two of these are regression tests for bugs that made release 0.1.0 unusable
in the browser, and both are written to fail loudly if they ever come back:

1. The upload endpoint rejected ``application/octet-stream``, which is what a
   browser's FormData sends. The frontend only worked because axios happened
   to override the header.
2. The JSON body mode was declared in the docstring and implemented in the
   client but the server could never populate the ``data`` parameter, so every
   JSON request returned "Provide either JSON data or a CSV file".
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CALC = "/api/v1/molecular/calc"
IMPORT = "/api/v1/molecular/import"

# Hand-checked: Mn = 1/(0.2/1000 + 0.5/2000 + 0.3/5000) = 1960.784313...
MN_REF = 1.0 / (0.2 / 1000 + 0.5 / 2000 + 0.3 / 5000)
MW_REF = 2700.0
D_REF = MW_REF / MN_REF


def _ok_csv() -> bytes:
    return b"mass,fraction\n1000,0.2\n2000,0.5\n5000,0.3\n"


# ---------------------------------------------------------------------------
# Bug 1: upload content type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "content_type",
    [
        "application/octet-stream",  # what browser FormData actually sends
        "text/csv",                  # what curl -F guesses
        "application/vnd.ms-excel",  # what some instruments and Excel use
        "text/plain",
        None,                        # no type at all
    ],
)
def test_upload_accepts_every_realistic_content_type(content_type):
    files = {"file": ("sample.csv", _ok_csv(), content_type)} if content_type else {
        "file": ("sample.csv", _ok_csv())
    }
    r = client.post(CALC, files=files)
    assert r.status_code == 200, f"{content_type} was rejected: {r.text}"
    body = r.json()
    assert body["Mn"] == pytest.approx(MN_REF, rel=1e-9)
    assert body["Mw"] == pytest.approx(MW_REF, rel=1e-9)


def test_upload_works_with_the_repositories_own_example_file():
    """The file shipped in exemples/ must work exactly as committed."""
    with open("../exemples/polymer_sample.csv", "rb") as fh:
        blob = fh.read()
    r = client.post(CALC, files={"file": ("polymer_sample.csv", blob, "text/csv")})
    assert r.status_code == 200, r.text
    assert r.json()["Mn"] == pytest.approx(MN_REF, rel=1e-9)


# ---------------------------------------------------------------------------
# Bug 2: JSON body mode
# ---------------------------------------------------------------------------


def test_json_body_mode_works():
    r = client.post(CALC, json={"masses": [1000, 2000, 5000], "weight_fractions": [0.2, 0.5, 0.3]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["Mn"] == pytest.approx(MN_REF, rel=1e-9)
    assert body["Mw"] == pytest.approx(MW_REF, rel=1e-9)
    assert body["dispersity"] == pytest.approx(D_REF, rel=1e-9)


def test_openapi_declares_both_input_modes():
    """
    The documented contract must match the implementation. Previously the
    schema advertised only multipart, while the docstring promised JSON.
    """
    spec = client.get("/openapi.json").json()
    content = spec["paths"][CALC]["post"]["requestBody"]["content"]
    assert "multipart/form-data" in content
    assert "application/json" in content


def test_json_mode_returns_all_four_averages():
    r = client.post(CALC, json={"masses": [1000, 2000, 5000], "weight_fractions": [0.2, 0.5, 0.3]})
    body = r.json()
    for key in ("Mn", "Mw", "Mz", "Mz_plus_1", "dispersity"):
        assert key in body, key
    assert body["Mn"] <= body["Mw"] <= body["Mz"] <= body["Mz_plus_1"]


def test_json_mode_honours_normalise_flag():
    r = client.post(
        CALC,
        json={
            "masses": [1000, 2000, 5000],
            "weight_fractions": [20, 50, 30],
            "normalise": True,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["normalised"] is True
    assert body["fraction_sum_input"] == pytest.approx(100.0)
    assert body["Mn"] == pytest.approx(MN_REF, rel=1e-9)


def test_percent_file_is_normalised_automatically():
    """
    A percentage column in a file must not need the user to flip a flag: the
    importer recognises the scale.
    """
    r = client.post(
        CALC, files={"file": ("p.csv", b"mass,fraction\n1000,20\n2000,50\n5000,30\n", "text/csv")}
    )
    assert r.status_code == 200, r.text
    assert r.json()["Mn"] == pytest.approx(MN_REF, rel=1e-9)


def test_mark_houwink_exponent_enables_mv():
    r = client.post(
        CALC,
        json={
            "masses": [1000, 2000, 5000],
            "weight_fractions": [0.2, 0.5, 0.3],
            "mark_houwink_a": 0.7,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["Mv"] is not None
    assert body["Mn"] <= body["Mv"] <= body["Mw"]


def test_mv_is_absent_without_the_exponent():
    r = client.post(CALC, json={"masses": [1000, 2000, 5000], "weight_fractions": [0.2, 0.5, 0.3]})
    assert r.json()["Mv"] is None


# ---------------------------------------------------------------------------
# Input validation over HTTP
# ---------------------------------------------------------------------------


def test_fractions_not_summing_to_one_is_a_400():
    r = client.post(CALC, json={"masses": [1000, 2000], "weight_fractions": [0.2, 0.2]})
    assert r.status_code == 400
    assert "sum to 1.0" in r.json()["detail"]


def test_negative_mass_is_a_400():
    r = client.post(CALC, json={"masses": [1000, -2000], "weight_fractions": [0.5, 0.5]})
    assert r.status_code == 400


def test_empty_request_is_a_400():
    r = client.post(CALC)
    assert r.status_code == 400
    assert "No input provided" in r.json()["detail"]


def test_both_inputs_at_once_is_rejected_when_the_body_reaches_the_server():
    """
    A request carrying both a file part and JSON fields must be refused.

    Note on the transport: when a client library is handed both ``files=`` and
    ``json=``, it drops the JSON and sends multipart only, so the server never
    sees the contradiction. The server-side guard therefore only fires when
    the JSON fields genuinely arrive alongside the file, which is what is
    simulated here by putting the body keys into the multipart form.
    """
    r = client.post(
        CALC,
        files={"file": ("s.csv", _ok_csv(), "text/csv")},
        data={"masses": "[1000, 2000]", "weight_fractions": "[0.5, 0.5]"},
    )
    assert r.status_code == 400, r.text
    assert "not both" in r.json()["detail"]


def test_form_data_without_a_file_is_rejected():
    """Form fields alone are not a valid input for this endpoint."""
    r = client.post(CALC, data={"masses": "1000,2000", "weight_fractions": "0.5,0.5"})
    assert r.status_code == 400
    assert "No input provided" in r.json()["detail"]


def test_empty_file_is_a_400():
    r = client.post(CALC, files={"file": ("empty.csv", b"", "text/csv")})
    assert r.status_code == 400


def test_unparseable_file_is_a_400_with_an_explanation():
    r = client.post(CALC, files={"file": ("x.csv", b"a,b\nfoo,bar\nbaz,qux\n", "text/csv")})
    assert r.status_code == 400
    assert len(r.json()["detail"]) > 10


# ---------------------------------------------------------------------------
# Import preview
# ---------------------------------------------------------------------------


def test_import_preview_explains_its_decisions():
    r = client.post(
        IMPORT, files={"file": ("p.csv", b"mass,fraction\n1000,20\n2000,50\n5000,30\n", "text/csv")}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scale_detected"] == "percent"
    assert body["normalised"] is True
    assert len(body["decisions"]) >= 2


def test_log_normal_reference_endpoint():
    r = client.post("/api/v1/molecular/log-normal", data={"Mn": "50000", "dispersity": "1.5"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dispersity"] == pytest.approx(1.5, rel=0.05)
    assert body["Mn"] == pytest.approx(50000, rel=0.05)
    assert body["Mn"] <= body["Mw"] <= body["Mz"]


# ---------------------------------------------------------------------------
# Service level
# ---------------------------------------------------------------------------


def test_root_lists_the_modules():
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert "molecular" in body["modules"]
    assert "thermal" in body["modules"]


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
