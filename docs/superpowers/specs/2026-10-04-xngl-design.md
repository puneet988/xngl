# xngl: design specification

- **Date:** 2026-10-04
- **Status:** draft for review
- **Repository:** `git@github.com:puneet988/xngl.git`
- **Import:** `import xngl as xn`

## 1. Purpose

xngl is a Python package for publication figures of gridded geoscience data. It draws `xarray.DataArray` objects with PyNGL, and it reads extra file formats and shapefiles with PyNIO.

The package has two goals:

1. **Less boilerplate.** Today a 4-panel PyNGL figure needs about 235 lines. About half of these lines set resources one by one, and about 150 lines are helper functions that are copied into each script. With xngl, a script contains only the choices for that figure: data, levels, colormap, region and labels.
2. **Full control.** Every PyNGL resource and every `Ngl` call must stay available. The package must never block a change that raw PyNGL allows.

### 1.1 Users

1. First: the author and his group, for their own papers.
2. Later: the wider NCL/PyNGL community.

For this reason, the public API is small, uses general names (`lat=`, `lon=`, not `india=True`) and stays stable from v1. Installation from git is enough for v1. Documentation and a conda-forge recipe come later.

### 1.2 Source of the requirements

The requirements come from these scripts in `/home/puneet/Documents/pyngl_files`:

- `plot_VIMFC_wind/MF_850hPa/INDIA/MFC_diff_INDIA.py` (contour panels, shapefiles, study region)
- `plot_VIMFC_wind/divergence_and_divergent_wind_850hPa/INDIA/ud_vd_etc_diff_INDIA.py` (contours with vectors)
- `spatial_DJF_meteorology/plot_DJF_CAPE_CIN_CAM5_CMIP5_CAM5G.py` (DJF panels)
- `other_examples/plotting_code_pyngl.py` (t-test stippling)

They also come from the colormap functions in `map_funcs.py` (ckplotlib).

## 2. Scope

### 2.1 In scope for v1

1. Filled contour maps (area, raster or cell fill).
2. Vector overlays on a contour map.
3. Multi-panel figures with:
   - a colour bar on each panel, or
   - one colour bar for all panels, or
   - one colour bar for a group of panels (for example, one row), or
   - a mix of these.
4. Left, centre and right strings above each panel, and panel tags (a), b), …).
5. Shapefile outlines, with feature selection by attribute, and rectangular region boxes.
6. Stippling of points from a boolean mask (for example, `p < 0.05`).
7. Lat/lon tick labels in the form `60E`, `10N`.
8. A colormap module: named, custom, reversed, truncated and combined colormaps.
9. Style presets in TOML files.
10. A read-only xarray backend `engine="pynio"` for GRIB1/2, HDF4 and HDF-EOS2/5.

### 2.2 Out of scope for v1

1. Data analysis: time means, statistics, regridding.
2. Writing data files. xarray already writes NetCDF.
3. XY plots, streamlines, skew-T, unstructured grids (MPAS, ICON). These can come later.
4. Line-contour overlays. Until a method exists, users can use `res=` or the custom hook.
5. Filled shapefile polygons and writing shapefiles.
6. The xarray accessor (`da.xn.contour_map(...)`). It comes after v1 as a thin wrapper around the core API.
7. A matplotlib or cartopy backend.

## 3. Constraints and decisions

| # | Decision | Reason |
|---|---|---|
| D1 | v1 targets **Python 3.11 with numpy 1.x**. | The newest conda-forge builds of PyNGL 1.6.1 and PyNIO 1.5.5 support Python up to 3.11 and need numpy < 2.0. |
| D2 | The Python 3.12 port of PyNGL/PyNIO is a **separate sub-project**. | A probe on 2026-10-04 showed that the port is possible but has open problems (see section 13). The package must not wait for it. |
| D3 | PyNIO is a **required** dependency. | It reads shapefiles and the formats that xarray cannot read. |
| D4 | `netCDF4` and `cftime` are dependencies. | xarray needs them for NetCDF4 files and non-standard calendars (for example `360_day`). |
| D5 | The core API is a **Figure object with plot methods** (approach A). | It matches matplotlib and `xarray.plot`. It handles panels, overlays and shared colour bars well. A fluent builder was rejected because panels and overlays become awkward. |
| D6 | Drawing is **deferred** until `fig.save()`. | Shared colour bars need the levels of all panels. Tick labels need the final panel positions. The output format is known only at save. |
| D7 | Only `xngl/render/` imports `Ngl`. Only `xngl/io/` imports `Nio`. | Most code can be tested without drawing. The port touches only a few modules. |
| D8 | Colours are set **per plot** with `cnFillPalette`, never with `Ngl.define_colormap`. | This allows a different colormap in each panel. A test on 2026-10-04 confirmed that `cnFillPalette` accepts names and N×4 RGBA arrays. |
| D9 | Panel strings use `Ngl.add_annotation` with positions relative to the plot frame. | The strings move with the plot when the layout changes. A test on 2026-10-04 confirmed this for 2×2 and 1×4 layouts. |
| D10 | Styles are TOML files read with the standard library `tomllib`. | No extra dependency. Python 3.11 includes `tomllib`. |
| D11 | xngl keeps **no catalogue** of PyNGL resources. | PyNGL already warns about unknown resources. A catalogue would need constant maintenance. |

