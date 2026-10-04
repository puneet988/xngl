"""ColorbarSpec: what a colour bar looks like. Drawing happens in xngl.render."""

from __future__ import annotations

from dataclasses import dataclass, field, fields

import numpy as np

from ..errors import StyleError

END_CAPS = {"none": "RectangleEnds", "triangles": "TriangleBothEnds",
            "triangle_low": "TriangleLowEnd", "triangle_high": "TriangleHighEnd"}
POSITIONS = {"top": "Top", "bottom": "Bottom", "left": "Left", "right": "Right"}
ORIENTATIONS = {"horizontal": "Horizontal", "vertical": "Vertical"}


@dataclass
class ColorbarSpec:
    label: str | None = None
    title_position: str = "bottom"
    orientation: str = "horizontal"
    end_caps: str = "none"
    label_stride: int = 1
    label_angle: float = 0.0
    label_format: str | None = None
    box_lines: bool = True
    raster_fill: bool = False
    width: float | None = None
    height: float | None = None
    offset: float | None = None
    res: dict = field(default_factory=dict)

    @classmethod
    def option_names(cls) -> set[str]:
        return {f.name for f in fields(cls)} - {"res"}

    @classmethod
    def from_options(cls, options: dict) -> ColorbarSpec:
        """Build from a dict of options; unknown keys raise StyleError."""
        valid = cls.option_names() | {"res"}
        unknown = sorted(set(options) - valid)
        if unknown:
            raise StyleError(f"colorbar: unknown option(s) {', '.join(unknown)}; "
                             f"valid options: {', '.join(sorted(valid))}")
        return cls(**options)

    def to_res(self, levels: np.ndarray | None = None) -> dict:
        """Labelbar resources. ``res`` is merged last and always wins."""
        for name, value, table in (("end_caps", self.end_caps, END_CAPS),
                                   ("title_position", self.title_position, POSITIONS),
                                   ("orientation", self.orientation, ORIENTATIONS)):
            if value not in table:
                raise StyleError(f"colorbar: {name}={value!r} is not valid; "
                                 f"use one of {', '.join(table)}")
        r = {
            "lbOrientation": ORIENTATIONS[self.orientation],
            "lbBoxEndCapStyle": END_CAPS[self.end_caps],
            "lbLabelStride": int(self.label_stride),
            "lbLabelAutoStride": False,
            "lbLabelAngleF": float(self.label_angle),
            "lbBoxLinesOn": bool(self.box_lines),
            "lbRasterFillOn": bool(self.raster_fill),
            "lbTitlePosition": POSITIONS[self.title_position],
        }
        if self.label:
            r["lbTitleOn"] = True
            r["lbTitleString"] = self.label
        if self.label_format and levels is not None:
            r["lbLabelStrings"] = [self.label_format.format(v) for v in np.asarray(levels)]
        r.update(self.res)
        return r
