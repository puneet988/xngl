import numpy as np
import pytest
from conftest import global_da

import xngl as xn
from xngl.errors import RenderError, StyleError, XnglWarning

pytestmark = pytest.mark.render


def test_single_panel_png(make_da, outdir):
    f = xn.Figure(output=outdir / "one.png", width=600)
    c = f.panels[0].contour_map(make_da(), levels=np.linspace(-1, 1, 21), cmap="BlueYellowRed")
    p = f.save()
    assert p == outdir / "one.png" and p.stat().st_size > 10_000
    r = c.resolved_res()
    assert r["cnLevelSelectionMode"] == "ExplicitLevels" and r["cnFillPalette"].shape == (22, 4)
    assert r["mpMinLatF"] == 0 and r["mpMaxLonF"] == 100 and r["nglDraw"] is False
    assert r["cnFillOn"] is True and r["cnFillMode"] == "AreaFill" and r["lbLabelBarOn"] is False
    assert f.panels[0].frame is not None


@pytest.mark.parametrize("ext", ["pdf", "png", "eps", "ps", "svg"])
def test_formats(make_da, outdir, ext):
    f = xn.Figure(output=outdir / f"x.{ext}")
    f.panels[0].contour_map(make_da())
    assert f.save().stat().st_size > 1000


def test_uppercase_extension(make_da, outdir):
    f = xn.Figure(output=outdir / "u.PNG")
    f.panels[0].contour_map(make_da())
    assert f.save() == outdir / "u.PNG" and (outdir / "u.PNG").exists()


def test_empty_panel_and_save_twice(make_da, outdir):
    f = xn.Figure(ncols=2, output=outdir / "e.png")
    f[0, 0].contour_map(make_da())
    a = f.save().stat().st_mtime_ns
    b = f.save().stat().st_mtime_ns
    assert b >= a and not list(outdir.glob("e.0000*"))
    assert f.panel_resolved["nglPanelSave"] is True and f.panel_resolved["nglFrame"] is False


def test_res_wins_and_style_fill(make_da, outdir):
    f = xn.Figure(output=outdir / "r.png", style={"contour": {"fill": "raster"}})
    c = f.panels[0].contour_map(make_da(), res={"cnRasterSmoothingOn": True, "cnLinesOn": True})
    f.save()
    r = c.resolved_res()
    assert r["cnFillMode"] == "RasterFill" and r["cnRasterSmoothingOn"] and r["cnLinesOn"] is True


def test_layer_res_change_after_call(make_da, outdir):
    f = xn.Figure(output=outdir / "l.png")
    c = f.panels[0].contour_map(make_da())
    c.res["cnInfoLabelOn"] = False
    f.save()
    assert c.resolved_res()["cnInfoLabelOn"] is False


def test_locked_in_panel_res(make_da, outdir):
    f = xn.Figure(output=outdir / "p.png", panel_res={"nglFrame": True})
    f.panels[0].contour_map(make_da())
    with pytest.raises((RenderError, StyleError), match="nglFrame.*locked"):
        f.save()


def test_missing_values_and_own_colorbar(make_da, outdir):
    da = make_da(long_name="Temperature", units="K")
    da = da.where(da > -0.5)
    f = xn.Figure(output=outdir / "m.png")
    c = f.panels[0].contour_map(da, levels=np.linspace(-1, 1, 11), colorbar=True)
    f.save()
    r = c.resolved_res()
    assert r["sfMissingValueV"] == 1e20 and r["cnMissingValFillColor"] == "transparent"
    assert r["lbLabelBarOn"] is True and r["lbTitleString"] == "Temperature (K)"


def test_constant_field_warns(make_da, outdir):
    f = xn.Figure(output=outdir / "k.png")
    f.panels[0].contour_map(make_da() * 0 + 3)
    with pytest.warns(XnglWarning, match="constant"):
        f.save()


def test_lon_mismatch_global(outdir):
    f = xn.Figure(output=outdir / "g.png")
    with pytest.warns(XnglWarning, match="cyclic"):
        f.panels[0].contour_map(global_da(dlon=2.5), lon=(-20, 40), lat=(-30, 30))
    assert f.save().stat().st_size > 10_000


def test_curvilinear_renders(outdir):
    from conftest import curvilinear_da

    f = xn.Figure(output=outdir / "c.png")
    c = f.panels[0].contour_map(curvilinear_da())
    f.save()
    assert c.resolved_res()["sfXArray"].shape == (30, 40)


def test_render_error_cleans_up(make_da, outdir, monkeypatch):
    monkeypatch.setattr("xngl.render.plots.Ngl.contour_map", lambda *a, **k: None)
    f = xn.Figure(output=outdir / "bad.png")
    f.panels[0].contour_map(make_da())
    with pytest.raises(RenderError, match=r"panel \(0, 0\).*contour_map"):
        f.save()
    assert not (outdir / "bad.png").exists()


def test_pyngl_ids_cleared_after_save(make_da, outdir):  # final review I1
    # the workstation is destroyed in save(); dangling ids crash PyNGL when used
    f = xn.Figure(output=outdir / "ids.png")
    f.panels[0].contour_map(make_da())
    f.save()
    ax = f.panels[0]
    assert f.wks is None and ax.ngl_plot is None and ax.attached == [] and ax.string_ids == {}
    assert ax.frame is not None and ax.bbox is not None