## 4. Architecture

### 4.1 Module layout

```
src/xngl/
├── __init__.py          public API: Figure, colors, style, errors
├── figure.py            Figure: grid, panel list, colour bar requests, save()
├── panel.py             Panel: plot methods, records layer specs, custom hooks
├── specs.py             dataclasses: ContourSpec, VectorSpec, ShapefileSpec,
│                        BoxSpec, StippleSpec, StringsSpec, TicksSpec, CustomSpec
├── coords.py            DataArray → numpy: find lat/lon, sort, flip, cyclic
│                        point, NaN/mask → missing value
├── style.py             presets, extends chain, merge order, locked resources
├── errors.py            XnglError, DataError, StyleError, RenderError
├── colors/
│   ├── colormaps.py     Colormap object, registry, operations
│   ├── levels.py        level helpers
│   └── colorbar.py      ColorbarSpec (what a colour bar looks like)
├── styles/              built-in presets: default.toml, paper.toml
├── render/              ← the only modules that import Ngl
│   ├── workstation.py   open_wks, destroy
│   ├── plots.py         specs → Ngl.contour_map, Ngl.vector, Ngl.overlay
│   ├── overlays.py      polylines (shapefiles, boxes), polymarkers (stipple)
│   ├── annotations.py   panel strings, lat/lon tick labels
│   ├── colorbar.py      panel labelbar or computed labelbar_ndc
│   └── layout.py        Ngl.panel, tags, figure title
└── io/                  ← the only modules that import Nio
    ├── backend.py       xarray backend engine="pynio" (read-only)
    ├── shapefile.py     shapefile → lon, lat, segments (cached)
    └── colormap_files.py  reads NCL .rgb/.gp colormap files
```

### 4.2 Data flow

```
user script
   │  fig = xn.Figure(...); ax.contour_map(da, ...); fig.colorbar(...)
   ▼
Figure / Panel ──► coords.py (validate and convert the DataArray at once)
   │  record specs only
   ▼
fig.save()
   ▼
render/: open_wks → plots → overlays → tick labels → strings → custom hooks
         → Ngl.panel → group colour bars → frame → destroy(wks)
```

### 4.3 Rules

1. Public objects (`Figure`, `Panel`, specs, `Colormap`, styles) hold plain Python and numpy data. They do not hold PyNGL objects before `save()`.
2. Each figure calls `Ngl.destroy(wks)`. xngl never calls `Ngl.end()`, so one script or notebook can make many figures.
3. Errors appear at the call that caused them (section 8).
4. After `save()`, `ax.ngl_plot` and `fig.wks` give the raw PyNGL ids for inspection. Changes at this point do not reach the output. Use the custom hook for changes.

## 5. Public API

### 5.1 Figure

```python
fig = xn.Figure(
    nrows=1, ncols=1,
    output="figure.pdf",      # format from extension: .pdf .png .eps .ps .svg
    size=None,                # (width, height) in inches for PDF/PS/EPS
    width=None,               # pixels for PNG
    style="default",          # preset name, path to a TOML file, dict, or None
    tags=None,                # "a)", "(a)", "A", a list of strings, or None
    title=None,               # one title above all panels
    panel_res=None,           # raw Ngl.panel resources
)

fig.panels                    # list of Panel, row by row
fig[i, j]                     # one panel
fig.row(i), fig.col(j)        # lists of panels
fig.colorbar(panels=None, label=None, **colorbar_options)   # None = all panels
fig.save()                    # renders and writes; returns the output path
```

