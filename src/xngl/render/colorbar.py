"""Colour bars: modes per panel, the shared all-panel labelbar, and group labelbars."""

from __future__ import annotations

import warnings

import Ngl
import numpy as np

from ..colors.colorbar import ColorbarSpec
from ..errors import RenderError, XnglWarning
from .util import to_resources

DEFAULT_THICKNESS = 0.06
DEFAULT_OFFSET = 0.04
GROUP_LABEL_HEIGHT = 0.012
GROUP_TITLE_HEIGHT = 0.014


def colorbar_modes(fig) -> dict[tuple[int, int], str]:
    """'own', 'shared' or 'none' for each panel."""
    shared = {ax.index for group, _ in fig.colorbars for ax in group}
    modes = {}
    for ax in fig.panels:
        if ax.base is not None and ax.base.colorbar:
            modes[ax.index] = "own"
        elif ax.index in shared:
            modes[ax.index] = "shared"
        else:
            modes[ax.index] = "none"
    return modes


def all_panel_group(fig) -> tuple[list, ColorbarSpec] | None:
    """The colour bar group that covers every panel with a plot, if there is one."""
    drawn = {ax.index for ax in fig.panels if ax.base is not None}
    for group, spec in fig.colorbars:
        if {ax.index for ax in group} == drawn:
            return group, spec
    return None


def _palette(first) -> np.ndarray:
    spec = first.base
    if spec.cmap is not None:
        return np.array(spec.cmap.for_levels(spec.levels).rgba)
    return np.asarray(Ngl.get_integer_array(first.ngl_plot.contour, "cnFillColors"))


def draw_colorbars(wks, fig) -> None:
    """Draw every group colour bar that does not cover all panels (Ngl.labelbar_ndc)."""
    full = all_panel_group(fig)
    for group, spec in fig.colorbars:
        if full is not None and group is full[0]:
            continue
        boxes = np.array([Ngl.get_bounding_box(ax.ngl_plot) for ax in group])  # top,bottom,l,r
        frames = [(Ngl.get_float(ax.ngl_plot, "vpXF"), Ngl.get_float(ax.ngl_plot, "vpYF"),
                   Ngl.get_float(ax.ngl_plot, "vpWidthF"), Ngl.get_float(ax.ngl_plot, "vpHeightF"))
                  for ax in group]
        x0 = min(f[0] for f in frames)
        x1 = max(f[0] + f[2] for f in frames)
        ytop = max(f[1] for f in frames)
        ybot = min(f[1] - f[3] for f in frames)
        offset = spec.offset if spec.offset is not None else DEFAULT_OFFSET
        if spec.orientation == "vertical":
            w = spec.width or DEFAULT_THICKNESS
            h = spec.height or (ytop - ybot)
            x, y = float(boxes[:, 3].max()) + offset, ytop
        else:
            w = spec.width or (x1 - x0)
            h = spec.height or DEFAULT_THICKNESS
            x, y = x0, float(boxes[:, 1].min()) - offset
        levels = group[0].base.levels
        colors = _palette(group[0])
        labels = [spec.label_format.format(v) if spec.label_format else f"{v:g}" for v in levels]
        res = {"vpWidthF": float(w), "vpHeightF": float(h), "lbFillColors": colors,
               "lbMonoFillPattern": True, "lbLabelAlignment": "InteriorEdges",
               "lbPerimOn": False, **spec.to_res(levels)}
        font = fig.style.options("font").get("name")
        if font:
            res.setdefault("lbLabelFont", font)
            res.setdefault("lbTitleFont", font)
        # labelbar_ndc scales fonts with the bar size; fixed defaults keep them readable
        res.setdefault("lbLabelFontHeightF", GROUP_LABEL_HEIGHT)
        res.setdefault("lbTitleFontHeightF", GROUP_TITLE_HEIGHT)
        spec.resolved = dict(res)
        lb = Ngl.labelbar_ndc(wks, len(colors), labels, float(x), float(y), to_resources(res))
        if lb is None:
            raise RenderError("Ngl.labelbar_ndc returned no labelbar")
        spec.drawn_box = (float(x), float(y), float(w), float(h))
        if x < 0 or y - h < 0 or x + w > 1 or y > 1:
            warnings.warn(f"colorbar for panels {[ax.index for ax in group]} is outside the "
                          "page; set panel_res nglPanelBottom / nglPanelRight or the colorbar "
                          "offset", XnglWarning, stacklevel=4)
