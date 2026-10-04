"""Colormaps, levels and colour bar settings (spec section 6)."""

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

__all__ = ["Colormap", "combine", "from_array", "from_colors", "get", "list", "register",
           "to_colormap"]