### 5.2 Panel

Each plot method validates its input at once and records a layer. It returns the layer object. The user can change `layer.res` before `save()`.

```python
ax.contour_map(da, levels=None, cmap=None,
               lat=None, lon=None,                 # map extent, e.g. lat=(0, 40)
               fill="area",                        # "area" | "raster" | "cell"
               colorbar=False,                     # True, or a dict of colorbar options
               left=None, center=None, right=None,
               projection="CylindricalEquidistant",
               res=None)

ax.vectors(u, v, stride=1, ref_magnitude=None, ref_label=None,
           color="black", thickness=1.0, res=None)

ax.add_shapefile(path, select=None, color="black", thickness=1.0, dash=0, res=None)
ax.add_box(lat=(lat0, lat1), lon=(lon0, lon1), color="black", thickness=1.0, res=None)
ax.stipple(mask, marker="dot", size=0.004, color="black", stride=1, res=None)
ax.set_ticks(lon=None, lat=None)        # spacing in degrees, or explicit lists
ax.set_strings(left=None, center=None, right=None)
ax.add_custom(func)                     # func(wks, plot, panel)
```

Rules:

1. `ax.vectors()` overlays the panel's map. A panel needs a `contour_map` before `vectors`. A vector-only map is out of scope for v1.
2. `ax.stipple(mask)` takes a boolean DataArray on the same grid as the panel's contour data. It draws all points with one `Ngl.add_polymarker` call.
3. `ax.add_custom(func)` runs during rendering, after the built-in layers and before `Ngl.panel` (section 7). The function can call any `Ngl` function.
4. If `colorbar=True` on a panel and the same panel is in a `fig.colorbar()` group, `save()` raises an error.

### 5.3 DataArray input rules (`coords.py`)

1. After removing size-1 dimensions, the array must be 2-D. Otherwise a `DataError` names the extra dimensions and suggests `.sel()` or `.isel()`.
2. Latitude and longitude are found from CF attributes (`units="degrees_north"`, `units="degrees_east"`, `standard_name`, `axis`) or from common names (`lat`, `latitude`, `nav_lat`, `lon`, `longitude`, `nav_lon`). The search order is CF attributes, then names.
3. 1-D (rectilinear) and 2-D (curvilinear) coordinates are allowed. 2-D coordinates are passed with `sfXArray`/`sfYArray` as 2-D arrays.
4. Descending latitude is flipped to ascending.
5. A cyclic longitude point is added only when the data cover 360° of longitude.
6. NaN and masked values become the missing value. They are drawn transparent by default.
7. If a colour bar has no label, the label is `long_name (units)` from the DataArray attributes, when they exist.

### 5.4 Example

```python
import numpy as np, xarray as xr, xngl as xn

ds = xr.open_dataset("mfc_new850.nc")
exps = {"PD-PI": "PD_05-PI_05", "SULPHATE_2X-PI": "SULPHATE_2X-PI_05",
        "BC_5X-PI": "BC_5X-PI_05", "DUST_2X-PI": "DUST_2X-PI_05"}
lev = np.linspace(-24, 24, 41)

fig = xn.Figure(ncols=4, output="mfc_new850_INDIA_JJAS.png", width=8200,
                style="puneet_paper", tags="a)")
for ax, (label, var) in zip(fig.panels, exps.items()):
    ax.contour_map(ds[var] * 1e5, levels=lev, cmap="BlueYellowRed",
                   lat=(0, 40), lon=(60, 100), left=label)
    ax.add_shapefile("India_world_full_kashmir.shp", thickness=7)
    ax.add_shapefile("PUNEETJJASSTUDYREGION.shp", color="darkorchid4", thickness=15)
    ax.set_ticks(lon=10, lat=5)

fig.colorbar(label="MFC at 850 hPa (kg/m2/s) x 10~S~-5~N~",
             end_caps="triangles", label_stride=2, label_angle=45)
fig.save()
```

## 6. Colours: `xngl.colors`

### 6.1 Colormap object

A `Colormap` has a name and an N×4 RGBA array with values from 0 to 1. Each operation returns a new `Colormap`.

