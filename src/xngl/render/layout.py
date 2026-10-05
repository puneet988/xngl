"""Panel layout: placeholders for empty panels and the Ngl.panel call."""

from __future__ import annotations

import warnings

import Ngl

from ..errors import XnglWarning
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


def panel_resources(fig) -> dict:
    return merge_resources(style_res=fig.style.res("panel"), keyword_res=panel_keyword_res(fig),
                           user_res=fig.panel_res,
                           locked={"nglFrame": False, "nglPanelSave": True})


TEXT_FIT_PASSES = 4
TEXT_FIT_TOLERANCE = 0.005   # relative
MIN_FRAME_RATIO = 0.6        # the fit never makes a plot narrower than this x its width without it


def _text_targets(fig) -> list[tuple]:
    """(PyNGL id, resource, page height) for text sized by an xngl font-height option.

    Raw resources (ticks.res) keep their PyNGL meaning and are not changed.
    """
    strings_h = float(fig.style.options("strings").get("font_height", 0.02))
    ticks_h = float(fig.style.options("ticks").get("label_font_height", 0.016))
    tick_keys = ("tmXBLabelFontHeightF", "tmYLLabelFontHeightF")
    # the blank plot keeps XB and YL equal (tmEqualizeXYSizes), so one raw key means both
    raw_ticks = any(k in fig.style.res("ticks") for k in tick_keys)
    out = []
    for ax in fig.panels:
        out += [(t, "txFontHeightF", strings_h) for t in ax.string_ids.values()]
        if ax.tick_id is not None and not raw_ticks:
            out += [(ax.tick_id, k, ticks_h) for k in tick_keys]
    return out


def fit_text(wks, fig, plots: list) -> None:
    """Make panel strings and tick labels the requested height on the page.

    Ngl.panel shrinks each plot and the text attached to it (by about 4 in a 1x4 layout).
    A layout pass with nglDraw=False resizes the plots without drawing.

    Let u be the text height divided by the page height, relative to the plot width W
    (text = h * u * W). Larger text makes the panel boxes larger, so Ngl.panel makes W
    smaller; 1/W is close to linear in u. We need u * W = 1. A secant step on
    1/W = a + b*u gives u = a / (1 - b), which needs about 2 passes.
    """
    targets = _text_targets(fig)
    ref = next((p for p, ax in zip(plots, fig.panels, strict=True) if ax.base is not None), None)
    if not targets or ref is None:
        return
    # Ngl.panel attaches tags (and a panel label bar) to the plots on every call, so the
    # layout passes leave them out; they sit inside the plots and do not change the layout
    res = {k: v for k, v in panel_resources(fig).items()
           if not k.startswith("nglPanelFigureStrings")}
    res = to_resources({**res, "nglDraw": False, "nglPanelLabelBar": False})
    dims = [fig.nrows, fig.ncols]

    def layout_pass(u):
        if u is not None:
            w = Ngl.get_float(ref, "vpWidthF")
            for obj, key, h in targets:
                Ngl.set_values(obj, to_resources({key: h * u * w}))
        Ngl.panel(wks, plots, dims, res)
        return Ngl.get_float(ref, "vpWidthF")

    obj0, key0, h0 = targets[0]
    w0 = layout_pass(None)
    history = [(Ngl.get_float(obj0, key0) / (h0 * w0), 1.0 / w0)]   # (u, 1/W)
    u = 1.0 / w0
    for _ in range(TEXT_FIT_PASSES):
        w = layout_pass(u)
        history.append((u, 1.0 / w))
        if abs(u * w - 1.0) < TEXT_FIT_TOLERANCE and w >= MIN_FRAME_RATIO * w0:
            return
        (u0, i0), (u1, i1) = history[-2:]
        b = (i1 - i0) / (u1 - u0) if u1 != u0 else 0.0
        a = i1 - b * u1
        u = a / (1.0 - b) if b < 1.0 and a > 0 else None
        if u is None or w < MIN_FRAME_RATIO * w0:
            break
    # No stable size, or the plots would get too small: the text is too large for the
    # layout (e.g. a long string in a narrow panel). Use the text size that leaves the
    # plots at MIN_FRAME_RATIO of their width, from the same linear model.
    u = (1.0 / (MIN_FRAME_RATIO * w0) - a) / b if b > 0 else history[1][0]
    layout_pass(u)
    warnings.warn("panel strings and tick labels do not fit the panel layout at their "
                  "font_height (page fraction); they are drawn smaller. Reduce [strings] "
                  "font_height or [ticks] label_font_height, or use shorter strings",
                  XnglWarning, stacklevel=4)


def do_panel(wks, fig, plots: list) -> None:
    res = panel_resources(fig)
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
        ax.text_heights = {side: float(Ngl.get_float(t, "txFontHeightF"))
                           for side, t in ax.string_ids.items()}
        if ax.tick_id is not None:
            ax.text_heights["lon"] = float(Ngl.get_float(ax.tick_id, "tmXBLabelFontHeightF"))
            ax.text_heights["lat"] = float(Ngl.get_float(ax.tick_id, "tmYLLabelFontHeightF"))
