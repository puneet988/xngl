"""Image comparison against reference PNGs (spec section 11.2, item 3).

Run ``pytest --update-baselines`` to rewrite the reference images on purpose. Reference images
depend on the cairo and freetype versions, which the test prints.
"""

import subprocess
import sys
from pathlib import Path

import matplotlib.image as mpimg
import numpy as np
import pytest

import xngl as xn

pytestmark = pytest.mark.render
BASELINES = Path(__file__).parents[1] / "baselines"
MAX_DIFF_FRACTION = 0.01


def _versions() -> str:
    out = subprocess.run(["conda", "list", "-p", sys.prefix, "^(cairo|freetype)$"],
                         capture_output=True, text=True, check=False).stdout
    return " ".join(ln.split()[0] + "=" + ln.split()[1] for ln in out.splitlines()
                    if ln and not ln.startswith("#"))


def _single(make_da, out):
    f = xn.Figure(output=out, width=600, style="paper")
    f.panels[0].contour_map(make_da(), levels=np.linspace(-1, 1, 21), cmap="BlueYellowRed",
                            colorbar=True, left="single")
    return f


def _rows(make_da, out):
    f = xn.Figure(2, 2, output=out, width=800, tags="a)", style={"ticks": {"outer_only": True}})
    for k, ax in enumerate(f.panels):
        ax.contour_map(make_da() * (1 + k), levels=np.linspace(-4, 4, 17), cmap="cb_BrBG",
                       left=f"exp {k}", right="850 hPa")
        ax.set_ticks(lon=10, lat=10)
    f.colorbar(panels=f.row(0), label="row 1")
    f.colorbar(panels=f.row(1), label="row 2", end_caps="triangles")
    return f


def _vectors_stipple(make_da, ngl_data, out):
    f = xn.Figure(output=out, width=600)
    ax = f.panels[0]
    ax.contour_map(make_da(), levels=np.linspace(-1, 1, 11), cmap="MPL_RdBu")
    ax.vectors(make_da(), make_da() * 0.5, stride=3, ref_magnitude=1,
               ref_label="1 m/s")
    ax.stipple(make_da() > 0.6, stride=2)
    ax.add_box(lat=(10, 20), lon=(70, 80), color="magenta", thickness=3)
    return f


@pytest.mark.parametrize("name", ["single", "rows", "vectors_stipple"])
def test_against_baseline(name, make_da, ngl_data, tmp_path, update_baselines):
    out = tmp_path / f"{name}.png"
    build = {"single": lambda: _single(make_da, out), "rows": lambda: _rows(make_da, out),
             "vectors_stipple": lambda: _vectors_stipple(make_da, ngl_data, out)}[name]
    build().save()
    ref = BASELINES / f"{name}.png"
    if update_baselines or not ref.exists():
        BASELINES.mkdir(exist_ok=True)
        ref.write_bytes(out.read_bytes())
        pytest.skip(f"baseline written: {ref} ({_versions()})")
    a, b = mpimg.imread(str(out))[..., :3], mpimg.imread(str(ref))[..., :3]
    assert a.shape == b.shape, f"image size changed ({_versions()})"
    frac = float((np.abs(a - b).max(axis=-1) > 1e-3).mean())
    print(f"{name}: {frac:.4%} pixels differ ({_versions()})")
    assert frac <= MAX_DIFF_FRACTION
