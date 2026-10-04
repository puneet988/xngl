"""File input: colormap files, shapefiles and the PyNIO xarray backend.

Only modules in this package import Nio. All Nio calls hold ``NIO_LOCK``,
because PyNIO is not documented as thread-safe.
"""

import threading

NIO_LOCK = threading.Lock()
