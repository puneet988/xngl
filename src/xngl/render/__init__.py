"""Rendering: the only package of xngl that imports Ngl (spec section 8.1)."""


from pathlib import Path

import Ngl

from ..errors import RenderError, XnglError
from ..specs import VectorSpec
from . import annotations, layout, overlays, plots
from .colorbar import colorbar_modes, draw_colorbars
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


def _render_panel(wks, fig, ax, mode, where: _Where):
    where.panel = ax.index
    if ax.base is None:
        where.layer = "empty panel"
        return layout.placeholder(wks)
    where.layer = "contour_map"
    ticks_off = annotations.uses_xngl_ticks(ax, fig.style)
    plot = plots.build_contour(wks, ax.base, fig.style, mode, ticks_off=ticks_off)
    ax.ngl_plot = plot
    ax.attached = []
    for layer in ax.layers[1:]:
        if isinstance(layer, VectorSpec):
            where.layer = layer.name
            ax.attached.append(plots.build_vectors(wks, layer, fig.style, plot))
    where.layer = "overlays"
    overlays.add_overlays(wks, plot, ax, fig.style)
    where.layer = "tick labels"
    annotations.add_ticks(wks, plot, ax, fig, fig.style)
    where.layer = "strings"
    annotations.add_strings(wks, plot, ax, fig.style)
    where.layer = "add_custom"
    overlays.run_custom(wks, plot, ax)
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
        layout.record_geometry(fig)
        where.layer = "colour bars"
        draw_colorbars(wks, fig)
        where.layer = "title"
        layout.draw_title(wks, fig)
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
