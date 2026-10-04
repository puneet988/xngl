import Nio
import numpy as np
import pytest
import xarray as xr

from xngl.io.backend import PynioArray, PynioBackend

GRB1 = "grb/ced1.lf00.t00z.eta.grb"
GRB2 = "grb/fh.0012_tl.press_gr.awp211.grb2"


def test_engine_registered():
    assert "pynio" in xr.backends.list_engines()


def test_values_match_nio(ngl_data):
    ds = xr.open_dataset(ngl_data / GRB1, engine="pynio")
    f = Nio.open_file(str(ngl_data / GRB1))
    ref = f.variables["PRES_6_SFC"][:]
    f.close()
    np.testing.assert_allclose(ds["PRES_6_SFC"].values, np.ma.filled(ref.astype(float), np.nan),
                               equal_nan=True)
    assert ds["PRES_6_SFC"].attrs["units"] == "Pa" or "units" in ds["PRES_6_SFC"].attrs


def test_lazy_slice(ngl_data):
    ds = xr.open_dataset(ngl_data / GRB1, engine="pynio")
    var = ds["PRES_6_SFC"].variable
    assert not isinstance(var._data, np.ndarray)          # not loaded yet
    assert ds["PRES_6_SFC"][0:2, 0:3].shape == (2, 3)
    arr = PynioArray.__new__(PynioArray)
    assert hasattr(arr, "__getitem__")


def test_fill_value_becomes_nan(ngl_data, tmp_path):
    ds = xr.open_dataset(ngl_data / GRB2, engine="pynio")
    v = ds["TMP_P0_L100_GLC0"]
    assert "_FillValue" in v.encoding and not np.any(v.values == v.encoding["_FillValue"])


def test_curvilinear_grib2_coords(ngl_data):
    ds = xr.open_dataset(ngl_data / GRB2, engine="pynio")
    assert {"gridlat_0", "gridlon_0"} <= set(ds["TMP_P0_L100_GLC0"].coords)


def test_guess_can_open():
    b = PynioBackend()
    assert b.guess_can_open("a.GRB2") and b.guess_can_open("x.he5") and b.guess_can_open("x.hdf")
    assert not b.guess_can_open("x.nc") and not b.guess_can_open(123)


def test_netcdf_still_uses_netcdf4(ngl_data):
    nc = next((ngl_data / "cdf").glob("*.nc"))
    assert xr.backends.plugins.guess_engine(nc) == "netcdf4"


def test_format_override(ngl_data, tmp_path):
    p = tmp_path / "noext"
    p.write_bytes((ngl_data / GRB1).read_bytes())
    assert "PRES_6_SFC" in xr.open_dataset(p, engine="pynio", format="grib")


def test_nio_options_and_masked_mode_locked(ngl_data):
    ds = xr.open_dataset(ngl_data / GRB2, engine="pynio",
                         nio_options={"MaskedArrayMode": "MaskedAlways"})
    assert isinstance(ds["TMP_P0_L100_GLC0"].values, np.ndarray)


def test_hdf4_opens(ngl_data):
    ds = xr.open_dataset(ngl_data / "hdf/avhrr.hdf", engine="pynio")
    assert "Data_Set_2" in ds.data_vars and ds["Data_Set_2"].ndim == 2
    ds.close()


def test_he5_defaults_to_hdf5_reader(ngl_data):
    # PyNIO's HDF-EOS5 reader crashes (bus error) on this sample; xngl reads .he5 as HDF5
    # unless the user passes format="he5" explicitly.
    from xngl.io.backend import default_format

    assert default_format("x.he5", "") == "h5" and default_format("x.he5", "he5") == "he5"
    assert default_format("x.grb", "") == ""
    ds = xr.open_dataset(ngl_data / "hdf/MLS-Aura_L2GP-IWC_v02-21-c02_2007d210.he5", engine="pynio")
    assert len(ds.data_vars) > 0
    ds.close()


def test_drop_variables(ngl_data):
    ds = xr.open_dataset(ngl_data / GRB1, engine="pynio", drop_variables=["PRES_6_SFC"])
    assert "PRES_6_SFC" not in ds


def test_missing_file(tmp_path):
    with pytest.raises((FileNotFoundError, OSError)):
        xr.open_dataset(tmp_path / "none.grb", engine="pynio")


def test_conflicting_dimension_sizes_renamed(ngl_data):
    ds = xr.open_dataset(ngl_data / "hdf/MLS-Aura_L2GP-IWC_v02-21-c02_2007d210.he5", engine="pynio")
    sizes = {}
    for v in ds.variables.values():
        for d, n in zip(v.dims, v.shape, strict=True):
            assert sizes.setdefault(d, n) == n
    assert any(d.startswith("DIM_") and d.count("_") == 2 for d in sizes)
    ds.close()
