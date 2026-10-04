import numpy as np
import pytest
from helpers import white_fraction

import xngl as xn

pytestmark = pytest.mark.render
LEV = np.linspace(-1, 1, 11)


def test_modes(make_da):
    from xngl.render.colorbar import colorbar_modes

    f = xn.Figure(ncols=3)
    f[0, 0].contour_map(make_da(), levels=LEV, colorbar=True)
    f[0, 1].contour_map(make_da(), levels=LEV)
    f.colorbar(panels=[f[0, 1]])
    assert colorbar_modes(f) == {(0, 0): "own", (0, 1): "shared", (0, 2): "none"}


def test_own_colorbars(make_da, outdir):
    f = xn.Figure(ncols=2, output=outdir / "own.png")
    c = [ax.contour_map(make_da(), colorbar=True) for ax in f.panels]
    f.save()
    assert all(x.resolved_res()["lbLabelBarOn"] for x in c)
    assert not f.panel_resolved.get("nglPanelLabelBar", False)


def test_one_colorbar_all_panels(make_da, outdir):
    # drawn by xngl (labelbar_ndc) below all panels, not by nglPanelLabelBar, which overlaps
    # the xngl tick labels and scales fonts too large
    f = xn.Figure(ncols=3, output=outdir / "all.png", tags="a)")
    cs = []
    for ax in f.panels:
        cs.append(ax.contour_map(make_da(), levels=LEV, cmap="BlueYellowRed"))
        ax.set_ticks(lon=10, lat=10)
    cb = f.colorbar(label="T", end_caps="triangles", label_font_height=0.015,
                    title_font_height=0.02)
    f.save()
    p = f.panel_resolved
    assert "nglPanelLabelBar" not in p and not any(k.startswith("lb") for k in p)
    assert p["nglPanelFigureStrings"] == ["a)", "b)", "c)"]
    assert p["nglPanelFigureStringsJust"] == "TopLeft" and p["nglPanelBottom"] > 0
    assert all(c.resolved_res()["lbLabelBarOn"] is False for c in cs)
    _x, y, _w, h = cb.drawn_box
    assert y < min(ax.bbox[1] for ax in f.panels) and y - h >= 0
    assert cb.resolved["lbBoxEndCapStyle"] == "TriangleBothEnds" and cb.resolved["lbTitleString"] == "T"
    assert cb.resolved["lbLabelFontHeightF"] == 0.015 and cb.resolved["lbTitleFontHeightF"] == 0.02


def test_group_colorbars_per_row(make_da, outdir):
    f = xn.Figure(2, 2, output=outdir / "rows.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV, cmap="BlueYellowRed")
    top = f.colorbar(panels=f.row(0), label="before")
    bot = f.colorbar(panels=f.row(1), label="after", end_caps="triangles")
    f.save()
    assert "nglPanelLabelBar" not in f.panel_resolved
    for cb, row in ((top, f.row(0)), (bot, f.row(1))):
        x, y, w, h = cb.drawn_box
        bottoms = [ax.bbox[1] for ax in row]
        lefts = [ax.frame[0] for ax in row]
        assert min(bottoms) > 0
        assert y < min(bottoms) and abs(x - min(lefts)) < 0.01 and w > 0.5 and h > 0
    assert top.drawn_box[1] > bot.drawn_box[1]
    assert bot.resolved["lbBoxEndCapStyle"] == "TriangleBothEnds"
    assert bot.resolved["lbFillColors"].shape == (12, 4)
    assert bot.resolved["lbLabelAlignment"] == "InteriorEdges"
    assert bot.resolved["lbLabelFontHeightF"] == 0.012 and bot.resolved["lbTitleFontHeightF"] == 0.014


def test_group_vertical(make_da, outdir):
    f = xn.Figure(ncols=2, output=outdir / "vert.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV, cmap="cb_BrBG")
    cb = f.colorbar(panels=[f[0, 1]], orientation="vertical", label_format="{:.1f}")
    f.save()
    x, _y, _w, _h = cb.drawn_box
    assert f[0, 1].bbox[3] > 0.5 and x > f[0, 1].bbox[3] - 0.001
    assert cb.resolved["lbLabelStrings"][0] == "-1.0"


def test_group_default_palette(make_da, outdir):
    f = xn.Figure(ncols=2, output=outdir / "pal.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV)
    cb = f.colorbar(panels=[f[0, 0]])
    f.save()
    assert len(cb.resolved["lbFillColors"]) == 12


def test_title(make_da, outdir):
    png = outdir / "ti.png"
    f = xn.Figure(ncols=2, output=png, title="Main title")
    for ax in f.panels:
        ax.contour_map(make_da())
    f.save()
    assert f.panel_resolved["nglPanelTop"] == pytest.approx(0.93)
    assert white_fraction(png, 0.3, 0.7, 0.0, 0.06) < 1.0


def test_group_bar_space_reserved_and_on_page(make_da, outdir):
    f = xn.Figure(2, 2, output=outdir / "space.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV)
    f.colorbar(panels=f.row(0))
    bot = f.colorbar(panels=f.row(1))
    f.save()
    assert f.panel_resolved["nglPanelBottom"] > 0 and f.panel_resolved["nglPanelYWhiteSpacePercent"] > 0
    x, y, w, h = bot.drawn_box
    assert y - h >= 0 and x >= 0 and x + w <= 1


def test_group_bar_off_page_warns(make_da, outdir):
    f = xn.Figure(2, 1, output=outdir / "off.png", panel_res={"nglPanelBottom": 0.0})
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV)
    f.colorbar(panels=f.row(1))
    with pytest.warns(xn.errors.XnglWarning, match="outside the page"):
        f.save()
