"""Panel layout: placeholders for empty panels and the Ngl.panel call."""

from __future__ import annotations

import Ngl

from ..style import merge_resources
from .util import to_resources


def placeholder(wks):
    """An invisible plot for an empty panel (Ngl.panel cannot take None)."""
    res = {"nglDraw": False, "nglFrame": False}
    for side in ("XB", "XT", "YL", "YR"):
        res[f"tm{side}On"] = False
        res[f"tm{side}BorderOn"] = False
    return Ngl.blank_plot(wks, to_resources(res))


TITLE_TOP = 0.93


def panel_keyword_res(fig) -> dict:
    """Panel resources from figure options: tags, title space and colour bar space."""
    from ..figure import tag_strings
    r = {}
    tags = tag_strings(fig.tags, len(fig.panels))
    if tags:
        opts = fig.style.options("tags")
        r["nglPanelFigureStrings"] = [t if ax.base is not None else ""
                                      for t, ax in zip(tags, fig.panels, strict=False)]
        r["nglPanelFigureStringsFontHeightF"] = float(opts.get("font_height", 0.02))
        r["nglPanelFigureStringsJust"] = opts.get("just", "TopLeft")
    if fig.title:
        r["nglPanelTop"] = TITLE_TOP
    r.update(_group_bar_space(fig))
    return r


GROUP_BAR_SPACE = 0.12      # page fraction kept free under the last row / right of last column
GROUP_BAR_GAP_PERCENT = 30  # extra white space between rows/columns with a bar between them


def _group_bar_space(fig) -> dict:
    """Reserve room for shared colour bars so they stay on the page."""
    r = {}
    for group, spec in fig.colorbars:
        if spec.orientation == "vertical":
            if any(ax.index[1] == fig.ncols - 1 for ax in group):
                r["nglPanelRight"] = 1.0 - GROUP_BAR_SPACE
            else:
                r["nglPanelXWhiteSpacePercent"] = GROUP_BAR_GAP_PERCENT
        else:
            if any(ax.index[0] == fig.nrows - 1 for ax in group):
                r["nglPanelBottom"] = GROUP_BAR_SPACE
            if any(ax.index[0] < fig.nrows - 1 for ax in group):
                r["nglPanelYWhiteSpacePercent"] = GROUP_BAR_GAP_PERCENT
    return r


def draw_title(wks, fig) -> None:
    """Figure title centred above the panels (txString in Ngl.panel draws nothing)."""
    if not fig.title:
        return
    opts = fig.style.options("strings")
    res = {"txFontHeightF": 1.5 * float(opts.get("font_height", 0.02)), "txJust": "CenterCenter"}
    font = fig.style.options("font").get("name")
    if font:
        res["txFont"] = font
    Ngl.text_ndc(wks, fig.title, 0.5, (1.0 + TITLE_TOP) / 2, to_resources(res))


def do_panel(wks, fig, plots: list) -> None:
    res = merge_resources(style_res=fig.style.res("panel"), keyword_res=panel_keyword_res(fig),
                          user_res=fig.panel_res,
                          locked={"nglFrame": False, "nglPanelSave": True})
    fig.panel_resolved = dict(res)
    Ngl.panel(wks, plots, [fig.nrows, fig.ncols], to_resources(res))


def record_geometry(fig) -> None:
    """Store final NDC geometry on each panel (PyNGL ids are invalid after destroy).

    ``panel.frame`` = (x, y_top, width, height) of the plot frame;
    ``panel.bbox`` = (top, bottom, left, right) including labels and annotations;
    ``panel.string_boxes[side]`` = (x, y_top, width, height) of each panel string.
    """
    for ax in fig.panels:
        if ax.base is None or ax.ngl_plot is None:
            continue
        p = ax.ngl_plot
        ax.frame = tuple(float(Ngl.get_float(p, k))
                         for k in ("vpXF", "vpYF", "vpWidthF", "vpHeightF"))
        ax.bbox = tuple(float(v) for v in Ngl.get_bounding_box(p))
        ax.string_boxes = {
            side: tuple(float(Ngl.get_float(t, k))
                        for k in ("vpXF", "vpYF", "vpWidthF", "vpHeightF"))
            for side, t in ax.string_ids.items()}
