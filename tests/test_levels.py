import numpy as np

from xngl.colors import from_colors, nice_levels, symmetric_levels


def test_symmetric_levels():
    np.testing.assert_allclose(symmetric_levels(24, 1.2), np.linspace(-24, 24, 41))


def test_nice_levels_cover_data():
    lev = nice_levels(np.array([-0.37, 2.81]), n=10)
    assert lev[0] <= -0.37 and lev[-1] >= 2.81 and 5 <= len(lev) <= 15
    assert np.all(np.diff(lev) > 0)


def test_nice_levels_ignore_nan():
    lev = nice_levels(np.array([np.nan, 0.0, 1.0]), n=5)
    assert lev[0] <= 0 and lev[-1] >= 1


def test_for_levels_counts_and_middle_white():
    cm = from_colors(["blue", "white", "red"], n=101)
    assert cm.for_levels(symmetric_levels(1, 0.2)).rgba.shape[0] == 12   # 11 levels
    odd = cm.for_levels(np.linspace(-1, 1, 10))                           # 10 levels -> 11 colours
    assert odd.rgba.shape[0] == 11
    np.testing.assert_allclose(odd.rgba[5, :3], [1, 1, 1], atol=0.02)
