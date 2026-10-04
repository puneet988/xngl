"""Small helpers shared by the render modules."""

from __future__ import annotations

import Ngl
import numpy as np

MISSING = 1e20


def to_resources(d: dict) -> Ngl.Resources:
    res = Ngl.Resources()
    for key, value in d.items():
        setattr(res, key, value)
    return res


def filled(values: np.ndarray) -> np.ndarray:
    """Replace NaN by the PyNGL missing value."""
    out = np.array(values, dtype=np.float64)
    out[~np.isfinite(out)] = MISSING
    return out
