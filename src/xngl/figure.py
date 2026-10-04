"""Figure: a grid of panels, colour bar requests, pre-flight checks and save()."""

from __future__ import annotations

import os
import string
from pathlib import Path

import numpy as np

from .colors.colorbar import ColorbarSpec
from .errors import XnglError
from .panel import Panel
from .style import load_style

FORMATS = ("pdf", "png", "eps", "ps", "svg")


def tag_strings(tags, n: int) -> list[str] | None:
    """Panel tags: ``"a)"`` -> a) b) ..., ``"(a)"`` -> (a) (b) ..., ``"A"`` -> A B ..."""
    if tags is None:
        return None
    if isinstance(tags, (list, tuple)):
        return [str(t) for t in tags][:n]
    for letters in (string.ascii_lowercase, string.ascii_uppercase):
        for i, ch in enumerate(tags):
            if ch == letters[0]:
                if n > len(letters):
                    raise XnglError(f"tags: at most {len(letters)} panels can be tagged")
                return [tags[:i] + letters[k] + tags[i + 1:] for k in range(n)]
    raise XnglError(f"tags={tags!r}: use a pattern with 'a' or 'A' (e.g. 'a)'), or a list")


class Figure:
    """A figure with ``nrows`` x ``ncols`` panels. Nothing is drawn until :meth:`save`."""

    def __init__(self, nrows: int = 1, ncols: int = 1, output="figure.pdf", size=None,
                 width=None, style="default", tags=None, title=None, panel_res=None):
        if nrows < 1 or ncols < 1:
            raise XnglError(f"Figure: nrows and ncols must be >= 1, got {nrows}, {ncols}")
        self.nrows, self.ncols = int(nrows), int(ncols)
        self.output = Path(output).expanduser().absolute()
        ext = self.output.suffix.lower().lstrip(".")
        if ext not in FORMATS:
            raise XnglError(f"Figure: output '{output}' needs an extension from "
                            f"{', '.join('.' + f for f in FORMATS)}")
        self.format = ext
        self.size = size
        self.width = width
        self.style = load_style(style)
        self.tags = tags
        self.title = title
        self.panel_res = dict(panel_res or {})
        self.panels = [Panel((r, c)) for r in range(self.nrows) for c in range(self.ncols)]
        self.colorbars: list[tuple[list[Panel], ColorbarSpec]] = []
        self.wks = None
        self.panel_resolved: dict | None = None
        self.workstation_resolved: dict | None = None

    def __getitem__(self, idx) -> Panel:
        r, c = idx
        if not (0 <= r < self.nrows and 0 <= c < self.ncols):
            raise XnglError(f"Figure: panel ({r}, {c}) is out of range for a "
                            f"{self.nrows}x{self.ncols} figure")
        return self.panels[r * self.ncols + c]

    def row(self, i: int) -> list[Panel]:
        return [self[i, c] for c in range(self.ncols)]

    def col(self, j: int) -> list[Panel]:
        return [self[r, j] for r in range(self.nrows)]

    def colorbar(self, panels=None, label=None, **options) -> ColorbarSpec:
        """Request one colour bar for ``panels`` (default: all panels)."""
        merged = {**self.style.options("colorbar"), **options}
        if "res" in options or self.style.res("colorbar"):
            merged["res"] = {**self.style.res("colorbar"), **options.get("res", {})}
        spec = ColorbarSpec.from_options(merged)
        if label is not None:
            spec.label = label
        group = list(panels) if panels is not None else list(self.panels)
        self.colorbars.append((group, spec))
        return spec

    def preflight(self) -> None:
        """Checks that need the whole figure. Raises XnglError before anything is drawn."""
        seen: dict[tuple, int] = {}
        for gi, (group, _spec) in enumerate(self.colorbars):
            for ax in group:
                if ax.index in seen and seen[ax.index] != gi:
                    raise XnglError(f"colorbar: panel {ax.index} is in two colour bar groups")
                seen[ax.index] = gi
                if ax.base is None:
                    raise XnglError(f"colorbar: panel {ax.index} has no contour_map")
                if ax.base.colorbar:
                    raise XnglError(f"colorbar: panel {ax.index} has its own colour bar "
                                    "(colorbar=True) and is also in a shared colour bar")
                if ax.base.levels is None:
                    raise XnglError(f"colorbar: panel {ax.index} needs explicit levels "
                                    "to share a colour bar")
            first = group[0]
            for ax in group[1:]:
                a, b = first.base, ax.base
                if not np.array_equal(a.levels, b.levels):
                    raise XnglError(f"colorbar: panels {first.index} and {ax.index} use "
                                    "different levels. Use one colorbar per panel or the "
                                    "same levels.")
                rgba_a = None if a.cmap is None else a.cmap.rgba
                rgba_b = None if b.cmap is None else b.cmap.rgba
                if (rgba_a is None) != (rgba_b is None) or (
                        rgba_a is not None and not np.array_equal(rgba_a, rgba_b)):
                    raise XnglError(f"colorbar: panels {first.index} and {ax.index} use "
                                    "different colormaps")
        folder = self.output.parent
        if not folder.is_dir() or not os.access(folder, os.W_OK):
            raise XnglError(f"save: output folder does not exist or is not writable: {folder}")

    def save(self) -> Path:
        """Check, render and write the figure. Returns the output path."""
        self.preflight()
        from .render import render_figure  # PyNGL is imported only when drawing

        return render_figure(self)
