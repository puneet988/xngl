import numpy as np
import pytest

import xngl as xn
from xngl.colors import ColorbarSpec
from xngl.errors import XnglError
from xngl.figure import Figure, tag_strings

LEV = [0, 1, 2]


def test_exports():
    assert xn.Figure is Figure and hasattr(xn, "colors") and hasattr(xn, "style")


def test_output_variants(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = Figure(output="out.PNG")
    assert f.format == "png" and f.output == tmp_path / "out.PNG"
    for bad in ("out", "out.jpg"):
        with pytest.raises(XnglError, match="extension"):
            Figure(output=bad)


def test_grid_access():
    f = Figure(nrows=2, ncols=4)
    assert len(f.panels) == 8 and f[1, 2] is f.panels[6] and f.panels[6].index == (1, 2)
    assert f.row(0) == f.panels[:4] and f.col(3) == [f.panels[3], f.panels[7]]
    with pytest.raises(XnglError, match="out of range"):
        f[2, 0]


def test_style_loaded():
    assert Figure(style={"strings": {"gap": 0.3}}).style.options("strings")["gap"] == 0.3


def test_tags():
    assert tag_strings("a)", 3) == ["a)", "b)", "c)"]
    assert tag_strings("(a)", 2) == ["(a)", "(b)"]
    assert tag_strings("A", 2) == ["A", "B"]
    assert tag_strings(["x", "y"], 2) == ["x", "y"]
    assert tag_strings(None, 2) is None


def test_colorbar_request(make_da):
    f = Figure(ncols=2)
    cb = f.colorbar(panels=f.row(0), label="T", end_caps="triangles")
    assert isinstance(cb, ColorbarSpec) and cb.end_caps == "triangles" and cb.label == "T"
    assert f.colorbars[0][0] == f.row(0)
    assert f.colorbar().label is None and f.colorbars[1][0] == f.panels


def test_colorbar_style_defaults():
    f = Figure(style={"colorbar": {"end_caps": "triangles", "label_stride": 2}})
    cb = f.colorbar(label="x", label_stride=3)
    assert cb.end_caps == "triangles" and cb.label_stride == 3


def _two(make_da, tmp_path, lev0=LEV, lev1=LEV, cmap1="BlueYellowRed"):
    f = Figure(ncols=2, output=tmp_path / "a.png")
    f[0, 0].contour_map(make_da() + 1, levels=lev0, cmap="BlueYellowRed")
    f[0, 1].contour_map(make_da() + 1, levels=lev1, cmap=cmap1)
    return f


def test_preflight_ok(make_da, tmp_path):
    f = _two(make_da, tmp_path)
    f.colorbar()
    f.preflight()


def test_preflight_shared_levels_differ(make_da, tmp_path):
    f = _two(make_da, tmp_path, lev1=[0, 2, 4])
    f.colorbar()
    with pytest.raises(XnglError, match=r"panels \(0, 0\) and \(0, 1\) use different levels"):
        f.preflight()


def test_preflight_shared_cmap_differ(make_da, tmp_path):
    f = _two(make_da, tmp_path, cmap1="cb_BrBG")
    f.colorbar()
    with pytest.raises(XnglError, match="different colormaps"):
        f.preflight()


def test_preflight_levels_none(make_da, tmp_path):
    f = Figure(ncols=2, output=tmp_path / "a.png")
    for ax in f.panels:
        ax.contour_map(make_da())
    f.colorbar()
    with pytest.raises(XnglError, match="explicit levels"):
        f.preflight()


def test_preflight_panel_in_two_groups(make_da, tmp_path):
    f = _two(make_da, tmp_path)
    f.colorbar(panels=f.panels)
    f.colorbar(panels=[f[0, 1]])
    with pytest.raises(XnglError, match=r"panel \(0, 1\) is in two colour bar groups"):
        f.preflight()


def test_preflight_own_and_group(make_da, tmp_path):
    f = Figure(ncols=2, output=tmp_path / "a.png")
    f[0, 0].contour_map(make_da() + 1, levels=LEV, colorbar=True)
    f[0, 1].contour_map(make_da() + 1, levels=LEV)
    f.colorbar()
    with pytest.raises(XnglError, match=r"panel \(0, 0\) has its own colour bar"):
        f.preflight()


def test_preflight_group_panel_without_contour(make_da, tmp_path):
    f = Figure(ncols=2, output=tmp_path / "a.png")
    f[0, 0].contour_map(make_da() + 1, levels=LEV)
    f.colorbar()
    with pytest.raises(XnglError, match=r"panel \(0, 1\) has no contour_map"):
        f.preflight()


def test_preflight_output_folder(make_da, tmp_path):
    f = Figure(output=tmp_path / "missing" / "a.png")
    f.panels[0].contour_map(make_da())
    with pytest.raises(XnglError, match="output folder"):
        f.preflight()


def test_colorbar_levels_as_arrays(make_da, tmp_path):
    f = _two(make_da, tmp_path, lev0=np.array(LEV, dtype=float), lev1=LEV)
    f.colorbar()
    f.preflight()
