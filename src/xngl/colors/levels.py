"""Level helpers for contour plots and colour bars."""

from __future__ import annotations

import numpy as np

from ..errors import StyleError


def symmetric_levels(limit: float, step: float) -> np.ndarray:
    """Levels from ``-limit`` to ``+limit`` with spacing ``step``."""
    if limit <= 0 or step <= 0:
        raise StyleError(f"symmetric_levels: limit and step must be > 0, got {limit}, {step}")
    n = round(2 * limit / step) + 1
    return np.linspace(-limit, limit, n)


def nice_levels(data, n: int = 10) -> np.ndarray:
    """About ``n`` rounded levels that cover the finite range of ``data``."""
    values = np.asarray(data, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise StyleError("nice_levels: data contain no finite values")
    lo, hi = float(values.min()), float(values.max())
    if lo == hi:
        return np.array([lo])
    raw = (hi - lo) / max(n, 1)
    mag = 10.0 ** np.floor(np.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw), default=10 * mag)
    start = np.floor(lo / step) * step
    stop = np.ceil(hi / step) * step
    return np.round(np.arange(start, stop + step / 2, step), 12)
