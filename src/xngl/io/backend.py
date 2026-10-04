"""Read-only xarray backend ``engine="pynio"`` for GRIB1/2, HDF4 and HDF-EOS2/5 (spec section 9)."""

from __future__ import annotations

import os
from pathlib import Path

import Nio
import numpy as np
from xarray.backends import BackendArray, BackendEntrypoint
from xarray.backends.common import AbstractDataStore
from xarray.backends.store import StoreBackendEntrypoint
from xarray.core import indexing
from xarray.core.utils import Frozen, FrozenDict
from xarray.core.variable import Variable

from . import NIO_LOCK

EXTENSIONS = (".grb", ".grib", ".grb1", ".grib1", ".grb2", ".grib2", ".hdf", ".hdf4", ".he2",
              ".he4", ".he5", ".hdfeos")


def default_format(path, format: str) -> str:
    """Format passed to Nio.open_file.

    PyNIO's HDF-EOS5 reader crashed the Python process (bus error) on the PyNGL sample file
    in testing, so ``.he5`` files are read as plain HDF5 unless ``format`` is given.
    """
    if not format and Path(path).suffix.lower() == ".he5":
        return "h5"
    return format


def _plain(value):
    """Nio attribute values as plain Python/numpy scalars."""
    if isinstance(value, np.ndarray):
        if value.dtype.kind == "S":
            value = np.char.decode(value, "utf-8", errors="replace")
        return value.item() if value.size == 1 else value
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class PynioArray(BackendArray):
    """Lazy view of one Nio variable; only requested slices are read."""

    def __init__(self, store: PynioDataStore, name: str):
        self.store = store
        self.name = name
        var = store.file.variables[name]
        self.shape = tuple(var.shape)
        self.dtype = np.dtype(var.typecode()) if var.typecode() != "S1" else np.dtype("S1")

    def __getitem__(self, key):
        return indexing.explicit_indexing_adapter(key, self.shape,
                                                  indexing.IndexingSupport.BASIC, self._read)

    def _read(self, key: tuple):
        with NIO_LOCK:
            var = self.store.file.variables[self.name]
            data = var.get_value() if len(self.shape) == 0 else var[key]
        return np.asarray(data)


class PynioDataStore(AbstractDataStore):
    def __init__(self, filename: str, format: str = "", nio_options: dict | None = None):
        options = Nio.options()
        for k, v in (nio_options or {}).items():
            setattr(options, k, v)
        options.MaskedArrayMode = "MaskedNever"   # xarray applies _FillValue itself
        with NIO_LOCK:
            self.file = Nio.open_file(filename, "r", options=options, format=format)

    def _unique_dims(self) -> dict[str, tuple[str, ...]]:
        """Dimension names per variable; a name reused with another size gets a suffix.

        PyNIO's HDF5 reader reuses names like DIM_001 with different sizes in different
        groups, which xarray does not allow.
        """
        sizes: dict[str, int] = {}
        renamed: dict[tuple[str, int], str] = {}
        dims_of = {}
        for name, var in self.file.variables.items():
            dims = []
            for d, n in zip(var.dimensions, var.shape, strict=True):
                if sizes.setdefault(d, n) != n:
                    if (d, n) not in renamed:
                        k = 1
                        while f"{d}_{k}" in sizes:
                            k += 1
                        renamed[(d, n)] = f"{d}_{k}"
                        sizes[renamed[(d, n)]] = n
                    d = renamed[(d, n)]
                dims.append(d)
            dims_of[name] = tuple(dims)
        self._sizes = sizes
        return dims_of

    def get_variables(self):
        dims_of = self._unique_dims()
        out = {}
        for name, var in self.file.variables.items():
            attrs = {k: _plain(v) for k, v in var.attributes.items()}
            data = indexing.LazilyIndexedArray(PynioArray(self, name))
            out[name] = Variable(dims_of[name], data, attrs)
        return FrozenDict(out)

    def get_attrs(self):
        return Frozen({k: _plain(v) for k, v in self.file.attributes.items()})

    def get_dimensions(self):
        if not hasattr(self, "_sizes"):
            self._unique_dims()
        return Frozen(dict(self._sizes))

    def get_encoding(self):
        return {}

    def close(self):
        with NIO_LOCK:
            self.file.close()


class PynioBackend(BackendEntrypoint):
    """``xr.open_dataset(path, engine="pynio", format="", nio_options=None)``."""

    description = "Read GRIB1/2, HDF4 and HDF-EOS2/5 files with PyNIO (read-only)"
    url = "https://github.com/puneet988/xngl"
    open_dataset_parameters = ("filename_or_obj", "drop_variables", "format", "nio_options",
                               "mask_and_scale", "decode_times", "decode_coords",
                               "concat_characters", "use_cftime", "decode_timedelta")

    def guess_can_open(self, filename_or_obj) -> bool:
        if not isinstance(filename_or_obj, (str, os.PathLike)):
            return False
        return Path(filename_or_obj).suffix.lower() in EXTENSIONS

    def open_dataset(self, filename_or_obj, *, drop_variables=None, format: str = "",
                     nio_options: dict | None = None, mask_and_scale=True, decode_times=True,
                     decode_coords=True, concat_characters=True, use_cftime=None,
                     decode_timedelta=None):
        path = Path(filename_or_obj).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"pynio backend: file not found: {path}")
        store = PynioDataStore(str(path), format=default_format(path, format),
                               nio_options=nio_options)
        try:
            ds = StoreBackendEntrypoint().open_dataset(
                store, mask_and_scale=mask_and_scale, decode_times=decode_times,
                concat_characters=concat_characters, decode_coords=decode_coords,
                drop_variables=drop_variables, use_cftime=use_cftime,
                decode_timedelta=decode_timedelta)
        except Exception:
            store.close()
            raise
        ds.set_close(store.close)
        return ds
