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
