import pytest

import xngl as xn

pytestmark = pytest.mark.render


def test_vectors_overlay(make_da, outdir):
    f = xn.Figure(output=outdir / "v.png")
    ax = f.panels[0]
    ax.contour_map(make_da())
    u, v = make_da(), make_da().where(make_da() > -0.5)
    vec = ax.vectors(u, v, stride=2, ref_magnitude=1.0, ref_label="1 m/s", color="red",
                     thickness=2.0)
    assert f.save().stat().st_size > 10_000
    r = vec.resolved_res()
    assert r["vfXCStride"] == 2 and r["vfYCStride"] == 2
    assert r["vcRefMagnitudeF"] == 1.0 and r["vcRefAnnoString1"] == "1 m/s" and r["vcRefAnnoOn"]
    assert r["vcLineArrowColor"] == "red" and r["vcLineArrowThicknessF"] == 2.0
    assert r["vfMissingUValueV"] == 1e20 and r["nglDraw"] is False


def test_vectors_style_defaults_no_ref(make_da, outdir):
    f = xn.Figure(output=outdir / "v2.png", style={"vectors": {"color": "blue"}})
    ax = f.panels[0]
    ax.contour_map(make_da())
    vec = ax.vectors(make_da(), make_da(), res={"vcMinDistanceF": 0.02})
    f.save()
    r = vec.resolved_res()
    assert r["vcLineArrowColor"] == "blue" and r["vcRefAnnoOn"] is False
    assert r["vcMinDistanceF"] == 0.02 and "vfXCStride" not in r
