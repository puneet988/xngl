"""Base plots: specs -> Ngl.contour_map (vectors are added in this module too)."""

from __future__ import annotations

import warnings

import Ngl
import numpy as np

from ..colors.colorbar import ColorbarSpec
from ..coords import default_label
from ..errors import RenderError, XnglWarning
from ..specs import ContourSpec, VectorSpec
from ..style import Style, merge_resources
from .util import MISSING, filled, to_resources

FILL_MODES = {"area": "AreaFill", "raster": "RasterFill", "cell": "CellFill"}


def own_colorbar_spec(spec: ContourSpec, style: Style) -> ColorbarSpec:
    options = dict(style.options("colorbar"))
    res = dict(style.res("colorbar"))
    if isinstance(spec.colorbar, dict):
        extra = dict(spec.colorbar)
        res.update(extra.pop("res", {}))
        options.update(extra)
    cb = ColorbarSpec.from_options({**options, "res": res})
    if cb.label is None:
        cb.label = default_label(spec.field)
    return cb


def contour_keyword_res(spec: ContourSpec, style: Style, colorbar_mode: str) -> dict:
    opts = style.options("contour")
    field = spec.field
    font = style.options("font").get("name")
    fill = spec.fill or opts.get("fill", "area")
    r = {
        "cnFillOn": True,
        "cnFillMode": FILL_MODES[fill],
        "cnLinesOn": bool(opts.get("lines", False)),
        "cnLineLabelsOn": bool(opts.get("line_labels", False)),
        "sfMissingValueV": MISSING,
        "cnMissingValFillColor": "transparent",
        "mpProjection": spec.projection,
        "mpLimitMode": "LatLon",
        "mpMinLatF": float(spec.lat[0] if spec.lat else np.nanmin(field.lat)),
        "mpMaxLatF": float(spec.lat[1] if spec.lat else np.nanmax(field.lat)),
        "mpMinLonF": float(spec.lon[0] if spec.lon else np.nanmin(field.lon)),
        "mpMaxLonF": float(spec.lon[1] if spec.lon else np.nanmax(field.lon)),
        "lbLabelBarOn": colorbar_mode == "own",
    }
    if font:
        r.update(tiMainFont=font, lbLabelFont=font, lbTitleFont=font)
    if spec.levels is not None:
        r.update(cnLevelSelectionMode="ExplicitLevels", cnLevels=np.asarray(spec.levels))
    cmap = spec.cmap
    if cmap is None and opts.get("cmap"):
        from ..colors.colormaps import to_colormap

        cmap = to_colormap(opts["cmap"])
    if cmap is not None:
        rgba = cmap.for_levels(spec.levels).rgba if spec.levels is not None else cmap.rgba
        r["cnFillPalette"] = np.array(rgba)
    if colorbar_mode == "own":
        r.update(own_colorbar_spec(spec, style).to_res(spec.levels))
    return r


def build_contour(wks, spec: ContourSpec, style: Style, colorbar_mode: str,
                  ticks_off: bool = False):
    field = spec.field
    if spec.levels is None and np.nanmin(field.values) == np.nanmax(field.values):
        warnings.warn(f"contour_map: field '{field.name}' is constant; no contour levels",
                      XnglWarning, stacklevel=4)
    extra_locked = frozenset({"pmLabelBarDisplayMode"}) if colorbar_mode == "shared" else frozenset()
    locked = {"nglDraw": False, "nglFrame": False, "sfXArray": field.lon, "sfYArray": field.lat}
    keyword = contour_keyword_res(spec, style, colorbar_mode)
    if ticks_off:  # xngl draws its own lat/lon labels (blank-plot overlay)
        keyword["pmTickMarkDisplayMode"] = "Never"
    res = merge_resources(style_res={**style.res("map"), **style.res("contour")},
                          keyword_res=keyword,
                          user_res=spec.res, locked=locked, extra_locked=extra_locked)
    spec.resolved = dict(res)
    plot = Ngl.contour_map(wks, filled(field.values), to_resources(res))
    if plot is None:
        raise RenderError("Ngl.contour_map returned no plot")
    return plot


def vector_keyword_res(spec: VectorSpec, style: Style) -> dict:
    opts = style.options("vectors")
    r = {
        "vcLineArrowColor": spec.color or opts.get("color", "black"),
        "vcLineArrowThicknessF": float(spec.thickness or opts.get("thickness", 1.0)),
        "vfMissingUValueV": MISSING,
        "vfMissingVValueV": MISSING,
        "vcRefAnnoOn": spec.ref_label is not None,
    }
    if spec.stride:
        r.update(vfXCStride=int(spec.stride), vfYCStride=int(spec.stride))
    if spec.ref_magnitude is not None:
        r["vcRefMagnitudeF"] = float(spec.ref_magnitude)
    if spec.ref_label is not None:
        r["vcRefAnnoString1"] = spec.ref_label
    return r


def build_vectors(wks, spec: VectorSpec, style: Style, base_plot):
    """Ngl.vector on the u/v grid, overlaid on the panel's base plot."""
    locked = {"nglDraw": False, "nglFrame": False}
    keyword = vector_keyword_res(spec, style)
    keyword.update(vfXArray=spec.u.lon, vfYArray=spec.u.lat)
    res = merge_resources(style_res=style.res("vectors"), keyword_res=keyword,
                          user_res=spec.res, locked=locked)
    spec.resolved = dict(res)
    vec = Ngl.vector(wks, filled(spec.u.values), filled(spec.v.values), to_resources(res))
    if vec is None:
        raise RenderError("Ngl.vector returned no plot")
    Ngl.overlay(base_plot, vec)
    return vec
