import xngl
from xngl.errors import DataError, RenderError, StyleError, XnglError, XnglWarning


def test_error_tree():
    assert issubclass(DataError, XnglError) and issubclass(DataError, ValueError)
    assert issubclass(StyleError, XnglError) and issubclass(RenderError, XnglError)
    assert issubclass(XnglWarning, UserWarning)


def test_version():
    assert xngl.__version__ == "0.1.0"
