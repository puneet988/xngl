"""Colormaps, levels and colour bar settings (spec section 6)."""

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

__all__ = [
    "ColorbarSpec",
    "Colormap",
    "combine",
    "from_array",
    "from_colors",
    "get",
    "list",
    "nice_levels",
    "register",
    "symmetric_levels",
    "to_colormap",
]
