import os
import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr

os.environ.setdefault("PROJ_DATA", f"{sys.prefix}/share/proj")


def pytest_addoption(parser):
    parser.addoption("--update-baselines", action="store_true", default=False,
                     help="rewrite the reference images in tests/baselines")


@pytest.fixture
def update_baselines(request):
    return request.config.getoption("--update-baselines")


@pytest.fixture(scope="session")
def ngl_data():
    import ngl  # PyNGL package; only its install path is used here

    return Path(ngl.__file__).parent / "ncarg" / "data"


@pytest.fixture
def outdir(tmp_path):
    return tmp_path


def _latlon_da(values, lat, lon, name="t", **attrs):
    da = xr.DataArray(values, dims=("lat", "lon"),
                      coords={"lat": lat, "lon": lon}, name=name, attrs=attrs)
    da["lat"].attrs.update(units="degrees_north", standard_name="latitude")
    da["lon"].attrs.update(units="degrees_east", standard_name="longitude")
    return da


@pytest.fixture
def make_da():
    def _make(shape=(41, 41), lat=(0, 40), lon=(60, 100), name="t", **attrs):
        la = np.linspace(lat[0], lat[1], shape[0])
        lo = np.linspace(lon[0], lon[1], shape[1])
        lon2, lat2 = np.meshgrid(lo, la)
        values = np.sin(np.radians(lon2 * 4)) * np.cos(np.radians(lat2 * 4))
        return _latlon_da(values, la, lo, name=name, **attrs)

    return _make


def global_da(dlon=2.5, dlat=2.5):
    """Global field: lat -90..90, lon 0..360-dlon."""
    la = np.arange(-90, 90 + dlat / 2, dlat)
    lo = np.arange(0, 360, dlon)
    lon2, lat2 = np.meshgrid(lo, la)
    return _latlon_da(np.cos(np.radians(lat2)) * np.sin(np.radians(lon2)), la, lo, name="g")


def regional_da():
    """Regional field: lat 0..40, lon 60..100."""
    la, lo = np.linspace(0, 40, 41), np.linspace(60, 100, 41)
    lon2, lat2 = np.meshgrid(lo, la)
    return _latlon_da(np.sin(np.radians(lon2 * 4)) * np.cos(np.radians(lat2 * 4)), la, lo, name="r")


def curvilinear_da():
    """Field on a rotated 2-D grid with nav_lat/nav_lon coordinates on dims y, x."""
    y, x = np.meshgrid(np.arange(30), np.arange(40), indexing="ij")
    nav_lat = 10 + 0.8 * y + 0.1 * x
    nav_lon = 70 + 0.7 * x - 0.1 * y
    da = xr.DataArray(np.sin(nav_lat / 5) + np.cos(nav_lon / 7), dims=("y", "x"),
                      coords={"nav_lat": (("y", "x"), nav_lat), "nav_lon": (("y", "x"), nav_lon)},
                      name="c")
    return da
