import numpy as np
import pytest

import xngl.colors as xc
from xngl.colors import combine, from_array, from_colors, get, register, to_colormap
from xngl.errors import StyleError


def test_get_builtin_and_custom():
    assert get("BlueYellowRed").rgba.shape == (254, 4)
    cm = get("cb_BrBG")
    assert cm.rgba.shape == (11, 4)
    np.testing.assert_allclose(cm.rgba[0, :3], np.array([84, 48, 5]) / 255)


def test_all_custom_maps_present():
    for n in ("cb_YlGnBu", "cb_YlGnBu2", "cb_PuRd", "cb_RdPu", "cb_YlGn", "cb_YlOrBr", "cb_PiYG",
              "cb_BrBG", "cb_Paired", "cb_Set1", "cb_Set3", "cb_rainbow", "ck_BlueRedBlack",
              "ck_BlueBlackRed"):
        cm = get(n)
        assert cm.rgba.min() >= 0 and cm.rgba.max() <= 1, n
    np.testing.assert_allclose(get("ck_BlueRedBlack").rgba[:, :3], [[0, 0, 1], [1, 0, 0], [0, 0, 0]])


def test_get_path(tmp_path):
    p = tmp_path / "two.rgb"
    p.write_text("0 0 0\n255 255 255\n")
    assert get(p).rgba.shape == (2, 4) and get(str(p)).name == "two"


def test_unknown_name_suggests():
    with pytest.raises(StyleError, match='did you mean "BlueYellowRed"'):
        get("BlueYelowRed")


def test_operations():
    cm = from_array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    np.testing.assert_allclose(cm.reversed().rgba[0, :3], [0, 0, 1])
    assert cm.expand_middle(3).rgba.shape[0] == 5
    np.testing.assert_allclose(cm.expand_middle(3).rgba[1:4, :3], [[0, 1, 0]] * 3)
    assert (cm + cm).rgba.shape[0] == 6 and combine(cm, cm, cm).rgba.shape[0] == 9
    started = cm.add_colors(["grey"], where="start")
    assert started.rgba.shape[0] == 4 and started.rgba[0, 0] == pytest.approx(190 / 255)
    assert cm.resample(7).rgba.shape[0] == 7
    np.testing.assert_allclose(cm.truncate(0.0, 0.5).rgba[:, :3], [[1, 0, 0], [0, 1, 0]])


def test_operations_return_new_objects():
    cm = from_array([[1, 0, 0], [0, 0, 1]])
    cm.reversed()
    np.testing.assert_allclose(cm.rgba[0, :3], [1, 0, 0])


def test_from_colors_interpolates():
    cm = from_colors(["navy", "white", "red4"], n=21)
    assert cm.rgba.shape == (21, 4)
    np.testing.assert_allclose(cm.rgba[10, :3], [1, 1, 1])
    with pytest.raises(StyleError, match="unknown colour"):
        from_colors(["navy", "notacolour"], n=5)


def test_register_and_to_colormap():
    register("mine", from_array([[0, 0, 0], [1, 1, 1]]))
    assert to_colormap("mine").name == "mine" and "mine" in xc.list()
    assert to_colormap(np.zeros((3, 3))).rgba.shape == (3, 4)
    cm = get("cb_Set1")
    assert to_colormap(cm) is cm
    with pytest.raises(StyleError):
        to_colormap(np.zeros((3, 2)))
