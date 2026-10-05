import numpy as np
import pytest
from conftest import curvilinear_da, global_da, regional_da

from xngl.coords import covers_extent, default_label, find_latlon, prepare_field, same_grid
from xngl.errors import DataError, XnglWarning


def test_extra_dim_error(make_da):
    da = make_da().expand_dims(time=3)
    with pytest.raises(DataError, match=r"extra dimension 'time' \(size 3\).*isel"):
        prepare_field(da)


def test_size1_dims_squeezed(make_da):
    assert prepare_field(make_da().expand_dims(time=1)).values.ndim == 2


def test_descending_lat_flipped(make_da):
    da = make_da().isel(lat=slice(None, None, -1))
    f = prepare_field(da)
    assert f.lat[0] < f.lat[-1]
    np.testing.assert_array_equal(f.values, make_da().values)


def test_names_without_cf_attrs(make_da):
    da = make_da().rename(lat="latitude", lon="longitude")
    for c in ("latitude", "longitude"):
        da[c].attrs.clear()
    assert find_latlon(da) == ("latitude", "longitude")


def test_cf_attrs_beat_names(make_da):
    da = make_da().rename(lat="y", lon="x")
    assert find_latlon(da) == ("y", "x")


def test_no_latlon_error(make_da):
    da = make_da().rename(lat="a", lon="b")
    for c in ("a", "b"):
        da[c].attrs.clear()
    with pytest.raises(DataError, match="latitude"):
        prepare_field(da)


def test_curvilinear():
    f = prepare_field(curvilinear_da())
    assert f.curvilinear and f.lat.shape == f.values.shape and f.lon.shape == f.values.shape


def test_cyclic_only_global():
    g = global_da(dlon=2.5)
    with pytest.warns(XnglWarning, match="cyclic"):
        f = prepare_field(g)
    assert f.cyclic_added and f.values.shape[1] == g.sizes["lon"] + 1
    assert f.lon[-1] == pytest.approx(f.lon[0] + 360)
    assert not prepare_field(regional_da()).cyclic_added


def test_masked_int_float32(make_da):
    assert prepare_field((make_da() * 100).astype("int16")).values.dtype == np.float64
    da = make_da().astype("float32")
    da = da.where(da > 0)
    f = prepare_field(da)
    assert f.values.dtype == np.float64 and np.isnan(f.values).any()


def test_dask_backed(make_da):
    pytest.importorskip("dask")
    assert isinstance(prepare_field(make_da().chunk()).values, np.ndarray)


def test_all_nan_error(make_da):
    with pytest.raises(DataError, match="no finite values"):
        prepare_field(make_da() * np.nan)


def test_same_grid(make_da):
    a, b = prepare_field(make_da()), prepare_field(make_da() * 2)
    assert same_grid(a, b)
    assert not same_grid(a, prepare_field(make_da(shape=(21, 21))))


def test_covers_extent_0_360(make_da):
    with pytest.warns(XnglWarning, match="cyclic"):
        g = prepare_field(global_da(dlon=2.5))
    assert covers_extent(g, None, (-20, 40))
    r = prepare_field(make_da())
    assert not covers_extent(r, None, (-20, 40))
    assert covers_extent(r, (5, 30), (65, 90)) and not covers_extent(r, (-10, 30), None)


def test_default_label(make_da):
    assert default_label(prepare_field(make_da(long_name="Temperature", units="K"))) == "Temperature (K)"
    assert default_label(prepare_field(make_da(long_name="Temperature"))) == "Temperature"
    assert default_label(prepare_field(make_da())) is None


def test_unsorted_lon_is_sorted():  # final review C1
    da = global_da()
    da = da.assign_coords(lon=((da.lon + 180) % 360) - 180)   # -180..177.5, not sorted
    with pytest.warns(XnglWarning, match="cyclic"):
        f = prepare_field(da)
    assert np.all(np.diff(f.lon) > 0) and f.cyclic_added
    np.testing.assert_allclose(f.values[:, :-1], da.sortby("lon").values)


def test_unsorted_lat_is_sorted(make_da):  # final review C1
    idx = np.random.default_rng(0).permutation(41)
    f = prepare_field(make_da().isel(lat=idx))
    assert np.all(np.diff(f.lat) > 0)
    np.testing.assert_array_equal(f.values, make_da().values)
