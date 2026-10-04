# xngl

Publication maps of `xarray` data with PyNGL, with less boilerplate and full control.

A 4-panel figure with one shared colour bar takes about 235 lines of raw PyNGL. With xngl, the
plot part takes 9 lines (see `examples/mfc_india.py`). Every PyNGL resource stays available.

## Install

PyNGL and PyNIO are not on PyPI. Install them from conda-forge first:

```bash
conda env create -f environment.yml      # or: conda install -c conda-forge pyngl pynio
conda activate xngl-dev
pip install -e .
```

xngl v1 needs Python 3.11 and numpy 1.x, because the conda-forge builds of PyNGL and PyNIO
stop at these versions.

## Quick start

```python
import numpy as np, xarray as xr, xngl as xn

ds = xr.open_dataset("mfc_new850.nc")
exps = {"PD-PI": "PD_05-PI_05", "SULPHATE_2X-PI": "SULPHATE_2X-PI_05",
        "BC_5X-PI": "BC_5X-PI_05", "DUST_2X-PI": "DUST_2X-PI_05"}

fig = xn.Figure(ncols=4, output="mfc_INDIA.png", width=3000, style="paper", tags="a)")
for ax, (label, var) in zip(fig.panels, exps.items()):
    ax.contour_map(ds[var] * 1e5, levels=np.linspace(-24, 24, 41), cmap="BlueYellowRed",
                   lat=(0, 40), lon=(60, 100), left=label, right="850 hPa")
    ax.add_shapefile("India_world_full_kashmir.shp", thickness=2)
    ax.add_box(lat=(17, 27), lon=(74, 88), color="darkorchid4", thickness=4)
    ax.set_ticks(lon=10, lat=5)
fig.colorbar(label="MFC (kg/m2/s) x 10~S~-5~N~", end_caps="triangles", label_stride=2)
fig.save()
```

Nothing is drawn until `fig.save()`. Errors in the data appear at the line that caused them.

## What a panel can draw

| Method | What it does |
|---|---|
| `ax.contour_map(da, levels, cmap, lat, lon, fill, colorbar, left/center/right, projection, res)` | filled contour map of a 2-D DataArray |
| `ax.vectors(u, v, stride, ref_magnitude, ref_label, color, thickness, res)` | vector overlay |
| `ax.add_shapefile(path, select={"STATE_NAME": [...]}, color, thickness, dash, res)` | outlines, optionally only some features |
| `ax.add_box(lat=(a, b), lon=(c, d), color, thickness, res)` | rectangular region |
| `ax.stipple(pvals < 0.05, marker, size, color, stride, res)` | dots where a mask is true |
| `ax.set_ticks(lon=10, lat=5)` | `60E` / `10N` labels (CylindricalEquidistant) |
| `ax.add_custom(func)` | `func(wks, plot, panel)` runs before the panel layout: call any `Ngl` function |

Colour bars: `colorbar=True` on a panel, or `fig.colorbar(panels=...)` for one bar shared by
some or all panels (for example `fig.row(0)`).

## Control: four levels

1. **Keywords:** `levels=`, `cmap=`, `lat=`, `fill=` ...
2. **Styles:** TOML files with package options and raw resources, for example
   `~/.config/xngl/styles/mine.toml`, used with `style="mine"`.
3. **Raw resources:** `res={"cnRasterSmoothingOn": True}` on any layer, `panel_res=` on the figure.
4. **Hooks:** `ax.add_custom(func)`.

After `save()`, `layer.resolved_res()` shows the exact resources sent to PyNGL.

```toml
# ~/.config/xngl/styles/mine.toml
extends = "paper"
[contour]
fill = "raster"
[contour.res]
cnRasterSmoothingOn = true
[ticks]
outward = true
outer_only = true
[colorbar]
end_caps = "triangles"
label_font_height = 0.013
```

`xn.style.show("mine")` prints the merged style.

## Colormaps

```python
from xngl import colors as xc

cm = xc.get("BlueYellowRed")                      # about 300 NCL colormaps
cm = xc.get("cb_BrBG")                            # map_funcs.py colormaps (cb_*, ck_*)
cm = xc.from_colors(["navy", "white", "red4"], n=21)   # NCL colour names
cm = xc.combine(xc.get("MPL_Blues").reversed(), xc.get("MPL_Reds")).expand_middle(3)
xc.register("mfc_div", cm)                        # then cmap="mfc_div"
xc.show(["BlueYellowRed", "cb_BrBG"], output="colormaps.png")
```

## GRIB and HDF files

```python
ds = xr.open_dataset("gfs.grb2", engine="pynio")               # GRIB1/2, HDF4, HDF-EOS
ds = xr.open_dataset("datafile", engine="pynio", format="grib2")
```

The backend is read-only. NetCDF files keep using xarray's `netcdf4` engine. `.he5` files are
read with PyNIO's HDF5 reader by default; pass `format="he5"` for the HDF-EOS5 reader.

## Tests

```bash
pytest                         # unit, render, backend and acceptance tests
pytest --update-baselines      # rewrite the reference images in tests/baselines
```
