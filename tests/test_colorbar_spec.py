import numpy as np
import pytest

from xngl.colors import ColorbarSpec
from xngl.errors import StyleError


def test_colorbar_to_res():
    r = ColorbarSpec(label="MFC", end_caps="triangles", label_stride=2, label_angle=45,
                     box_lines=False, raster_fill=True, title_position="top").to_res()
    assert r["lbBoxEndCapStyle"] == "TriangleBothEnds" and r["lbLabelStride"] == 2
    assert r["lbLabelAutoStride"] is False
    assert r["lbTitleString"] == "MFC" and r["lbTitleOn"] and r["lbTitlePosition"] == "Top"
    assert r["lbBoxLinesOn"] is False and r["lbRasterFillOn"] and r["lbLabelAngleF"] == 45
    assert r["lbOrientation"] == "Horizontal"


def test_defaults_and_res_last():
    r = ColorbarSpec(res={"lbBoxLinesOn": True, "lbPerimOn": False}, box_lines=False).to_res()
    assert r["lbBoxEndCapStyle"] == "RectangleEnds" and "lbTitleString" not in r
    assert r["lbBoxLinesOn"] is True and r["lbPerimOn"] is False


def test_label_format_makes_strings():
    r = ColorbarSpec(label_format="{:.1f}").to_res(levels=np.array([0, 0.5, 1]))
    assert r["lbLabelStrings"] == ["0.0", "0.5", "1.0"]


def test_bad_values():
    with pytest.raises(StyleError, match="end_caps"):
        ColorbarSpec(end_caps="arrows").to_res()
    with pytest.raises(StyleError, match="orientation"):
        ColorbarSpec(orientation="diagonal").to_res()


def test_from_options_unknown_key():
    with pytest.raises(StyleError, match="end_cap.*valid"):
        ColorbarSpec.from_options({"end_cap": "triangles"})
    assert ColorbarSpec.from_options({"label_stride": 3}).label_stride == 3
