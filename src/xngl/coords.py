"""Convert an xarray.DataArray into a 2-D grid that the render layer can draw.

The checks run when the user calls a plot method, so errors appear at the line
that caused them (spec section 5.3).
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field

import numpy as np
import xarray as xr

from .errors import DataError, XnglWarning

LAT_NAMES = ("lat", "latitude", "nav_lat")
LON_NAMES = ("lon", "longitude", "nav_lon")
LAT_UNITS = ("degrees_north", "degree_north", "degree_n", "degrees_n", "degreen", "degreesn")
LON_UNITS = ("degrees_east", "degree_east", "degree_e", "degrees_e", "degreee", "degreese")


@dataclass(frozen=True)
class Field:
    """A 2-D field ready for drawing.

    ``values`` is float64 with NaN for missing data and ascending latitude.
    ``lat``/``lon`` are 1-D (rectilinear) or 2-D with the shape of ``values``.
    """

    values: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    curvilinear: bool
    attrs: dict = field(default_factory=dict)
    name: str = "data"
    cyclic_added: bool = False


def _is_axis(coord: xr.DataArray, kind: str) -> bool:
    attrs = coord.attrs
    units = str(attrs.get("units", "")).lower()
    if kind == "lat":
        return (units in LAT_UNITS or attrs.get("standard_name") == "latitude"
                or attrs.get("axis") == "Y")
    return (units in LON_UNITS or attrs.get("standard_name") == "longitude"
            or attrs.get("axis") == "X")


def find_latlon(da: xr.DataArray) -> tuple[str, str]:
    """Return the names of the latitude and longitude coordinates.

    CF attributes are searched first, then common names.
    """
    found = {}
    for kind, names in (("lat", LAT_NAMES), ("lon", LON_NAMES)):
        by_attr = [n for n, c in da.coords.items() if _is_axis(c, kind)]
        by_name = [n for n in da.coords if str(n).lower() in names]
        hits = by_attr or by_name
        if not hits:
            label = "latitude" if kind == "lat" else "longitude"
            raise DataError(
                f"no {label} coordinate found in DataArray '{da.name}'. Add CF attributes "
                f"(units='degrees_{'north' if kind == 'lat' else 'east'}') or name it "
                f"{' / '.join(names)}."
            )
        found[kind] = str(hits[0])
    return found["lat"], found["lon"]


def prepare_field(da: xr.DataArray, *, what: str = "data") -> Field:
    """Validate ``da`` and convert it into a :class:`Field`."""
    if not isinstance(da, xr.DataArray):
        raise DataError(f"{what}: expected an xarray.DataArray, got {type(da).__name__}")
    da = da.squeeze(drop=True)
    lat_name, lon_name = find_latlon(da)
    lat_c, lon_c = da[lat_name], da[lon_name]
    grid_dims = set(lat_c.dims) | set(lon_c.dims)
    extra = [d for d in da.dims if d not in grid_dims]
    if extra or da.ndim != 2:
        d = extra[0] if extra else da.dims[0]
        raise DataError(
            f"{what}: DataArray '{da.name}' has extra dimension '{d}' (size {da.sizes[d]}). "
            f"Select one value, e.g. da.isel({d}=0)."
        )

    curvilinear = lat_c.ndim == 2 or lon_c.ndim == 2
    if curvilinear:
        da = da.transpose(*lat_c.dims) if lat_c.ndim == 2 else da
        lat = np.asarray(da[lat_name].values, dtype=np.float64)
        lon = np.asarray(da[lon_name].values, dtype=np.float64)
        values = np.asarray(da.values, dtype=np.float64)
    else:
        da = da.transpose(lat_c.dims[0], lon_c.dims[0])
        # PyNGL draws non-monotonic coordinates at index positions, so sort them
        # (e.g. longitude after a 0..360 -> -180..180 change without sortby)
        la = da[lat_name].values
        if la.size > 1 and not np.all(np.diff(la) > 0):
            da = da.isel({lat_c.dims[0]: np.argsort(la, kind="stable")})
        lo = da[lon_name].values
        step = np.diff(lo)
        if lo.size > 1 and not (np.all(step > 0) or np.all(step < 0)):
            da = da.isel({lon_c.dims[0]: np.argsort(lo, kind="stable")})
        lat = np.asarray(da[lat_name].values, dtype=np.float64)
        lon = np.asarray(da[lon_name].values, dtype=np.float64)
        values = np.asarray(da.values, dtype=np.float64)

    if not np.isfinite(values).any():
        raise DataError(f"{what}: DataArray '{da.name}' contains no finite values")

    cyclic = False
    if not curvilinear and _is_global(lon):
        values = np.concatenate([values, values[:, :1]], axis=1)
        lon = np.append(lon, lon[0] + 360.0)
        cyclic = True
        warnings.warn(f"{what}: global data, a cyclic longitude point was added",
                      XnglWarning, stacklevel=3)

    return Field(values=values, lat=lat, lon=lon, curvilinear=curvilinear,
                 attrs=dict(da.attrs), name=str(da.name) if da.name is not None else what,
                 cyclic_added=cyclic)


def _is_global(lon: np.ndarray) -> bool:
    if lon.ndim != 1 or lon.size < 3:
        return False
    step = np.diff(lon)
    if not np.allclose(step, step[0]):
        return False
    return abs((lon[-1] - lon[0]) + step[0] - 360.0) < 1e-6


def same_grid(a: Field, b: Field) -> bool:
    """True when both fields have the same coordinates."""
    return (a.lat.shape == b.lat.shape and a.lon.shape == b.lon.shape
            and np.allclose(a.lat, b.lat) and np.allclose(a.lon, b.lon))


def default_label(field: Field) -> str | None:
    """Colour bar label from ``long_name`` and ``units``."""
    name = field.attrs.get("long_name")
    units = field.attrs.get("units")
    if name and units:
        return f"{name} ({units})"
    return name or None


def covers_extent(field: Field, lat: tuple | None, lon: tuple | None) -> bool:
    """True when the field covers the requested map extent."""
    tol = 1e-6
    if lat is not None and (
        min(lat) < np.nanmin(field.lat) - tol or max(lat) > np.nanmax(field.lat) + tol
    ):
        return False
    if lon is not None:
        lo_min, lo_max = np.nanmin(field.lon), np.nanmax(field.lon)
        if field.cyclic_added or (lo_max - lo_min) >= 360 - tol:
            return True
        return min(lon) >= lo_min - tol and max(lon) <= lo_max + tol
    return True