```python
from xngl import colors as xc

xc.get("BlueYellowRed")              # NCL built-in colormap (about 300)
xc.get("cb_BrBG")                    # custom colormaps from map_funcs.py, built in
xc.get("path/to/precip.rgb")         # NCL .rgb or .gp file
xc.from_colors(["navy", "white", "darkred"], n=21)   # interpolate named colours
xc.from_array(rgb_or_rgba_array)

cm.reversed()
cm.truncate(0.1, 0.9)                # keep a fraction range
cm.resample(n)                       # n evenly spaced colours
cm.expand_middle(n)                  # repeat the middle colour n times
cm.add_colors(["grey"], where="end") # "start" or "end"
xc.combine(cm1, cm2, ...)            # also cm1 + cm2
cm.for_levels(levels)                # exactly len(levels) + 1 colours

xc.register("name", cm)              # then cmap="name" works everywhere
xc.list()                            # all available names
xc.show(["BlueYellowRed", "cb_BrBG"], output="colormaps.png")   # preview sheet
```

Rules:

1. `cmap=` in any API call accepts a name, a `Colormap` or an N×3/N×4 array.
2. The custom colormaps from `map_funcs.py` (`cb_*`, `ck_*`) are stored without the old NCL background and foreground entries (the first two rows).
3. An unknown name raises a `StyleError` that lists close matches.
4. `cm.for_levels(levels)` with an odd number of colours puts the middle colour at the middle interval. With symmetric levels around zero, zero gets the middle colour.

### 6.2 Levels (`levels.py`)

- `xc.symmetric_levels(limit, step)` gives levels from `-limit` to `+limit`.
- `xc.nice_levels(data, n)` gives about `n` rounded levels that cover the data range.

### 6.3 Colour bar options (`colorbar.py`)

`ColorbarSpec` holds what a colour bar looks like. `fig.colorbar(...)` and `ax.contour_map(..., colorbar={...})` accept these options:

| Option | Meaning |
|---|---|
| `label` | title text |
| `title_position` | `"top"`, `"bottom"`, `"left"`, `"right"` |
| `orientation` | `"horizontal"` or `"vertical"` |
| `end_caps` | `"none"`, `"triangles"`, `"triangle_low"`, `"triangle_high"` |
| `label_stride` | show every n-th label |
| `label_angle` | label rotation in degrees |
| `label_format` | Python format string, e.g. `"{:.1f}"` |
| `box_lines` | lines between colour boxes on or off |
| `raster_fill` | smooth raster fill on or off |
| `width`, `height` | size as a fraction of the panel group |
| `offset` | distance from the panels |
| `res` | raw labelbar resources |

New colour bar options go into `colorbar.py`. New colormap operations go into `colormaps.py`. Both only produce arrays and settings for `render/`.

## 7. Styles and resource merging

### 7.1 Style file

A style is a TOML file with one table per plot part. Each table can contain:

- package options, with the same names as the API keywords, and
- raw PyNGL resources in a `.res` sub-table.

Tables: `font`, `map`, `contour`, `vectors`, `ticks`, `strings`, `tags`, `colorbar`, `shapefile`, `box`, `stipple`, `panel`, `workstation`.

```toml
extends = "paper"

[font]
name = "helvetica-bold"

[contour]
fill = "raster"
[contour.res]
cnRasterSmoothingOn = true
cnMaxLevelCount     = 255

[ticks]
outward = true
label_font_height = 0.03
[ticks.res]
tmBorderThicknessF = 2.0

[colorbar]
end_caps = "triangles"
box_lines = false
```

### 7.2 Where styles come from

1. Built-in presets: `"default"` (close to PyNGL defaults) and `"paper"` (bold fonts, outward ticks, no info label).
2. User presets by name, found in `~/.config/xngl/styles/` and in the folders of the `XNGL_STYLE_PATH` environment variable (colon-separated). The search order is `XNGL_STYLE_PATH`, then `~/.config/xngl/styles/`, then built-in presets.
3. A path to a TOML file.
4. A dict with the same structure, for one figure.

`extends` can form a chain. A chain that loops raises a `StyleError`.

### 7.3 Merge order

From lowest to highest priority:

