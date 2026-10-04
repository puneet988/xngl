import numpy as np
import pytest

from xngl.errors import DataError, StyleError, XnglError, XnglWarning
from xngl.panel import Panel
from xngl.specs import BoxSpec, ContourSpec, CustomSpec, ShapefileSpec, StippleSpec, VectorSpec

LEV = np.linspace(-1, 1, 11)


def test_records_layers_in_order(make_da, ngl_data):
    ax = Panel((0, 0))
    c = ax.contour_map(make_da(), levels=LEV, cmap="BlueYellowRed", left="PD-PI", right="850 hPa")
    s = ax.add_shapefile(ngl_data / "shp/states.shp")
    b = ax.add_box(lat=(17, 27), lon=(74, 88), color="magenta")
    assert isinstance(c, ContourSpec) and isinstance(s, ShapefileSpec) and isinstance(b, BoxSpec)
    assert ax.base is c and ax.layers == [c, s, b]
    assert ax.strings.left == "PD-PI" and ax.strings.right == "850 hPa"
    assert c.cmap.name == "BlueYellowRed" and b.color == "magenta"
    np.testing.assert_allclose(c.levels, LEV)


def test_style_backed_keywords_default_none(make_da):
    c = Panel((0, 0)).contour_map(make_da())
    assert c.fill is None and c.levels is None and c.cmap is None and c.colorbar is False


def test_vectors_need_contour(make_da):
    with pytest.raises(XnglError, match="add a contour_map to this panel first"):
        Panel((0, 0)).vectors(make_da(), make_da())


def test_second_contour_map(make_da):
    ax = Panel((1, 2))
    ax.contour_map(make_da())
    with pytest.raises(XnglError, match=r"panel \(1, 2\) already has a contour_map"):
        ax.contour_map(make_da())


def test_vectors_recorded(make_da):
    ax = Panel((0, 0))
    ax.contour_map(make_da())
    v = ax.vectors(make_da(), make_da(), stride=2, ref_magnitude=1.0, ref_label="1 m/s")
    assert isinstance(v, VectorSpec) and v.stride == 2 and ax.layers[-1] is v


def test_uv_grids_differ(make_da):
    ax = Panel((0, 0))
    ax.contour_map(make_da())
    with pytest.raises(DataError, match="u and v are on different grids"):
        ax.vectors(make_da(), make_da(shape=(21, 21)))


def test_stipple_checks(make_da):
    ax = Panel((0, 0))
    ax.contour_map(make_da())
    st = ax.stipple(make_da() > 0.5, stride=2)
    assert isinstance(st, StippleSpec) and st.mask.values.dtype == np.float64
    with pytest.raises(DataError, match="mask grid does not match"):
        ax.stipple(make_da(shape=(21, 21)) > 0)
    with pytest.raises(DataError, match="boolean"):
        ax.stipple(make_da())


def test_stipple_needs_contour(make_da):
    with pytest.raises(XnglError, match="add a contour_map to this panel first"):
        Panel((0, 0)).stipple(make_da() > 0)


def test_levels_must_increase(make_da):
    with pytest.raises(DataError, match="levels must increase"):
        Panel((0, 0)).contour_map(make_da(), levels=[0, 2, 1])


def test_unknown_cmap(make_da):
    with pytest.raises(StyleError, match="did you mean"):
        Panel((0, 0)).contour_map(make_da(), cmap="BlueYelowRed")


def test_missing_shapefile(tmp_path):
    with pytest.raises(DataError, match="add_shapefile: file not found"):
        Panel((0, 0)).add_shapefile(tmp_path / "none.shp")


def test_locked_res(make_da):
    with pytest.raises(StyleError, match="sfXArray.*locked"):
        Panel((0, 0)).contour_map(make_da(), res={"sfXArray": [1, 2]})


def test_bad_fill(make_da):
    with pytest.raises(DataError, match="fill"):
        Panel((0, 0)).contour_map(make_da(), fill="smooth")


def test_levels_not_covering_warns(make_da):
    with pytest.warns(XnglWarning, match="do not cover the data range"):
        Panel((0, 0)).contour_map(make_da(), levels=[-0.1, 0, 0.1])


def test_extent_not_covered_warns(make_da):
    with pytest.warns(XnglWarning, match="do not cover the map extent"):
        Panel((0, 0)).contour_map(make_da(), lat=(-10, 40))


def test_layer_res_editable_and_not_rendered(make_da):
    c = Panel((0, 0)).contour_map(make_da())
    c.res["cnLinesOn"] = True
    assert c.res == {"cnLinesOn": True}
    with pytest.raises(XnglError, match="not rendered"):
        c.resolved_res()


def test_custom_hook_ticks_strings(make_da):
    ax = Panel((0, 0))
    ax.contour_map(make_da())

    def f(wks, plot, panel):
        return None

    ax.add_custom(f)
    ax.set_ticks(lon=10, lat=[0, 20, 40])
    ax.set_strings(center="C")
    assert isinstance(ax.layers[-1], CustomSpec) and ax.layers[-1].func is f
    assert ax.ticks.lon == 10 and ax.ticks.lat == [0, 20, 40] and ax.strings.center == "C"
    with pytest.raises(XnglError, match="callable"):
        ax.add_custom("not a function")
