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


def panel_keyword_res(fig) -> dict:
    """Panel resources from figure options (extended by later steps)."""
    return {}


def do_panel(wks, fig, plots: list) -> None:
    res = merge_resources(style_res=fig.style.res("panel"), keyword_res=panel_keyword_res(fig),
                          user_res=fig.panel_res,
                          locked={"nglFrame": False, "nglPanelSave": True})
    fig.panel_resolved = dict(res)
    Ngl.panel(wks, plots, [fig.nrows, fig.ncols], to_resources(res))
