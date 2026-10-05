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


# Deferred minor 7: Ngl.panel shrinks every plot, and with it the text attached to the plot.
# xngl font heights are fractions of the page (like tags, shared colour bars and the title).
@pytest.mark.parametrize("layout", [(1, 1), (2, 2), (1, 4)])
def test_text_heights_are_page_units(make_da, outdir, layout):
    f = xn.Figure(*layout, output=outdir / f"th{layout[0]}x{layout[1]}.png", style="paper")
    for ax in f.panels:
        ax.contour_map(make_da(), left="PD-PI", right="R")
        ax.set_ticks(lon=10, lat=10)
    f.save()
    want_s = f.style.options("strings")["font_height"]
    want_t = f.style.options("ticks")["label_font_height"]
    for ax in f.panels:
        h = ax.text_heights
        assert h["left"] == pytest.approx(want_s, rel=0.03)
        assert h["right"] == pytest.approx(want_s, rel=0.03)
        assert h["lon"] == pytest.approx(want_t, rel=0.03)
        assert h["lat"] == pytest.approx(want_t, rel=0.03)


def test_wide_layout_text_not_smaller_than_tags(make_da, outdir):
    # README quick start shape: style="paper", ncols=4
    f = xn.Figure(ncols=4, output=outdir / "wide.png", width=3000, style="paper", tags="a)")
    for ax in f.panels:
        ax.contour_map(make_da(), left="PD-PI")
        ax.set_ticks(lon=10, lat=10)
    f.save()
    tag = f.panel_resolved["nglPanelFigureStringsFontHeightF"]
    assert all(ax.text_heights["left"] >= 0.75 * tag for ax in f.panels)


def test_text_too_large_for_layout_warns(make_da, outdir):
    f = xn.Figure(ncols=4, output=outdir / "toolong.png", style={"strings": {"font_height": 0.03}})
    for ax in f.panels:
        ax.contour_map(make_da(), left="A_VERY_LONG_EXPERIMENT_NAME")
    with pytest.warns(XnglWarning, match="do not fit"):
        f.save()
    h = f[0, 0].text_heights["left"]
    # smaller text, but not smaller than without the fit (x0.26 in 1x4), and a sensible plot
    assert 0.25 * 0.03 < h < 0.03 and f[0, 0].frame[2] > 0.1


def test_raw_tick_font_resource_keeps_pyngl_meaning(make_da, outdir):
    # a raw resource is passed as is: Ngl.panel scales it with the plot
    f = xn.Figure(ncols=4, output=outdir / "rawtick.png",
                  style={"ticks": {"res": {"tmXBLabelFontHeightF": 0.03,
                                             "tmYLLabelFontHeightF": 0.03}}})
    for ax in f.panels:
        ax.contour_map(make_da())
        ax.set_ticks(lon=10, lat=10)
    f.save()
    # (PyNGL's blank plot keeps XB and YL label heights equal: tmEqualizeXYSizes)
    assert f[0, 0].text_heights["lon"] < 0.015 and f[0, 0].text_heights["lat"] < 0.015


def test_fit_passes_add_no_tags(make_da, outdir, monkeypatch):
    # Ngl.panel attaches figure strings to the plots, so each extra layout pass would add
    # another tag (a double border on the tag box)
    import Ngl

    from xngl.render import layout
    calls, real_panel = [], Ngl.panel

    def spy(wks, plots, dims, res):
        calls.append((getattr(res, "nglDraw", True), hasattr(res, "nglPanelFigureStrings")))
        return real_panel(wks, plots, dims, res)

    monkeypatch.setattr(layout.Ngl, "panel", spy)
    f = xn.Figure(ncols=2, output=outdir / "tagsonce.png", tags="a)")
    for ax in f.panels:
        ax.contour_map(make_da(), left="L")
    f.save()
    assert len(calls) > 1 and calls[-1] == (True, True)
    assert all(not tags for _draw, tags in calls[:-1])
