"""Acceptance criterion 1: the MFC figure needs at most 50 plot lines with xngl."""

import json
import runpy
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

import xngl.colors as xc

ROOT = Path(__file__).parents[2]
EXAMPLE = ROOT / "examples" / "mfc_india.py"
ORIGINAL = Path(__file__).parent / "original_mfc_plot.py"
OUT = ROOT / "tests" / "output" / "acceptance"


def plot_lines(path: Path) -> list[str]:
    text = path.read_text().split("# --- plot start ---", 1)[1].split("# --- plot end ---", 1)[0]
    return [ln for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def test_plot_part_at_most_50_lines():
    n = len(plot_lines(EXAMPLE))
    print(f"xngl plot part: {n} lines")
    assert 0 < n <= 50


@pytest.mark.render
def test_same_figure_as_original(monkeypatch):
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ORIGINAL)], cwd=OUT, check=True, capture_output=True)
    info = json.loads((OUT / "original_info.json").read_text())
    monkeypatch.setattr(sys, "argv", [str(EXAMPLE), str(OUT / "xngl_mfc_new850_INDIA_JJAS.png")])
    fig = runpy.run_path(str(EXAMPLE), run_name="__main__")["fig"]
    assert (OUT / "mfc_new850_INDIA_JJAS.png").exists()
    assert (OUT / "xngl_mfc_new850_INDIA_JJAS.png").exists()
    drawn = [ax for ax in fig.panels if ax.base is not None]
    assert len(drawn) == info["nplots"] == 4
    byr = xc.get("BlueYellowRed").rgba
    expected_palette = byr[np.linspace(0, len(byr) - 1, 42).round().astype(int)]
    for ax in drawn:
        r = ax.base.resolved_res()
        np.testing.assert_allclose(r["cnLevels"], info["levels"])
        np.testing.assert_allclose(r["cnFillPalette"], expected_palette)
        assert r["cnFillMode"] == "RasterFill" and r["cnRasterSmoothingOn"] is True
    assert '"BlueYellowRed"' in ORIGINAL.read_text() and '"RasterFill"' in ORIGINAL.read_text()
