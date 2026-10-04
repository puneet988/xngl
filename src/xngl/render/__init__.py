"""Rendering: the only package of xngl that imports Ngl (spec section 8.1)."""

from __future__ import annotations

from pathlib import Path

import Ngl

from ..errors import RenderError, XnglError
from ..specs import VectorSpec
from . import layout, plots
from .workstation import open_workstation, produced_file


class _Where:
    """What the renderer is doing, for error messages."""

    def __init__(self):
        self.panel = None
        self.layer = "workstation"

    def __str__(self) -> str:
        if self.panel is None:
            return self.layer
        return f"panel {self.panel}, layer '{self.layer}'"


def colorbar_modes(fig) -> dict[tuple[int, int], str]:
    """'own', 'shared' or 'none' for each panel."""
    shared = {ax.index for group, _ in fig.colorbars for ax in group}
    modes = {}
    for ax in fig.panels:
        if ax.base is not None and ax.base.colorbar:
            modes[ax.index] = "own"
        elif ax.index in shared:
            modes[ax.index] = "shared"
        else:
            modes[ax.index] = "none"
    return modes


def _render_panel(wks, fig, ax, mode, where: _Where):
    where.panel = ax.index
    if ax.base is None:
        where.layer = "empty panel"
        return layout.placeholder(wks)
    where.layer = "contour_map"
    plot = plots.build_contour(wks, ax.base, fig.style, mode)
    for layer in ax.layers[1:]:
        where.layer = layer.name
        if isinstance(layer, VectorSpec):
            plots.build_vectors(wks, layer, fig.style, plot)
        else:
            raise RenderError(f"layer type {layer.name} is not supported yet")
    return plot


def render_figure(fig) -> Path:
    """Draw ``fig`` and write its output file. Returns the output path."""
    modes = colorbar_modes(fig)
    target = produced_file(fig.output, fig.format)
    where = _Where()
    wks = open_workstation(fig)
    fig.wks = wks
    error = None
    try:
        plot_list = []
        for ax in fig.panels:
            plot = _render_panel(wks, fig, ax, modes[ax.index], where)
            ax.ngl_plot = plot
            plot_list.append(plot)
        where.panel, where.layer = None, "panel layout"
        layout.do_panel(wks, fig, plot_list)
        Ngl.frame(wks)
    except Exception as exc:  # noqa: BLE001 - re-raised below with context
        error = exc
    finally:
        Ngl.destroy(wks)
    if error is not None:
        for p in {target, fig.output}:
            p.unlink(missing_ok=True)
        if isinstance(error, XnglError) and not isinstance(error, RenderError):
            raise error
        raise RenderError(f"{where}: {error}") from error
    if target != fig.output:
        target.replace(fig.output)
    return fig.output
