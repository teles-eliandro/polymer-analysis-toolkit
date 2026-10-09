"""
Every number the analysis reports must say what it is worth.

The interface change this guards
--------------------------------
``analyse_dsc`` returned bare floats. A reader could not tell a property of
the file from an inference, so a Tg that is a guess looked exactly like a Tg
that is a measurement. The actual measured behaviour on the figshare 24462004
set is that the Tg lands in the published window on roughly 30 % of the 116
traces, and that the detector has reported a melting temperature for amorphous
polystyrene -- which cannot melt. Numbers like that must not be presented as
measurements.

The confidence ladder has three rungs and they are not degrees of the same
thing:

    read      a property of the input, or a deterministic transform of it
    formula   a published formula applied to a declared input; reproducible
    suggested an inference from the shape of the trace; can be wrong

The rule this file enforces is that no transition temperature is ever
``read`` or ``formula``. A temperature is always an inference. And every
suggested field must carry evidence and a note, because a suggestion with no
stated basis is just a number with a friendlier label.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.core.thermal import (
    FORMULA,
    READ,
    SUGGESTED,
    _CONFIDENCE_RANK,
    analyse_dsc,
)

FIXTURES = Path(__file__).parent / "fixtures"
PLA = FIXTURES / "dsc_pla_ramp.json"


def _pla():
    data = json.loads(PLA.read_text())
    return data["temperature_C"], data["heat_flow_W_g"]


def _synthetic_amorphous():
    T = np.linspace(30.0, 180.0, 3000)
    step = -0.35 / (1.0 + np.exp(-(T - 105.0) / 2.5))
    return T.tolist(), (0.02 + 1e-4 * T + step).tolist()


@pytest.mark.skipif(not PLA.exists(), reason="PLA fixture not present")
def test_transition_temperatures_are_never_claimed_as_measured():
    """A temperature found by shape analysis is a suggestion, always."""
    T, hf = _pla()
    r = analyse_dsc(T, hf, heating_rate=10.0)

    for field in ("Tg", "Tm", "Tc"):
        claim = r.claims.get(field)
        if claim is None:
            continue
        assert claim.confidence == SUGGESTED, (
            f"{field} was labelled {claim.confidence!r}; a transition "
            "temperature inferred from the trace shape is never a measurement"
        )


def test_a_suggested_claim_carries_evidence_and_a_note():
    """
    A suggestion with no stated basis is just a number with a friendlier label.
    """
    T, hf = _pla() if PLA.exists() else _synthetic_amorphous()
    r = analyse_dsc(T, hf, heating_rate=10.0)

    suggested = [k for k, c in r.claims.items() if c.confidence == SUGGESTED]
    assert suggested, "this trace must produce at least one suggestion"
    for field in suggested:
        claim = r.claims[field]
        assert claim.evidence, f"{field} is suggested but states no evidence"
        assert claim.note, f"{field} is suggested but carries no caveat"


def test_formula_fields_are_marked_reproducible_not_measured():
    """
    Enthalpy and crystallinity are formulas, not readings: they are only as
    good as the integration bounds, which come from a suggested peak.
    """
    T, hf = _pla() if PLA.exists() else _synthetic_amorphous()
    r = analyse_dsc(T, hf, heating_rate=10.0, ref_enthalpy_J_g=139.5)

    for field in ("delta_Hm", "crystallinity_pct", "delta_cp"):
        claim = r.claims.get(field)
        if claim is None:
            continue
        assert claim.confidence == FORMULA, (
            f"{field} was labelled {claim.confidence!r}; it is a formula over "
            "a declared input, so it must say so"
        )
        assert claim.evidence, f"{field} is a formula claim with no cited basis"


def test_confidence_ladder_is_ordered():
    """read < formula < suggested, so callers can compare and sort."""
    assert _CONFIDENCE_RANK[READ] < _CONFIDENCE_RANK[FORMULA]
    assert _CONFIDENCE_RANK[FORMULA] < _CONFIDENCE_RANK[SUGGESTED]


def test_claims_serialise_with_the_numbers():
    """The claims must travel with the result, otherwise the UI cannot show them."""
    T, hf = PLA.exists() and _pla() or _synthetic_amorphous()
    r = analyse_dsc(T, hf, heating_rate=10.0)
    d = r.as_dict()

    assert "claims" in d
    assert isinstance(d["claims"], dict)
    for field, claim in d["claims"].items():
        assert set(claim) == {"value", "confidence", "evidence", "note"}, (
            f"{field} serialised with the wrong shape: {sorted(claim)}"
        )
        assert claim["confidence"] in (READ, FORMULA, SUGGESTED)
