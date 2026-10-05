"""xngl version of the MFC figure from MFC_diff_INDIA.py (4 panels, one colour bar).

Synthetic data replace the model output, and PyNGL's sample shapefile replaces the
India shapefiles, so the example runs anywhere. Run: python examples/mfc_india.py [output.png]
"""

import sys
import tempfile
from pathlib import Path

import ngl
import numpy as np
import xarray as xr

import xngl as xn

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "mfc_new850_INDIA_JJAS.png"
SHAPEFILE = Path(ngl.__file__).parent / "ncarg/data/shp/states.shp"
EXPS = {"PD-PI": "PD_05-PI_05", "SULPHATE_2X-PI": "SULPHATE_2X-PI_05",
        "BC_5X-PI": "BC_5X-PI_05", "DUST_2X-PI": "DUST_2X-PI_05"}
LEVELS = np.linspace(-24, 24, 41)

# The user's house style (spec section 7.1), written to a temporary TOML file.
STYLE = Path(tempfile.mkdtemp()) / "puneet_paper.toml"
STYLE.write_text("""
extends = "paper"
[font]
name = "helvetica-bold"
[contour]
fill = "raster"
[contour.res]
cnRasterSmoothingOn = true
cnMaxLevelCount = 255
cnInfoLabelOn = false
[ticks]
outward = true
label_font_height = 0.011
outer_only = true
[ticks.res]
tmBorderThicknessF = 2.0
tmXBMinorOn = false
tmYLMinorOn = false
[strings]
font_height = 0.014
[colorbar]
end_caps = "triangles"
box_lines = false
raster_fill = true
title_position = "top"
[shapefile]
thickness = 2.0
""")


def synthetic_dataset() -> xr.Dataset:
    lat, lon = np.arange(-2.0, 42.1, 0.95), np.arange(59.0, 101.1, 1.25)
    lon2, lat2 = np.meshgrid(lon, lat)
    ds = xr.Dataset(coords={"lat": ("lat", lat, {"units": "degrees_north"}),
                            "lon": ("lon", lon, {"units": "degrees_east"})})
    for k, var in enumerate(EXPS.values()):
        field = 20e-5 * np.sin(np.radians(lon2 * 4 + 40 * k)) * np.cos(np.radians(lat2 * 4))
        ds[var] = (("lat", "lon"), field, {"units": "kg/m2/s"})
    return ds


ds = synthetic_dataset()

# --- plot start ---
fig = xn.Figure(ncols=4, output=OUTPUT, width=1500, style=STYLE, tags="a)")
for ax, (label, var) in zip(fig.panels, EXPS.items(), strict=True):
    ax.contour_map(ds[var] * 1e5, levels=LEVELS, cmap="BlueYellowRed",
                   lat=(0, 40), lon=(60, 100), left=label)
    ax.add_shapefile(SHAPEFILE)
    ax.add_box(lat=(17, 27), lon=(74, 88), color="darkorchid4", thickness=4)
    ax.set_ticks(lon=10, lat=5)
fig.colorbar(label="MFC at 850 hPa (kg/m2/s) x 10~S~-5~N~", label_stride=2, label_angle=45)
fig.save()
# --- plot end ---
