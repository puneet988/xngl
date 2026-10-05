"""Panel strings (left/centre/right) and lat/lon tick labels."""

from __future__ import annotations

import warnings

import Ngl
import numpy as np

from ..errors import RenderError, XnglWarning
from ..style import Style
from .util import to_resources

SIDES = {"left": (-0.5, "BottomLeft"), "center": (0.0, "BottomCenter"),
         "right": (0.5, "BottomRight")}


def add_strings(wks, plot, panel, style: Style) -> None:
    """Attach the panel strings above the plot frame with the annotation manager."""
    opts = style.options("strings")
    font = style.options("font").get("name")
    gap = float(opts.get("gap", 0.02))
    panel.string_ids, panel.strings_resolved = {}, {}
    for side, (parallel, just) in SIDES.items():
        text = getattr(panel.strings, side)
        if not text:
            continue
        tx = {"nglDraw": False, "nglFrame": False,
              "txFontHeightF": float(opts.get("font_height", 0.02))}
        if font:
            tx["txFont"] = font
        text_obj = Ngl.text_ndc(wks, text, 0.0, 0.0, to_resources(tx))
        am = {"amZone": 0, "amOrthogonalPosF": -0.5 - gap, "amParallelPosF": parallel,
              "amJust": just, "amResizeNotify": True}
        anno = Ngl.add_annotation(plot, text_obj, to_resources(am))
        if text_obj is None or anno is None:
            raise RenderError(f"panel string '{side}' could not be attached")
        panel.string_ids[side] = text_obj
        panel.attached.append(anno)
        panel.strings_resolved[side] = {**tx, **am}


def _fmt(v: float) -> str:
    return f"{v:g}"


def tick_labels(values, axis: str) -> list[str]:
    """Labels like 60E, 160W, 10N, 10S; 0 and 180 have no letter."""
    out = []
    for v in values:
        v = float(v)
        if axis == "lon":
            w = ((v + 180.0) % 360.0) - 180.0
            if np.isclose(w, 0.0):
                out.append("0")
            elif np.isclose(abs(w), 180.0):
                out.append("180")
            else:
                out.append(f"{_fmt(abs(w))}{'E' if w > 0 else 'W'}")
        else:
            out.append("0" if np.isclose(v, 0.0) else f"{_fmt(abs(v))}{'N' if v > 0 else 'S'}")
    return out


def _tick_values(spec, lo: float, hi: float) -> np.ndarray | None:
    if spec is None:
        return None
    if np.isscalar(spec):
        step = float(spec)
        start = np.ceil(lo / step - 1e-9) * step
        return np.round(np.arange(start, hi + step * 1e-6, step), 10)
    return np.asarray(spec, dtype=np.float64)


def tick_request(panel, style: Style):
    """(lon_spec, lat_spec) or None when xngl does not draw tick labels."""
    opts = style.options("ticks")
    ticks = panel.ticks
    lon = ticks.lon if ticks and ticks.lon is not None else opts.get("lon_spacing")
    lat = ticks.lat if ticks and ticks.lat is not None else opts.get("lat_spacing")
    if lon is None and lat is None:
        return None
    return lon, lat


def uses_xngl_ticks(panel, style: Style) -> bool:
    return (panel.base is not None and tick_request(panel, style) is not None
            and panel.base.projection == "CylindricalEquidistant")


def add_ticks(wks, plot, panel, fig, style: Style) -> None:
    """Blank-plot overlay with explicit lat/lon labels (CylindricalEquidistant only)."""
    panel.ticks_resolved = None
    panel.tick_id = None
    request = tick_request(panel, style)
    if request is None:
        return
    if panel.base.projection != "CylindricalEquidistant":
        warnings.warn(f"set_ticks: panel {panel.index} uses {panel.base.projection}; xngl tick "
                      "labels work only with CylindricalEquidistant, so PyNGL's default "
                      "ticks are used", XnglWarning, stacklevel=4)
        return
    opts = style.options("ticks")
    font = style.options("font").get("name")
    res = {"nglDraw": False, "nglFrame": False, "tfDoNDCOverlay": True}
    for k in ("vpXF", "vpYF", "vpWidthF", "vpHeightF", "trXMinF", "trXMaxF", "trYMinF",
              "trYMaxF"):
        res[k] = Ngl.get_float(plot, k)
    lon_vals = _tick_values(request[0], res["trXMinF"], res["trXMaxF"])
    lat_vals = _tick_values(request[1], res["trYMinF"], res["trYMaxF"])
    for axis, vals, side in (("lon", lon_vals, "XB"), ("lat", lat_vals, "YL")):
        if vals is not None:
            res[f"tm{side}Mode"] = "Explicit"
            res[f"tm{side}Values"] = vals
            res[f"tm{side}Labels"] = tick_labels(vals, axis)
    height = float(opts.get("label_font_height", 0.016))
    res.update(tmXBLabelFontHeightF=height, tmYLLabelFontHeightF=height,
               tmXBMinorOn=False, tmYLMinorOn=False, tmXTMinorOn=False, tmYRMinorOn=False,
               nglPointTickmarksOutward=bool(opts.get("outward", False)))
    if font:
        res.update(tmXBLabelFont=font, tmYLLabelFont=font)
    row, col = panel.index
    outer = bool(opts.get("outer_only", False))
    res["tmYLLabelsOn"] = not (outer and col > 0)
    res["tmXBLabelsOn"] = not (outer and row < fig.nrows - 1)
    res.update(style.res("ticks"))
    blank = Ngl.blank_plot(wks, to_resources(res))
    if blank is None:
        raise RenderError("tick labels: Ngl.blank_plot returned no plot")
    Ngl.overlay(plot.base, blank)
    panel.attached.append(blank)
    panel.tick_id = blank
    panel.ticks_resolved = dict(res)
