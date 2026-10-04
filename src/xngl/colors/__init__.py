"""Colormaps, levels and colour bar settings (spec section 6)."""

import builtins

from .colorbar import ColorbarSpec
from .colormaps import (
    Colormap,
    combine,
    from_array,
    from_colors,
    get,
    list,
    register,
    to_colormap,
)
from .levels import nice_levels, symmetric_levels


def show(cmaps, output="colormaps.png"):
    """Draw a preview sheet of colormaps (names, Colormap objects or arrays). Needs PyNGL."""
    from ..render.preview import show_colormaps

    return show_colormaps(builtins.list(cmaps), output)


__all__ = [
    "ColorbarSpec",
    "Colormap",
    "combine",
    "from_array",
    "from_colors",
    "get",
    "list",
    "nice_levels",
    "register", "show",
    "symmetric_levels",
    "to_colormap",
]
