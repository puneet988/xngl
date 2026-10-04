"""Test helpers that read PyNGL objects and PNG output."""

import matplotlib.image as mpimg


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