1. **Locked internals.** Examples: `nglDraw=False`, `nglFrame=False`, `sfXArray`, `sfYArray`, and `pmLabelBarDisplayMode` when a shared colour bar is used.
2. **Style preset**, after the `extends` chain is resolved.
3. **API keywords**, translated to resources. Example: `levels=lev` gives `cnLevelSelectionMode="ExplicitLevels"` and `cnLevels=lev`.
4. **Raw `res={...}`.** It always wins over levels 2 and 3.

If a style or `res=` sets a locked resource, xngl raises a `StyleError`. The message names the resource and says why it is locked.

### 7.4 Inspection

- `xn.style.show(name)` prints the merged style.
- `layer.resolved_res()` returns the final resources sent to PyNGL. It is available after `save()`.

## 8. Rendering and errors

### 8.1 Rendering order in `fig.save()`

```
0. pre-flight checks
1. open the workstation (format and size from Figure)
2. for each panel:
   a. base plot: Ngl.contour_map with nglDraw=False
   b. vectors: Ngl.vector, then Ngl.overlay on the base plot
   c. overlays: add_polyline (shapefiles, boxes), add_polymarker (stipple)
   d. lat/lon tick labels: blank-plot overlay
   e. strings: text with nglDraw=False, then add_annotation
   f. custom hooks: func(wks, plot, panel)
3. Ngl.panel: layout, tags, figure title, and the built-in labelbar when one
   colour bar covers all panels
4. group colour bars: read each plot's final viewport, then labelbar_ndc
5. Ngl.frame
6. Ngl.destroy(wks): always runs, also after an error (try/finally)
```

Each figure has exactly one frame. PNG output gets the given file name.

### 8.2 Errors

| Stage | Checks | Error class |
|---|---|---|
| At the call | data is 2-D; lat/lon found; `u` and `v` share a grid; the stipple mask matches the grid; levels increase; the colormap exists; the shapefile exists; no locked resource is set | `DataError`, `StyleError` |
| Pre-flight (start of `save()`) | panels that share a colour bar have the same levels and colormap; a panel is not in two colour bar groups and does not have its own colour bar as well; the output folder exists and is writable | `XnglError` |
| Rendering | a PyNGL call returns `None` or raises | `RenderError` with the panel index and layer name. The partial output file is deleted. |

Class tree: `XnglError` → `DataError` (also a `ValueError`), `StyleError`, `RenderError`.

Warnings (Python `warnings`) for cases that work but can surprise:

1. The data do not cover the map extent.
2. The levels do not cover the data range.
3. A cyclic point was added.

Limit: PyNGL prints its own warnings from C code. xngl cannot catch them.

## 9. PyNIO backend (`io/backend.py`)

```python
ds = xr.open_dataset("gfs.grb2", engine="pynio")
ds = xr.open_dataset("datafile", engine="pynio", format="grib2")
ds = xr.open_dataset("f.grb2", engine="pynio",
                     nio_options={"InitialTimeCoordinateType": "Numeric"})
```

1. **Registration:** entry point `xarray.backends: pynio = xngl.io.backend:PynioBackend` in `pyproject.toml`.
2. **guess_can_open:** True for `.grb .grib .grb1 .grib1 .grb2 .grib2 .hdf .hdf4 .he2 .he4 .he5 .hdfeos`. False for `.nc`, so NetCDF files keep using the `netcdf4` engine.
3. **Lazy reading:** each variable is a `BackendArray`. Only the requested slices are read.
4. **Missing values:** files are opened with `MaskedArrayMode="MaskedNever"`. The backend passes `_FillValue`, `scale_factor` and `add_offset` to xarray, and xarray's CF decoding applies them.
5. **Names:** variable and dimension names stay as PyNIO/NCL names (for example `TMP_P0_L100_GLL0`, `lat_0`).
6. **Thread safety:** all Nio calls use one shared lock.
7. **Options:** `nio_options` goes to `Nio.options()`. `format` goes to `Nio.open_file(format=...)`.
8. **Read-only:** the backend has no write support.

## 10. Shapefiles (`io/shapefile.py`)

```python
ax.add_shapefile("India_states.shp")
ax.add_shapefile("India_states.shp", select={"STATE_NAME": ["Bihar", "Jharkhand"]},
                 color="red", thickness=4)
```

1. Nio reads `x`, `y`, `segments` and `geometry`.
2. `select={attribute: value or list of values}` keeps only the matching features. An unknown attribute raises a `DataError` that lists the available attributes.
3. Each file is read once per Python session. The cache key is the absolute path and the modification time.
4. Rendering is one `Ngl.add_polyline` call per panel and shapefile, with `gsSegments`.

