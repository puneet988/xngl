import numpy as np
import pytest

import xngl as xn

pytestmark = pytest.mark.render


def test_overlays_and_hook(make_da, ngl_data, outdir):
    seen = []
    f = xn.Figure(output=outdir / "o.png")
    ax = f.panels[0]
    ax.contour_map(make_da())
    s = ax.add_shapefile(ngl_data / "shp/states.shp", color="red", thickness=3, dash=2)
    b = ax.add_box(lat=(17, 27), lon=(74, 88), color="magenta")
    st = ax.stipple(make_da() > 0.5, stride=2, marker="filled_circle", color="grey")
    ax.add_custom(lambda wks, plot, panel: seen.append((panel.index, plot is panel.ngl_plot)))
    f.save()
    assert seen == [((0, 0), True)]
    rs, rb, rst = s.resolved_res(), b.resolved_res(), st.resolved_res()
    assert rs["gsLineColor"] == "red" and rs["gsLineThicknessF"] == 3 and rs["gsLineDashPattern"] == 2
    assert len(rs["gsSegments"]) == 95
    assert rb["gsLineColor"] == "magenta" and rb["gsLineThicknessF"] == 1.0
    assert rst["gsMarkerIndex"] == 16 and rst["gsMarkerColor"] == "grey"
    assert rst["gsMarkerSizeF"] == 0.004


def test_stipple_points_and_stride(make_da, outdir):
    from xngl.render.overlays import stipple_points

    ax = xn.Figure().panels[0]
    ax.contour_map(make_da())
    mask = make_da() > 0.5
    st = ax.stipple(mask, stride=1)
    lon, lat = stipple_points(st)
    assert lat.size == lon.size
    assert lon.size == int(mask.values.sum())
    st2 = ax.stipple(mask, stride=2)
    lon2, _ = stipple_points(st2)
    assert lon2.size == int(mask.values[::2, ::2].sum())
    assert np.all((lon >= 60) & (lon <= 100))


def test_shapefile_select_renders(make_da, ngl_data, outdir):
    f = xn.Figure(output=outdir / "sel.png")
    ax = f.panels[0]
    with pytest.warns(xn.errors.XnglWarning, match="map extent"):
        ax.contour_map(make_da(), lat=(25, 50), lon=(-125, -65))
    s = ax.add_shapefile(ngl_data / "shp/states.shp", select={"STATE_NAME": "Ohio"})
    f.save()
    assert 1 <= len(s.resolved_res()["gsSegments"]) < 95
