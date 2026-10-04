import numpy as np
import pytest

from xngl.io.colormap_files import builtin_colormap_dir, read_colormap_file, read_named_colors


def test_read_rgb_0_255(tmp_path):
    p = tmp_path / "a.rgb"
    p.write_text("ncolors=2\n# R G B\n255 0 0 # red\n0 0 255\n")
    np.testing.assert_allclose(read_colormap_file(p), [[1, 0, 0, 1], [0, 0, 1, 1]])


def test_read_0_1_values(tmp_path):
    p = tmp_path / "b.gp"
    p.write_text("0.0 0.5 1.0\n1.0 1.0 1.0\n")
    assert read_colormap_file(p)[0, 1] == 0.5


def test_all_builtin_files_parse():
    files = sorted(builtin_colormap_dir().iterdir())
    assert len(files) >= 300
    for f in files:
        a = read_colormap_file(f)
        assert a.ndim == 2 and a.shape[1] == 4 and a.shape[0] >= 2, f.name
        assert a.min() >= 0 and a.max() <= 1, f.name


def test_named_colors():
    c = read_named_colors()
    assert c["navy"] == pytest.approx((0, 0, 128 / 255))
    assert "darkorchid4" in c and "navyblue" in c
