"""Read shapefiles with PyNIO, with feature selection and a per-session cache."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import Nio
import numpy as np

from ..errors import DataError
from . import NIO_LOCK

_GEOMETRY_VARS = {"x", "y", "z", "segments", "geometry"}
_CACHE: dict[tuple[str, int], dict] = {}


@dataclass(frozen=True)
class ShapeData:
    """Outline points and segment start indices (for the ``gsSegments`` resource)."""

    lon: np.ndarray
    lat: np.ndarray
    starts: np.ndarray


def clear_cache() -> None:
    _CACHE.clear()


def _decode(values: np.ndarray) -> np.ndarray:
    if values.dtype.kind == "S":
        return np.char.decode(values, "utf-8", errors="replace")
    return values


def _read_raw(path: Path) -> dict:
    path = Path(path).expanduser().resolve()
    key = (str(path), path.stat().st_mtime_ns)
    if key not in _CACHE:
        with NIO_LOCK:
            f = Nio.open_file(str(path), "r")
            try:
                raw = {
                    "x": np.ravel(np.asarray(f.variables["x"][:], dtype=np.float64)),
                    "y": np.ravel(np.asarray(f.variables["y"][:], dtype=np.float64)),
                    "segments": np.asarray(f.variables["segments"][:], dtype=np.int64),
                    "geometry": np.asarray(f.variables["geometry"][:], dtype=np.int64),
                    "attrs": {name: _decode(np.asarray(var[:]))
                              for name, var in f.variables.items()
                              if name not in _GEOMETRY_VARS and var.rank == 1},
                }
            finally:
                f.close()
        _CACHE[key] = raw
    return _CACHE[key]


def attribute_names(path: Path) -> list[str]:
    return sorted(_read_raw(path)["attrs"])


def read_shapefile(path: Path, select: dict | None = None) -> ShapeData:
    """Outlines of all features, or only those whose attributes match ``select``."""
    raw = _read_raw(path)
    if not select:
        return ShapeData(raw["x"], raw["y"], raw["segments"][:, 0].copy())
    keep = np.ones(len(raw["geometry"]), dtype=bool)
    for name, wanted in select.items():
        if name not in raw["attrs"]:
            raise DataError(f"add_shapefile: attribute '{name}' not found in {Path(path).name}; "
                            f"available attributes: {', '.join(attribute_names(path))}")
        wanted = [wanted] if isinstance(wanted, (str, int, float)) else list(wanted)
        values = raw["attrs"][name]
        keep &= np.isin(values.astype(str), [str(w) for w in wanted])
    if not keep.any():
        raise DataError(f"add_shapefile: no features match select={select}")
    lon_parts, lat_parts, starts, offset = [], [], [], 0
    for first, count in raw["geometry"][keep]:
        for start, npts in raw["segments"][first:first + count]:
            lon_parts.append(raw["x"][start:start + npts])
            lat_parts.append(raw["y"][start:start + npts])
            starts.append(offset)
            offset += npts
    return ShapeData(np.concatenate(lon_parts), np.concatenate(lat_parts), np.array(starts))
