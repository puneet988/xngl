"""Panel: one plot area of a Figure. Methods check input at once and record layers."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import xarray as xr

from .colors.colormaps import to_colormap
from .coords import covers_extent, prepare_field, same_grid
from .errors import DataError, StyleError, XnglError, XnglWarning
from .specs import (
    BoxSpec,
    ContourSpec,
    CustomSpec,
    Layer,
    ShapefileSpec,
    StippleSpec,
    StringsSpec,
    TicksSpec,
    VectorSpec,
)
from .style import LOCKED

FILLS = ("area", "raster", "cell")


def _check_res(res: dict | None, what: str) -> dict:
    res = dict(res or {})
    bad = sorted(set(res) & LOCKED)
    if bad:
        raise StyleError(f"{what}: {bad[0]} is locked: xngl sets it to control drawing")
    return res


class Panel:
    """A plot area. Create panels through :class:`xngl.Figure`."""

    def __init__(self, index: tuple[int, int]):
        self.index = tuple(index)
        self.base: ContourSpec | None = None
        self.layers: list[Layer] = []
        self.ticks: TicksSpec | None = None
        self.strings = StringsSpec()
        self.ngl_plot = None
        self.attached: list = []  # PyNGL ids of overlays (kept alive with the plot)
        self.string_ids: dict = {}
        self.strings_resolved: dict = {}
        self.ticks_resolved: dict | None = None

    def __repr__(self) -> str:
        return f"Panel{self.index}"

    def _need_base(self, what: str) -> ContourSpec:
        if self.base is None:
            raise XnglError(f"{what}: add a contour_map to this panel first")
        return self.base

    def contour_map(self, da: xr.DataArray, levels=None, cmap=None, lat=None, lon=None,
                    fill=None, colorbar=False, left=None, center=None, right=None,
                    projection="CylindricalEquidistant", res=None) -> ContourSpec:
        if self.base is not None:
            raise XnglError(f"contour_map: panel {self.index} already has a contour_map")
        field = prepare_field(da, what="contour_map")
        if levels is not None:
            levels = np.asarray(levels, dtype=np.float64)
            if levels.ndim != 1 or levels.size < 1 or np.any(np.diff(levels) <= 0):
                raise DataError("contour_map: levels must increase")
            lo, hi = np.nanmin(field.values), np.nanmax(field.values)
            if lo < levels[0] or hi > levels[-1]:
                warnings.warn(f"contour_map: levels {levels[0]:g}..{levels[-1]:g} do not cover "
                              f"the data range {lo:g}..{hi:g}", XnglWarning, stacklevel=2)
        if fill is not None and fill not in FILLS:
            raise DataError(f"contour_map: fill={fill!r} is not valid; use one of {FILLS}")
        if not covers_extent(field, lat, lon):
            warnings.warn("contour_map: the data do not cover the map extent",
                          XnglWarning, stacklevel=2)
        spec = ContourSpec(field=field, levels=levels,
                           cmap=to_colormap(cmap) if cmap is not None else None,
                           lat=tuple(lat) if lat is not None else None,
                           lon=tuple(lon) if lon is not None else None,
                           fill=fill, colorbar=colorbar, projection=projection,
                           res=_check_res(res, "contour_map"))
        self.base = spec
        self.layers.append(spec)
        self.set_strings(left=left, center=center, right=right)
        return spec

    def vectors(self, u, v, stride=None, ref_magnitude=None, ref_label=None, color=None,
                thickness=None, res=None) -> VectorSpec:
        self._need_base("vectors")
        fu, fv = prepare_field(u, what="vectors u"), prepare_field(v, what="vectors v")
        if not same_grid(fu, fv):
            raise DataError("vectors: u and v are on different grids")
        spec = VectorSpec(u=fu, v=fv, stride=stride, ref_magnitude=ref_magnitude,
                          ref_label=ref_label, color=color, thickness=thickness,
                          res=_check_res(res, "vectors"))
        self.layers.append(spec)
        return spec

    def add_shapefile(self, path, select=None, color=None, thickness=None, dash=None,
                      res=None) -> ShapefileSpec:
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            raise DataError(f"add_shapefile: file not found: {p}")
        spec = ShapefileSpec(path=p, select=select, color=color, thickness=thickness, dash=dash,
                             res=_check_res(res, "add_shapefile"))
        self.layers.append(spec)
        return spec

    def add_box(self, lat, lon, color=None, thickness=None, res=None) -> BoxSpec:
        spec = BoxSpec(lat=tuple(lat), lon=tuple(lon), color=color, thickness=thickness,
                       res=_check_res(res, "add_box"))
        self.layers.append(spec)
        return spec

    def stipple(self, mask, marker=None, size=None, color=None, stride=1, res=None) -> StippleSpec:
        base = self._need_base("stipple")
        if not isinstance(mask, xr.DataArray) or mask.dtype != bool:
            raise DataError("stipple: mask must be a boolean DataArray, e.g. pvals < 0.05")
        field = prepare_field(mask.astype(np.float64), what="stipple")
        if not same_grid(field, base.field):
            raise DataError("stipple: mask grid does not match the contour data grid")
        spec = StippleSpec(mask=field, marker=marker, size=size, color=color, stride=int(stride),
                           res=_check_res(res, "stipple"))
        self.layers.append(spec)
        return spec

    def set_ticks(self, lon=None, lat=None) -> None:
        self.ticks = TicksSpec(lon=lon, lat=lat)

    def set_strings(self, left=None, center=None, right=None) -> None:
        for side, text in (("left", left), ("center", center), ("right", right)):
            if text is not None:
                setattr(self.strings, side, text)

    def add_custom(self, func) -> CustomSpec:
        if not callable(func):
            raise XnglError("add_custom: func must be callable as func(wks, plot, panel)")
        spec = CustomSpec(func=func)
        self.layers.append(spec)
        return spec
