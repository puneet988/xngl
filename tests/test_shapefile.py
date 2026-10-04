import numpy as np
import pytest

import xngl.io.shapefile as shp
from xngl.errors import DataError
from xngl.io.shapefile import attribute_names, read_shapefile


@pytest.fixture(autouse=True)
def clear_cache():
    shp.clear_cache()


def test_read_states(ngl_data):
    d = read_shapefile(ngl_data / "shp/states.shp")
    assert len(d.starts) == 95 and d.lon.size == 11481 and d.lat.size == 11481
    assert d.starts[0] == 0 and np.all(np.diff(d.starts) > 0)


def test_attribute_names(ngl_data):
    names = attribute_names(ngl_data / "shp/states.shp")
    assert "STATE_NAME" in names and "x" not in names and "segments" not in names


def test_select_features(ngl_data):
    d = read_shapefile(ngl_data / "shp/states.shp", select={"STATE_NAME": ["Texas", "Ohio"]})
    assert 2 <= len(d.starts) < 95 and d.lon.size < 11481 and d.starts[0] == 0
    one = read_shapefile(ngl_data / "shp/states.shp", select={"STATE_NAME": "Ohio"})
    assert 1 <= len(one.starts) < len(d.starts)
    assert -85 < float(np.mean(one.lon)) < -80 and 38 < float(np.mean(one.lat)) < 42


def test_select_no_match(ngl_data):
    with pytest.raises(DataError, match="no features match"):
        read_shapefile(ngl_data / "shp/states.shp", select={"STATE_NAME": "Atlantis"})


def test_select_unknown_attribute(ngl_data):
    with pytest.raises(DataError, match="STATE_NAM.*STATE_NAME"):
        read_shapefile(ngl_data / "shp/states.shp", select={"STATE_NAM": "Ohio"})


def test_cache_reads_once(ngl_data, monkeypatch):
    import Nio

    calls = []
    real = Nio.open_file
    monkeypatch.setattr(Nio, "open_file", lambda *a, **k: calls.append(a) or real(*a, **k))
    for _ in range(3):
        read_shapefile(ngl_data / "shp/states.shp")
    read_shapefile(ngl_data / "shp/states.shp", select={"STATE_NAME": "Ohio"})
    assert len(calls) == 1
