"""The Colormap object, the colormap registry and colormap operations.

All colours are RGBA arrays with values from 0 to 1. Every operation returns a
new Colormap; the original is never changed.
"""

from __future__ import annotations

import builtins
import difflib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path

import numpy as np

from ..errors import StyleError
from ..io.colormap_files import builtin_colormap_dir, read_colormap_file, read_named_colors

_REGISTRY: dict[str, Colormap] = {}


def _as_rgba(arr, what: str = "colours") -> np.ndarray:
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] not in (3, 4) or a.shape[0] < 1:
        raise StyleError(f"{what}: expected an N x 3 or N x 4 array, got shape {a.shape}")
    if a.shape[1] == 3:
        a = np.column_stack([a, np.ones(len(a))])
    if a.max() > 1.0:
        a = a.copy()
        a[:, :3] = a[:, :3] / 255.0
    return np.clip(a, 0.0, 1.0)


@dataclass(frozen=True, eq=False)
class Colormap:
    """A named list of colours (N x 4 RGBA, values 0..1)."""

    name: str
    rgba: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "rgba", _as_rgba(self.rgba, f"colormap '{self.name}'"))
        self.rgba.setflags(write=False)

    def __len__(self) -> int:
        return len(self.rgba)

    def _new(self, rgba, suffix: str) -> Colormap:
        return Colormap(f"{self.name}{suffix}", np.array(rgba))

    def reversed(self) -> Colormap:
        return self._new(self.rgba[::-1], "_r")

    def truncate(self, lo: float, hi: float) -> Colormap:
        """Keep the colours between fractions ``lo`` and ``hi`` (0..1) of the map."""
        if not 0.0 <= lo < hi <= 1.0:
            raise StyleError(f"truncate: need 0 <= lo < hi <= 1, got lo={lo}, hi={hi}")
        n = len(self.rgba)
        i0 = round(lo * (n - 1))
        i1 = round(hi * (n - 1))
        return self._new(self.rgba[i0:i1 + 1], f"_t{lo:g}-{hi:g}")

    def resample(self, n: int) -> Colormap:
        """``n`` colours, linearly interpolated over the map."""
        if n < 1:
            raise StyleError(f"resample: n must be >= 1, got {n}")
        x_old = np.linspace(0.0, 1.0, len(self.rgba))
        x_new = np.linspace(0.0, 1.0, n)
        rgba = np.column_stack([np.interp(x_new, x_old, self.rgba[:, k]) for k in range(4)])
        return self._new(rgba, f"_{n}")

    def expand_middle(self, n: int) -> Colormap:
        """Repeat the middle colour ``n`` times (``map_funcs.expand_colormap_middle``)."""
        if n < 1:
            raise StyleError(f"expand_middle: n must be >= 1, got {n}")
        mid = len(self.rgba) // 2
        rgba = np.vstack([self.rgba[:mid], np.repeat(self.rgba[mid:mid + 1], n, axis=0),
                          self.rgba[mid + 1:]])
        return self._new(rgba, f"_x{n}")

    def add_colors(self, colors, where: str = "end") -> Colormap:
        """Add colours (names or RGB/RGBA rows) at the ``"start"`` or ``"end"``."""
        if where not in ("start", "end"):
            raise StyleError(f"add_colors: where must be 'start' or 'end', got {where!r}")
        extra = _colors_to_rgba(colors)
        rgba = np.vstack([extra, self.rgba] if where == "start" else [self.rgba, extra])
        return self._new(rgba, "+")

    def for_levels(self, levels) -> Colormap:
        """Exactly ``len(levels) + 1`` evenly spaced colours from this map."""
        k = len(np.asarray(levels)) + 1
        idx = np.linspace(0, len(self.rgba) - 1, k).round().astype(int)
        return self._new(self.rgba[idx], f"_{k}")

    def __add__(self, other: Colormap) -> Colormap:
        return combine(self, other)


def _colors_to_rgba(colors) -> np.ndarray:
    named = read_named_colors()
    rows = []
    for c in colors:
        if isinstance(c, str):
            key = c.replace(" ", "").lower()
            if key not in named:
                close = difflib.get_close_matches(key, named.keys(), n=1)
                hint = f'; did you mean "{close[0]}"?' if close else ""
                raise StyleError(f'unknown colour "{c}"{hint}')
            rows.append([*named[key], 1.0])
        else:
            rows.append(_as_rgba([c])[0])
    return np.array(rows, dtype=np.float64)


@lru_cache(maxsize=1)
def _custom_maps() -> dict[str, list]:
    text = files("xngl.colors").joinpath("data/custom_colormaps.json").read_text()
    return json.loads(text)["maps"]


@lru_cache(maxsize=1)
def _builtin_files() -> dict[str, Path]:
    return {p.stem: p for p in sorted(builtin_colormap_dir().iterdir()) if p.is_file()}


def list() -> builtins.list[str]:
    """All colormap names: registered, custom (map_funcs.py) and built-in NCL maps."""
    return sorted(set(_REGISTRY) | set(_custom_maps()) | set(_builtin_files()))


def get(spec: str | Path) -> Colormap:
    """Look up a colormap by name, or read it from a colormap file path."""
    key = str(spec)
    if key in _REGISTRY:
        return _REGISTRY[key]
    if key in _custom_maps():
        return Colormap(key, np.array(_custom_maps()[key], dtype=np.float64) / 255.0)
    if key in _builtin_files():
        return Colormap(key, read_colormap_file(_builtin_files()[key]))
    path = Path(key).expanduser()
    if path.suffix and path.is_file():
        return Colormap(path.stem, read_colormap_file(path))
    close = difflib.get_close_matches(key, list(), n=3)
    hint = f'; did you mean "{close[0]}"?' if close else ""
    raise StyleError(f'unknown colormap "{key}"{hint}')


def from_colors(colors, n: int) -> Colormap:
    """Interpolate ``n`` colours through the given colour names or RGB rows."""
    base = Colormap("from_colors", _colors_to_rgba(colors))
    return Colormap("from_colors", base.resample(n).rgba)


def from_array(arr, name: str = "custom") -> Colormap:
    return Colormap(name, np.asarray(arr, dtype=np.float64))


def combine(*cms: Colormap) -> Colormap:
    """Join colormaps end to end."""
    if not cms:
        raise StyleError("combine: give at least one colormap")
    return Colormap("+".join(c.name for c in cms), np.vstack([c.rgba for c in cms]))


def register(name: str, cm: Colormap) -> None:
    """Make ``cm`` available as ``cmap=name`` everywhere."""
    _REGISTRY[name] = Colormap(name, np.array(cm.rgba))


def to_colormap(arg) -> Colormap:
    """Accept a name, a path, a Colormap or an N x 3 / N x 4 array."""
    if isinstance(arg, Colormap):
        return arg
    if isinstance(arg, (str, Path)):
        return get(arg)
    return Colormap("custom", _as_rgba(arg, "cmap"))
