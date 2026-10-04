"""Open and close PyNGL workstations."""

from __future__ import annotations

from pathlib import Path

import Ngl

from ..style import merge_resources
from .util import to_resources


def output_stem(output: Path) -> str:
    """Name passed to Ngl.open_wks (PyNGL adds the extension itself)."""
    return str(output.with_suffix(""))


def produced_file(output: Path, fmt: str) -> Path:
    """The file PyNGL writes for ``output`` (lowercase extension)."""
    return output.with_suffix("." + fmt)


def open_workstation(fig):
    keyword = {}
    if fig.format == "png" and fig.width:
        keyword.update(wkWidth=int(fig.width), wkHeight=int(fig.width))
    if fig.format in ("pdf", "ps", "eps") and fig.size:
        keyword.update(wkPaperWidthF=float(fig.size[0]), wkPaperHeightF=float(fig.size[1]))
    res = merge_resources(style_res=fig.style.res("workstation"), keyword_res=keyword,
                          user_res={}, locked={})
    return Ngl.open_wks(fig.format, output_stem(fig.output), to_resources(res))
