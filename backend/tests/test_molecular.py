import pytest
from app.core.calculations import validate_inputs, calculate_molecular_properties

def test_valid_calculation():
    masses = [1000, 2000, 5000]
    w = [0.2, 0.5, 0.3]
    Mn, Mw, D = calculate_molecular_properties(masses, w)
    assert Mn > 0
    assert Mw > 0
    assert D >= 1.0

def test_invalid_sum():
    with pytest.raises(ValueError, match="sum to 1.0"):
        validate_inputs([1000], [0.5])

def test_negative_mass():
    with pytest.raises(ValueError, match="positive"):
        validate_inputs([-100], [1.0])