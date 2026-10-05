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
    page_y = 1 - f.title_resolved["y"]
    assert white_fraction(png, 0.3, 0.7, page_y - 0.02, page_y + 0.02) < 1.0


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


def test_shared_bar_uses_style_cmap_colours(make_da, outdir):
    f = xn.Figure(ncols=2, output=outdir / "stylecmap.png",
                  style={"contour": {"cmap": "cb_BrBG"}})
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV)
    cb = f.colorbar()
    f.save()
    expected = xn.colors.get("cb_BrBG").for_levels(LEV).rgba
    np.testing.assert_allclose(cb.resolved["lbFillColors"], expected)


def test_shared_bar_uses_res_palette_name(make_da, outdir):
    f = xn.Figure(ncols=2, output=outdir / "respal.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV, res={"cnFillPalette": "MPL_RdBu"})
    cb = f.colorbar()
    f.save()
    expected = xn.colors.get("MPL_RdBu").for_levels(LEV).rgba
    np.testing.assert_allclose(cb.resolved["lbFillColors"], expected)


def test_one_bar_for_all_rows_adds_no_row_gap(make_da, outdir):
    f = xn.Figure(2, 2, output=outdir / "nogap.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV)
    f.colorbar()
    f.save()
    assert f.panel_resolved["nglPanelBottom"] > 0
    assert "nglPanelYWhiteSpacePercent" not in f.panel_resolved


def test_shared_bar_default_label(make_da, outdir):  # final review I2
    f = xn.Figure(ncols=2, output=outdir / "deflabel.png")
    for ax in f.panels:
        ax.contour_map(make_da(long_name="Temperature", units="K"), levels=LEV)
    cb = f.colorbar()
    f.save()
    assert cb.resolved["lbTitleOn"] is True and cb.resolved["lbTitleString"] == "Temperature (K)"
    assert cb.label is None   # the request itself is not changed


def test_own_bar_size_and_offset(make_da, outdir):  # final review I3
    f = xn.Figure(ncols=2, output=outdir / "ownsize.png")
    # same data, so both plots have the same size: the full-size bar is the reference
    a = f[0, 0].contour_map(make_da(), levels=LEV, colorbar={"width": 1.0, "height": 1.0})
    b = f[0, 1].contour_map(make_da(), levels=LEV,
                            colorbar={"width": 0.5, "height": 0.1, "offset": 0.05})
    f.save()
    ra, rb = a.resolved_res(), b.resolved_res()
    assert 0.3 < ra["pmLabelBarWidthF"] < 1
    assert rb["pmLabelBarWidthF"] == pytest.approx(0.5 * ra["pmLabelBarWidthF"])
    assert rb["pmLabelBarHeightF"] == pytest.approx(0.1 * ra["pmLabelBarHeightF"])
    assert rb["pmLabelBarOrthogonalPosF"] == pytest.approx(0.05)
    assert "pmLabelBarOrthogonalPosF" not in ra


def test_own_bar_without_size_options_keeps_pyngl_defaults(make_da, outdir):
    f = xn.Figure(output=outdir / "ownsize0.png")
    c = f[0, 0].contour_map(make_da(), levels=LEV, colorbar=True)
    f.save()
    assert not any(k.startswith("pmLabelBar") for k in c.resolved_res())


def test_own_bar_res_beats_size_option(make_da, outdir):  # final review I3
    f = xn.Figure(output=outdir / "ownsize2.png")
    c = f[0, 0].contour_map(make_da(), levels=LEV,
                            colorbar={"width": 0.5, "res": {"pmLabelBarWidthF": 0.2}})
    f.save()
    assert c.resolved_res()["pmLabelBarWidthF"] == 0.2


def test_shared_bar_size_is_fraction_and_centred(make_da, outdir):  # final review I4
    f = xn.Figure(ncols=2, output=outdir / "frac.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV)
    cb = f.colorbar(width=0.5)
    f.save()
    x0 = min(ax.frame[0] for ax in f.panels)
    x1 = max(ax.frame[0] + ax.frame[2] for ax in f.panels)
    x, _y, w, _h = cb.drawn_box
    assert w == pytest.approx(0.5 * (x1 - x0))
    assert x + w / 2 == pytest.approx((x0 + x1) / 2)


def test_shared_vertical_bar_height_is_fraction_and_centred(make_da, outdir):  # final review I4
    f = xn.Figure(2, 1, output=outdir / "vfrac.png")
    for ax in f.panels:
        ax.contour_map(make_da(), levels=LEV)
    cb = f.colorbar(orientation="vertical", height=0.5)
    f.save()
    ytop = max(ax.frame[1] for ax in f.panels)
    ybot = min(ax.frame[1] - ax.frame[3] for ax in f.panels)
    _x, y, _w, h = cb.drawn_box
    assert h == pytest.approx(0.5 * (ytop - ybot))
    assert y - h / 2 == pytest.approx((ytop + ybot) / 2)


def test_title_sits_just_above_panels(make_da, outdir):  # final review I5
    png = outdir / "title1x4.png"
    f = xn.Figure(ncols=4, output=png, width=2000, title="Main title")
    for ax in f.panels:
        ax.contour_map(make_da())
    f.save()
    top = max(ax.bbox[0] for ax in f.panels)
    y = f.title_resolved["y"]
    assert top < y < top + 0.08
    page_y = 1 - y   # PNG rows count from the top; a 1x4 page is square
    assert white_fraction(png, 0.3, 0.7, page_y - 0.02, page_y + 0.02) < 1.0
