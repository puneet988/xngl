import pytest

from xngl.errors import StyleError
from xngl.style import LOCKED, OPTIONS, PARTS, load_style, merge_resources, show


@pytest.fixture(autouse=True)
def isolated_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("XNGL_STYLE_PATH", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path / "nohome"))


def test_parts_and_locked():
    assert "contour" in PARTS and "workstation" in PARTS and len(PARTS) == 13
    assert {"nglDraw", "nglFrame", "sfXArray", "sfYArray", "nglPanelSave"} == set(LOCKED)
    assert "outer_only" in OPTIONS["ticks"] and "end_caps" in OPTIONS["colorbar"]


def test_default_loaded():
    s = load_style(None)
    assert s.options("contour")["fill"] == "area" and s.options("box")["color"] == "black"
    assert s.options("stipple") == {"marker": "dot", "size": 0.004, "color": "black"}
    assert load_style("default").options("strings")["gap"] == 0.02


def test_extends_chain_and_override(tmp_path, monkeypatch):
    (tmp_path / "a.toml").write_text('[contour]\nfill = "raster"\n[contour.res]\ncnMaxLevelCount = 255\n')
    (tmp_path / "b.toml").write_text('extends = "a"\n[strings]\ngap = 0.05\n')
    monkeypatch.setenv("XNGL_STYLE_PATH", str(tmp_path))
    s = load_style("b")
    assert s.options("contour")["fill"] == "raster" and s.options("strings")["gap"] == 0.05
    assert s.res("contour") == {"cnMaxLevelCount": 255} and s.options("box")["color"] == "black"
    assert s.name == "b"


def test_loop_detected(tmp_path, monkeypatch):
    (tmp_path / "x.toml").write_text('extends = "y"\n')
    (tmp_path / "y.toml").write_text('extends = "x"\n')
    monkeypatch.setenv("XNGL_STYLE_PATH", str(tmp_path))
    with pytest.raises(StyleError, match="loop.*x.*y"):
        load_style("x")


def test_search_order(tmp_path, monkeypatch):
    env, home = tmp_path / "env", tmp_path / "home"
    for d, g in ((env, 0.1), (home / ".config/xngl/styles", 0.2)):
        d.mkdir(parents=True)
        (d / "p.toml").write_text(f"[strings]\ngap = {g}\n")
    monkeypatch.setenv("HOME", str(home))
    assert load_style("p").options("strings")["gap"] == 0.2
    monkeypatch.setenv("XNGL_STYLE_PATH", str(env))
    assert load_style("p").options("strings")["gap"] == 0.1


def test_unknown_style_name():
    with pytest.raises(StyleError, match="style 'nosuch' not found"):
        load_style("nosuch")


def test_unknown_option_and_part():
    with pytest.raises(StyleError, match="contour.*filll"):
        load_style({"contour": {"filll": "x"}})
    with pytest.raises(StyleError, match="unknown table 'countour'"):
        load_style({"countour": {}})
    with pytest.raises(StyleError, match="colorbar.*end_cap"):
        load_style({"colorbar": {"end_cap": "triangles"}})


def test_locked_in_style_res():
    with pytest.raises(StyleError, match="nglFrame.*locked"):
        load_style({"contour": {"res": {"nglFrame": True}}})


def test_dict_style_and_path(tmp_path):
    assert load_style({"strings": {"gap": 0.3}}).options("strings")["gap"] == 0.3
    p = tmp_path / "s.toml"
    p.write_text("[strings]\ngap = 0.4\n")
    assert load_style(p).options("strings")["gap"] == 0.4
    assert load_style(str(p)).options("strings")["gap"] == 0.4


def test_merge_order_and_locked():
    out = merge_resources(style_res={"a": 1, "b": 1}, keyword_res={"b": 2, "c": 2},
                          user_res={"c": 3}, locked={"nglDraw": False})
    assert out == {"a": 1, "b": 2, "c": 3, "nglDraw": False}
    with pytest.raises(StyleError, match="nglDraw.*locked"):
        merge_resources(style_res={}, keyword_res={}, user_res={"nglDraw": True}, locked={})
    with pytest.raises(StyleError, match="pmLabelBarDisplayMode.*locked"):
        merge_resources(style_res={}, keyword_res={}, user_res={"pmLabelBarDisplayMode": "Always"},
                        locked={}, extra_locked=frozenset({"pmLabelBarDisplayMode"}))


def test_show_text():
    text = show({"strings": {"gap": 0.3}})
    assert "[strings]" in text and "gap = 0.3" in text
