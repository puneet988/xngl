"""Acceptance criterion 2: every resource and Ngl call of the user's scripts is reachable."""

import inspect
import tomllib
from pathlib import Path

import numpy as np
import pytest

import xngl as xn
from xngl.colors import ColorbarSpec
from xngl.panel import Panel
from xngl.style import OPTIONS

INVENTORY = tomllib.loads((Path(__file__).parent / "control_inventory.toml").read_text())
SRC = Path(xn.__file__).parent
LEV = np.linspace(-1, 1, 11)
ENTRIES = INVENTORY["resource"] + INVENTORY["call"]


def by_level(level):
    return [e for e in ENTRIES if e["level"] == level]


def test_inventory_counts():
    assert len(INVENTORY["resource"]) == 125 and len(INVENTORY["call"]) == 15
    assert {e["level"] for e in ENTRIES} == {"keyword", "style", "res", "hook", "internal"}


@pytest.mark.parametrize("entry", by_level("keyword"), ids=lambda e: e["name"])
def test_keyword_exists(entry):
    owner, param = entry["option"].split(":")
    if owner == "ColorbarSpec":
        assert param in ColorbarSpec.option_names()
        return
    obj = {"Figure": xn.Figure}.get(owner) or getattr(Panel, owner.split(".")[1])
    assert param in inspect.signature(obj).parameters


@pytest.mark.parametrize("entry", by_level("style"), ids=lambda e: e["name"])
def test_style_option_exists(entry):
    part, option = entry["option"].split(".")
    assert option in OPTIONS[part]


@pytest.mark.parametrize("entry", by_level("internal"), ids=lambda e: e["name"])
def test_internal_is_set_by_xngl(entry):
    text = (SRC / entry["module"]).read_text()
    name = entry.get("replaced_by") or entry["name"].removeprefix("Ngl.")
    assert name in text, f"{name} not found in {entry['module']}"


@pytest.mark.render
@pytest.mark.parametrize("entry", by_level("res"), ids=lambda e: e["name"])
def test_res_reaches_pyngl(entry, make_da, ngl_data, tmp_path):
    name, value, where = entry["name"], entry["value"], entry["where"]
    style, panel_res, ext = None, None, "png"
    if where == "ticks":
        style = {"ticks": {"res": {name: value}}}
    if where == "workstation":
        style, ext = {"workstation": {"res": {name: value}}}, "pdf"
    if where == "panel":
        panel_res = {name: value}
    f = xn.Figure(output=tmp_path / f"r.{ext}", style=style, panel_res=panel_res)
    ax = f.panels[0]
    layer = ax.contour_map(make_da(), levels=LEV, res={name: value} if where == "contour" else None)
    if where == "vectors":
        layer = ax.vectors(make_da(), make_da(), res={name: value})
    elif where == "shapefile":
        layer = ax.add_shapefile(ngl_data / "shp/states.shp", res={name: value})
    elif where == "colorbar":
        cb = f.colorbar(res={name: value})
    elif where == "ticks":
        ax.set_ticks(lon=10, lat=10)
    f.save()
    resolved = {"colorbar": lambda: cb.resolved, "ticks": lambda: ax.ticks_resolved,
                "panel": lambda: f.panel_resolved,
                "workstation": lambda: f.workstation_resolved}.get(where, layer.resolved_res)()
    assert resolved[name] == value


@pytest.mark.render
def test_hook_can_call_any_ngl_function(make_da, tmp_path):
    import Ngl

    drawn = []

    def free_text(wks, plot, panel):
        txres = Ngl.Resources()
        txres.txFontHeightF = 0.02
        drawn.append(Ngl.add_text(wks, plot, "hook", 80.0, 20.0, txres))

    f = xn.Figure(output=tmp_path / "hook.png")
    f.panels[0].contour_map(make_da())
    f.panels[0].add_custom(free_text)
    f.save()
    assert drawn and drawn[0] is not None