## 11. Testing

### 11.1 Unit tests (no drawing)

1. `coords.py`: descending latitude, 0–360 and −180–180 longitude, curvilinear grids, NaN and masks, extra dimensions, cyclic point only for global data.
2. `style.py`: `extends` chains, loop detection, merge order, locked resources, dict styles, search path order.
3. `colors/`: every operation gives the expected RGBA array; `for_levels` puts the middle colour at zero for symmetric levels; `.rgb` parsing; close matches for unknown names.
4. `specs.py` and `panel.py`: every error in section 8.2 "At the call" raises the documented class and message.

### 11.2 Render tests (PyNGL draws)

1. Smoke tests: every plot type and layer writes a non-empty PDF and PNG.
2. Structure checks (preferred): after `save()`, check `layer.resolved_res()` and query plots with `Ngl.get_float`. Examples: a left string is above the top-left corner of its plot; a group colour bar is below its row.
3. A few image comparisons against stored reference PNGs. The test fails if more than 1% of pixels differ. `pytest --update-baselines` writes new reference images. The tests record the versions of cairo and freetype.

### 11.3 Backend and shapefile tests

These tests use the sample files in the PyNGL install (`ngl/ncarg/data`): GRIB1, GRIB2, HDF4, HDF-EOS5 and `shp/states.shp`.

1. Values from `xr.open_dataset(engine="pynio")` equal values from a direct Nio read.
2. Slices read lazily. `_FillValue` becomes NaN.
3. `guess_can_open` accepts GRIB/HDF and rejects `.nc`. `format=` works.
4. `select=` returns the correct features. The cache reads each file once.

### 11.4 Acceptance tests

1. **Boilerplate:** a test script draws the figure of `MFC_diff_INDIA.py` with xngl, with synthetic data. The plot part has at most 50 lines. Its PNG is compared with the output of the original plot code on the same synthetic data.
2. **Control:** a list of every resource and `Ngl` call in the 4 scripts of section 1.2. For each item, a test shows that it works through one of these levels: keyword, style, `res=`, or custom hook.

### 11.5 Tools

- `pytest` and `ruff`.
- Tests run headless. PyNGL writes PNG and PDF without a display.
- `environment.yml`: Python 3.11, conda-forge `pyngl`, `pynio`, `numpy<2`, `scipy`, `xarray`, `netCDF4`, `cftime`, `pytest`, `ruff`.
- Tests never use paths to user data.
- GitHub Actions CI is optional and can be added later.

## 12. Packaging

1. `pyproject.toml` with a `src/` layout and setuptools.
2. `requires-python = ">=3.11,<3.12"` for v1. The upper bound is removed after the port sub-project.
3. PyNGL and PyNIO are not on PyPI. The README tells users to install them from conda-forge first, then to run `pip install -e .`.
4. License: MIT.
5. The built-in styles and the custom colormaps ship as package data.

## 13. Future work

1. **xarray accessor** (`da.xn.contour_map(...)`) as a thin wrapper around the core API.
2. **More plot types:** line-contour overlays, XY plots, streamlines.
3. **Python 3.12 port of PyNGL and PyNIO** (separate sub-project). Findings from the probe on 2026-10-04:
   - PyNGL and PyNIO both built on Python 3.12 + numpy 1.26 after fixes to the build system (`distutils` and `numpy.distutils` removed), compiler flags for GCC 14/15, HDF5 1.14 API and g2clib 2.x.
   - Gallery output matched Python 3.11 (less than 1% of pixels different).
   - Open problems: GRIB2 decoding with g2clib 2.3 (2 test failures), `np.int` in `coordsel.py` (conda-forge already patches this).
   - Python 3.13 needs numpy 2. PyNGL needs only renames of old numpy constants. PyNIO shows runtime errors in 4 test suites that need debugging in `niomodule.c`.
   - The conda-forge feedstock patches should be the starting point.

## 14. Items to verify during planning

1. How `Ngl.panel` handles a panel without a plot (empty panel).
2. That the blank-plot tick label overlay works with every projection in scope, or only with `CylindricalEquidistant`. If only that projection works, other projections use the default PyNGL tick marks.
3. That `nglPanelLabelBar` uses the palette given with `cnFillPalette`.
