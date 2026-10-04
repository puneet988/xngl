"""Overlays attached to a plot: shapefiles, boxes, stippling, and custom hooks."""

from __future__ import annotations

import Ngl
import numpy as np

from ..errors import RenderError
from ..io.shapefile import read_shapefile
from ..specs import BoxSpec, CustomSpec, ShapefileSpec, StippleSpec
from ..style import Style, merge_resources
from .util import to_resources

MARKERS = {"dot": 1, "plus": 2, "asterisk": 3, "circle": 4, "cross": 5, "square": 6,
           "filled_circle": 16}


def _line_res(spec, style: Style, part: str) -> dict:
    opts = style.options(part)
    keyword = {
        "gsLineColor": spec.color or opts.get("color", "black"),
        "gsLineThicknessF": float(spec.thickness or opts.get("thickness", 1.0)),
    }
    dash = getattr(spec, "dash", None)
    if part == "shapefile":
        keyword["gsLineDashPattern"] = int(dash if dash is not None else opts.get("dash", 0))
    return keyword


def stipple_points(spec: StippleSpec) -> tuple[np.ndarray, np.ndarray]:
    """Longitudes and latitudes of the masked points, thinned by ``stride``."""
    f = spec.mask
    lon, lat = (f.lon, f.lat) if f.curvilinear else np.meshgrid(f.lon, f.lat)
    s = max(int(spec.stride), 1)
    m = np.nan_to_num(f.values[::s, ::s]) > 0.5
    return lon[::s, ::s][m], lat[::s, ::s][m]


def _attach(panel, prim):
    if prim is None:
        raise RenderError("PyNGL returned no primitive")
    panel.attached.append(prim)


def add_overlays(wks, plot, panel, style: Style) -> None:
    for layer in panel.layers[1:]:
        if isinstance(layer, ShapefileSpec):
            shape = read_shapefile(layer.path, layer.select)
            keyword = {**_line_res(layer, style, "shapefile"), "gsSegments": shape.starts}
            res = merge_resources(style_res=style.res("shapefile"), keyword_res=keyword,
                                  user_res=layer.res, locked={})
            layer.resolved = dict(res)
            _attach(panel, Ngl.add_polyline(wks, plot, shape.lon, shape.lat, to_resources(res)))
        elif isinstance(layer, BoxSpec):
            (la0, la1), (lo0, lo1) = layer.lat, layer.lon
            res = merge_resources(style_res=style.res("box"),
                                  keyword_res=_line_res(layer, style, "box"),
                                  user_res=layer.res, locked={})
            layer.resolved = dict(res)
            _attach(panel, Ngl.add_polyline(wks, plot, [lo0, lo1, lo1, lo0, lo0],
                                            [la0, la0, la1, la1, la0], to_resources(res)))
        elif isinstance(layer, StippleSpec):
            opts = style.options("stipple")
            marker = layer.marker if layer.marker is not None else opts.get("marker", "dot")
            if isinstance(marker, str):
                if marker not in MARKERS:
                    raise RenderError(f"stipple: unknown marker {marker!r}; use one of "
                                      f"{', '.join(MARKERS)} or an int")
                marker = MARKERS[marker]
            keyword = {"gsMarkerIndex": int(marker),
                       "gsMarkerSizeF": float(layer.size or opts.get("size", 0.004)),
                       "gsMarkerColor": layer.color or opts.get("color", "black")}
            res = merge_resources(style_res=style.res("stipple"), keyword_res=keyword,
                                  user_res=layer.res, locked={})
            layer.resolved = dict(res)
            lon, lat = stipple_points(layer)
            if lon.size:
                _attach(panel, Ngl.add_polymarker(wks, plot, lon, lat, to_resources(res)))


def run_custom(wks, plot, panel) -> None:
    for layer in panel.layers:
        if isinstance(layer, CustomSpec):
            layer.func(wks, plot, panel)
            layer.resolved = {}
