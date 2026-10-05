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
        if spec.orientation == "vertical":   # the bar sits right of the group's last column
            if max(ax.index[1] for ax in group) == fig.ncols - 1:
                r["nglPanelRight"] = 1.0 - GROUP_BAR_SPACE
            else:
                r["nglPanelXWhiteSpacePercent"] = GROUP_BAR_GAP_PERCENT
        elif max(ax.index[0] for ax in group) == fig.nrows - 1:   # bar below the last row
            r["nglPanelBottom"] = GROUP_BAR_SPACE
        else:                                 # bar between rows
            r["nglPanelYWhiteSpacePercent"] = GROUP_BAR_GAP_PERCENT
    return r


TITLE_GAP = 0.01   # NDC space between the top of the panels and the title


def draw_title(wks, fig) -> None:
    """Figure title centred just above the panels (txString in Ngl.panel draws nothing).

    Uses the geometry from record_geometry, so a 1-row layout gets its title next to the
    panels and not at the top of the page.
    """
    fig.title_resolved = None
    if not fig.title:
        return
    opts = fig.style.options("strings")
    height = 1.5 * float(opts.get("font_height", 0.02))
    res = {"txFontHeightF": height, "txJust": "CenterCenter"}
    font = fig.style.options("font").get("name")
    if font:
        res["txFont"] = font
    tops = [ax.bbox[0] for ax in fig.panels if ax.bbox is not None]
    y = max(tops) + TITLE_GAP + height / 2 if tops else (1.0 + TITLE_TOP) / 2
    y = min(y, 1.0 - height / 2)
    Ngl.text_ndc(wks, fig.title, 0.5, y, to_resources(res))
    fig.title_resolved = {**res, "y": float(y)}


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
