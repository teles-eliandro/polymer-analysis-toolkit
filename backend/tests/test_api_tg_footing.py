"""
The Tg footing has to survive the HTTP layer.

It was computed in the core routine and then silently dropped by the endpoint,
which rebuilds the response field by field: calling analyse_dsc() directly gave
+/-3.85 C on the real ABS trace, while POST /thermal/dsc returned null. A field
the API forgets is a field no user ever sees, so it is asserted here rather
than only at the core level.
"""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"
client = TestClient(app)


def _abs_body():
    d = json.loads((FIXTURES / "dsc_abs_ramp.json").read_text())
    return {
        "temperature": d["temperature_C"],
        "heat_flow": d["heat_flow_W_g"],
        "heating_rate": 10.0,
    }


def test_dsc_response_carries_the_tg_footing():
    r = client.post("/api/v1/thermal/dsc", json=_abs_body())
    assert r.status_code == 200
    body = r.json()

    assert body["Tg"] is not None
    assert body["Tg_uncertainty_C"] is not None, (
        "the API dropped the Tg footing that the core routine computed"
    )
    assert isinstance(body["Tg_reliable"], bool)


def test_a_clean_transition_comes_back_marked_reliable():
    """A strong, isolated step must not be flagged -- the field has to vary."""
    n = 1200
    T = [20.0 + 100.0 * i / (n - 1) for i in range(n)]
    hf = [-0.10 + 0.35 / (1 + pow(2.718281828, -(t - 75.0) / 3.0)) for t in T]

    r = client.post(
        "/api/v1/thermal/dsc",
        json={"temperature": T, "heat_flow": hf, "heating_rate": 10.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["Tg_reliable"] is True
    assert body["Tg_uncertainty_C"] < 3.0


def test_no_transition_means_no_footing_claim():
    """Without a Tg there is nothing to vouch for."""
    n = 300
    T = [20.0 + 200.0 * i / (n - 1) for i in range(n)]
    hf = [-0.10 for _ in T]
    r = client.post(
        "/api/v1/thermal/dsc",
        json={"temperature": T, "heat_flow": hf, "heating_rate": 10.0},
    )
    assert r.status_code == 200
    body = r.json()
    if body["Tg"] is None:
        assert body["Tg_uncertainty_C"] is None
        assert body["Tg_reliable"] is None
