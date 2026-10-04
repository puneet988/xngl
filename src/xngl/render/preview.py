"""Colormap preview sheet: one labelled colour bar per colormap."""

from pathlib import Path

import Ngl

from ..colors.colormaps import to_colormap
from ..errors import RenderError, XnglError
from .util import to_resources

MAX_BOXES = 256  # PyNGL labelbar limit


def preview_colors(cm):
    """Colours to draw for ``cm``: resampled to at most MAX_BOXES."""
    return cm.rgba if len(cm) <= MAX_BOXES else cm.resample(MAX_BOXES).rgba


def show_colormaps(cmaps: list, output) -> Path:
    cms = [to_colormap(c) for c in cmaps]
    output = Path(output).expanduser().absolute()
    fmt = output.suffix.lower().lstrip(".")
    if fmt not in ("pdf", "png", "eps", "ps", "svg"):
        raise XnglError(f"show: output '{output}' needs a .pdf .png .eps .ps or .svg extension")
    n = len(cms)
    row = min(0.9 / max(n, 1), 0.12)
    wks = Ngl.open_wks(fmt, str(output.with_suffix("")))
    try:
        for i, cm in enumerate(cms):
            y = 0.95 - i * row
            colors = preview_colors(cm)
            res = {"vpWidthF": 0.8, "vpHeightF": row * 0.55, "lbFillColors": colors,
                   "lbMonoFillPattern": True, "lbOrientation": "Horizontal",
                   "lbLabelsOn": False, "lbPerimOn": False, "lbBoxLinesOn": False,
                   "lbTitleOn": True, "lbTitleString": f"{cm.name} ({len(cm)})",
                   "lbTitlePosition": "Top", "lbTitleFontHeightF": min(0.015, row * 0.2)}
            labels = [""] * len(colors)
            if Ngl.labelbar_ndc(wks, len(colors), labels, 0.1, y, to_resources(res)) is None:
                raise RenderError(f"show: could not draw colormap {cm.name}")
        Ngl.frame(wks)
    finally:
        Ngl.destroy(wks)
    produced = output.with_suffix("." + fmt)
    if produced != output:
        produced.replace(output)
    return output
