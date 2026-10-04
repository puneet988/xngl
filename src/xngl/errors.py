"""Error and warning classes of xngl."""


class XnglError(Exception):
    """Base class of all xngl errors."""


class DataError(XnglError, ValueError):
    """The input data cannot be used (dimensions, coordinates, values)."""


class StyleError(XnglError):
    """A style, colormap or resource setting is not valid."""


class RenderError(XnglError):
    """PyNGL failed while drawing a figure."""


class XnglWarning(UserWarning):
    """A setting works, but the result can surprise the user."""
