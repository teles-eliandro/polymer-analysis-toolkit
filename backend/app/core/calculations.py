import numpy as np
from typing import List, Tuple

def validate_inputs(masses: List[float], weight_fractions: List[float], tol: float = 1e-3) -> None:
    if len(masses) != len(weight_fractions):
        raise ValueError("Masses and weight fractions must have the same length.")
    if len(masses) == 0:
        raise ValueError("Input lists cannot be empty.")
    if any(m <= 0 for m in masses):
        raise ValueError("All masses must be positive.")
    if any(w < 0 for w in weight_fractions):
        raise ValueError("Weight fractions must be non-negative.")
    total = sum(weight_fractions)
    if abs(total - 1.0) > tol:
        raise ValueError(f"Weight fractions must sum to 1.0 (within tolerance {tol}). Got {total:.6f}.")

def calculate_molecular_properties(masses: List[float], weight_fractions: List[float]) -> Tuple[float, float, float]:
    masses = np.array(masses, dtype=np.float64)
    w = np.array(weight_fractions, dtype=np.float64)

    M_w = np.sum(w * masses)
    M_n = 1.0 / np.sum(w / masses)
    dispersity = M_w / M_n

    return float(M_n), float(M_w), float(dispersity)