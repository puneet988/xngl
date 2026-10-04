"""Test helpers that read PyNGL objects and PNG output."""

import matplotlib.image as mpimg
import Ngl


def viewport(plot):
    """(x, y, width, height) of a plot in NDC; y is the top edge."""
    return tuple(Ngl.get_float(plot, k) for k in ("vpXF", "vpYF", "vpWidthF", "vpHeightF"))


def text_box(text_obj):
    """(x, y, width, height) of a text item after the annotation manager placed it."""
    return tuple(Ngl.get_float(text_obj, k) for k in ("vpXF", "vpYF", "vpWidthF", "vpHeightF"))


def region(png, x0, x1, y0, y1):
    """Pixels of a box given as fractions of the image (y from the top)."""
    img = mpimg.imread(str(png))[..., :3]
    h, w = img.shape[:2]
    return img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]


def white_fraction(png, x0, x1, y0, y1):
    """Fraction of white pixels in a box given as fractions of the image (y from the top)."""
    img = mpimg.imread(str(png))[..., :3]
    h, w = img.shape[:2]
    box = img[int(y0 * h):int(y1 * h), int(x0 * w):int(x1 * w)]
    return float((box.min(axis=-1) > 0.99).mean())
