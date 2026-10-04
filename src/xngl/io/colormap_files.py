"""Read NCL colormap files (.rgb, .gp, .ncmap) and the NCL named-colour table.

These files are plain text, so this module does not need Nio or Ngl.
"""

from __future__ import annotations

import re
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path

import numpy as np

_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _ncarg_dir() -> Path:
    spec = find_spec("ngl")
    if spec is None or spec.origin is None:
        raise FileNotFoundError("PyNGL (package 'ngl') is not installed")
    return Path(spec.origin).parent / "ncarg"


def builtin_colormap_dir() -> Path:
    """Folder of the colormap files that ship with PyNGL."""
    return _ncarg_dir() / "colormaps"


def read_colormap_file(path: Path | str) -> np.ndarray:
    """Return an N x 4 RGBA array with values from 0 to 1.

    Lines with ``ncolors=``, comments (``#`` or ``;``) and blank lines are skipped.
    Values greater than 1 are taken as 0-255 and divided by 255.
    """
    rows = []
    for line in Path(path).read_text(errors="replace").splitlines():
        line = line.split("#", 1)[0].split(";", 1)[0].strip()
        if not line or "=" in line:
            continue
        nums = _NUMBER.findall(line)
        if len(nums) >= 3:
            rows.append([float(n) for n in nums[:3]])
    if not rows:
        raise ValueError(f"no colours found in colormap file {path}")
    rgb = np.array(rows, dtype=np.float64)
    if rgb.max() > 1.0:
        rgb = rgb / 255.0
    rgb = np.clip(rgb, 0.0, 1.0)
    return np.column_stack([rgb, np.ones(len(rgb))])


@lru_cache(maxsize=1)
def read_named_colors() -> dict[str, tuple[float, float, float]]:
    """NCL named colours from ``rgb.txt``; keys are lowercase without spaces."""
    colors = {}
    for line in (_ncarg_dir() / "database" / "rgb.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) < 4 or not all(p.isdigit() for p in parts[:3]):
            continue
        name = "".join(parts[3:]).lower()
        colors.setdefault(name, tuple(int(p) / 255.0 for p in parts[:3]))
    return colors
