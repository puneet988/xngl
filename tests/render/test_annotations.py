import pytest
from helpers import white_fraction

import xngl as xn
from xngl.errors import XnglWarning
from xngl.render.annotations import tick_labels

pytestmark = pytest.mark.render


def test_tick_label_text():
    assert tick_labels([0, 60, 180, 200, -160], "lon") == ["0", "60E", "180", "160W", "160W"]
    assert tick_labels([-10, 0, 10], "lat") == ["10S", "0", "10N"]
    assert tick_labels([2.5, 7.5], "lat") == ["2.5N", "7.5N"]


@pytest.mark.parametrize("layout", [(2, 2), (1, 4)])
def test_strings_follow_panels(make_da, outdir, layout):
    png = outdir / f"s{layout[0]}x{layout[1]}.png"
    f = xn.Figure(*layout, output=png)
    for ax in f.panels:
        ax.contour_map(make_da(), left="L", right="R")
    f.save()
    tops = set()
    for ax in f.panels:
        x, y, w, _h = ax.frame
        assert 0 < w < 1 and 0 < y <= 1                              # real geometry was recorded
        lx, ly, _lw, lh = ax.string_boxes["left"]
        rx, _ry, rw, _rh = ax.string_boxes["right"]
        assert abs(lx - x) < 0.01 and ly - lh >= y - 0.002          # above the top-left corner
        assert ly - lh < y + 0.05                                    # close to the frame
        assert abs((rx + rw) - (x + w)) < 0.01                       # right-aligned to the frame
        tops.add(round(y, 3))
    assert len(tops) == layout[0]                                    # strings moved with each row
    # a string drawn by mistake at NDC (0, 0) would show in the bottom 1% at the left edge
    assert white_fraction(png, 0.0, 0.03, 0.99, 1.0) == 1.0


def test_string_style(make_da, outdir):
    f = xn.Figure(output=outdir / "st.png", style={"strings": {"font_height": 0.03, "gap": 0.05},
                                                     "font": {"name": "helvetica-bold"}})
    ax = f.panels[0]
    ax.contour_map(make_da(), center="Title")
    f.save()
    r = ax.strings_resolved["center"]
    assert r["txFontHeightF"] == 0.03 and r["txFont"] == "helvetica-bold"
    assert r["amOrthogonalPosF"] == pytest.approx(-0.55) and r["amJust"] == "BottomCenter"


def test_ticks_outer_only(make_da, outdir):
    f = xn.Figure(2, 2, output=outdir / "t.png", style={"ticks": {"outer_only": True}})
    for ax in f.panels:
        ax.contour_map(make_da())
        ax.set_ticks(lon=10, lat=5)
    f.save()
    t = {ax.index: ax.ticks_resolved for ax in f.panels}
    assert t[(0, 0)]["tmYLLabelsOn"] and not t[(0, 0)]["tmXBLabelsOn"]
    assert not t[(0, 1)]["tmYLLabelsOn"] and not t[(0, 1)]["tmXBLabelsOn"]
    assert t[(1, 0)]["tmYLLabelsOn"] and t[(1, 0)]["tmXBLabelsOn"]
    assert t[(1, 1)]["tmXBLabels"] == ["60E", "70E", "80E", "90E", "100E"]
    assert t[(1, 1)]["tmYLLabels"][:3] == ["0", "5N", "10N"]
    assert f[0, 0].base.resolved_res()["pmTickMarkDisplayMode"] == "Never"


def test_ticks_from_style_and_outward(make_da, outdir):
    f = xn.Figure(output=outdir / "t2.png",
                  style={"ticks": {"lon_spacing": 20, "lat_spacing": 20, "outward": True,
                                   "label_font_height": 0.02}})
    ax = f.panels[0]
    ax.contour_map(make_da())
    f.save()
    r = ax.ticks_resolved
    assert list(r["tmXBValues"]) == [60, 80, 100] and r["nglPointTickmarksOutward"] is True
    assert r["tmXBLabelFontHeightF"] == 0.02 and r["tmYLLabelFontHeightF"] == 0.02


def test_no_ticks_requested_keeps_pyngl_ticks(make_da, outdir):
    f = xn.Figure(output=outdir / "t3.png")
    ax = f.panels[0]
    ax.contour_map(make_da())
    f.save()
    assert ax.ticks_resolved is None and "pmTickMarkDisplayMode" not in ax.base.resolved_res()


def test_ticks_other_projection_warns(make_da, outdir):
    f = xn.Figure(output=outdir / "m.png")
    ax = f.panels[0]
    ax.contour_map(make_da(), projection="Mercator")
    ax.set_ticks(lon=10)
    with pytest.warns(XnglWarning, match="CylindricalEquidistant"):
        f.save()
    assert ax.ticks_resolved is None


def test_render_package_imports_annotations_module_in_fresh_process():
    import subprocess
    import sys

    code = ("import types, xngl.render as r; "
            "assert isinstance(r.annotations, types.ModuleType), type(r.annotations)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=False)
    assert out.returncode == 0, out.stderr[-500:]
