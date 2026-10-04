"""Layer specs: plain records of what to draw. ``xngl.render`` turns them into PyNGL calls."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .colors.colormaps import Colormap
from .coords import Field
from .errors import XnglError


@dataclass(eq=False)
class Layer:
    """Base class of all layers. ``res`` can be changed until ``fig.save()``."""

    name: str = field(init=False, default="layer")
    res: dict = field(default_factory=dict, kw_only=True)
    resolved: dict | None = field(default=None, init=False, kw_only=True)

    def resolved_res(self) -> dict:
        """The final resources sent to PyNGL (available after ``fig.save()``)."""
        if self.resolved is None:
            raise XnglError(f"{self.name}: not rendered yet; call fig.save()")
        return dict(self.resolved)


@dataclass(eq=False)
class ContourSpec(Layer):
    field: Field
    levels: np.ndarray | None = None
    cmap: Colormap | None = None
    lat: tuple | None = None
    lon: tuple | None = None
    fill: str | None = None
    colorbar: bool | dict = False
    projection: str = "CylindricalEquidistant"

    def __post_init__(self):
        self.name = "contour_map"


@dataclass(eq=False)
class VectorSpec(Layer):
    u: Field
    v: Field
    stride: int | None = None
    ref_magnitude: float | None = None
    ref_label: str | None = None
    color: str | None = None
    thickness: float | None = None

    def __post_init__(self):
        self.name = "vectors"


@dataclass(eq=False)
class ShapefileSpec(Layer):
    path: Path
    select: dict | None = None
    color: str | None = None
    thickness: float | None = None
    dash: int | None = None

    def __post_init__(self):
        self.name = "add_shapefile"


@dataclass(eq=False)
class BoxSpec(Layer):
    lat: tuple
    lon: tuple
    color: str | None = None
    thickness: float | None = None

    def __post_init__(self):
        self.name = "add_box"


@dataclass(eq=False)
class StippleSpec(Layer):
    mask: Field
    marker: str | int | None = None
    size: float | None = None
    color: str | None = None
    stride: int = 1

    def __post_init__(self):
        self.name = "stipple"


@dataclass(eq=False)
class CustomSpec(Layer):
    func: Callable

    def __post_init__(self):
        self.name = "add_custom"


@dataclass
class TicksSpec:
    lon: float | list | None = None
    lat: float | list | None = None


@dataclass
class StringsSpec:
    left: str | None = None
    center: str | None = None
    right: str | None = None
