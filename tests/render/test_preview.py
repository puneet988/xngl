import pytest

import xngl.colors as xc
from xngl.errors import StyleError

pytestmark = pytest.mark.render


def test_colormap_preview(outdir):
    p = xc.show(["BlueYellowRed", "cb_BrBG", xc.from_colors(["navy", "white", "red4"], 11)],
                output=outdir / "cmaps.png")
    assert p == outdir / "cmaps.png" and p.stat().st_size > 5_000


def test_preview_unknown_name(outdir):
    with pytest.raises(StyleError, match="did you mean"):
        xc.show(["BlueYelowRed"], output=outdir / "x.png")


def test_preview_limits_boxes():
    from xngl.render.preview import preview_colors

    long = xc.get("BlueYellowRed").expand_middle(10)
    assert len(long) > 256 and len(preview_colors(long)) == 256
    assert len(preview_colors(xc.get("cb_BrBG"))) == 11
