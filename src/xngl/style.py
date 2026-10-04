"""Style presets (TOML), the extends chain, and resource merging (spec section 7)."""

from __future__ import annotations

import copy
import os
import tomllib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from .colors.colorbar import ColorbarSpec
from .errors import StyleError

PARTS = ("font", "map", "contour", "vectors", "ticks", "strings", "tags", "colorbar",
         "shapefile", "box", "stipple", "panel", "workstation")

OPTIONS: dict[str, set[str]] = {
    "font": {"name"},
    "map": set(),
    "contour": {"fill", "lines", "line_labels", "cmap"},
    "vectors": {"color", "thickness"},
    "ticks": {"outward", "label_font_height", "lon_spacing", "lat_spacing", "outer_only"},
    "strings": {"font_height", "gap"},
    "tags": {"font_height", "just"},
    "colorbar": ColorbarSpec.option_names(),
    "shapefile": {"color", "thickness", "dash"},
    "box": {"color", "thickness"},
    "stipple": {"marker", "size", "color"},
    "panel": set(),
    "workstation": set(),
}

LOCKED = frozenset({"nglDraw", "nglFrame", "sfXArray", "sfYArray", "nglPanelSave"})

_LOCK_REASON = "xngl sets it to control drawing"


@dataclass(frozen=True)
class Style:
    """A fully merged style. ``data`` maps each part to its options and ``res``."""

    name: str
    data: dict

    def options(self, part: str) -> dict:
        _check_part(part)
        return {k: v for k, v in self.data.get(part, {}).items() if k != "res"}

    def res(self, part: str) -> dict:
        _check_part(part)
        return dict(self.data.get(part, {}).get("res", {}))


def _check_part(part: str) -> None:
    if part not in PARTS:
        raise StyleError(f"unknown table '{part}'; valid tables: {', '.join(PARTS)}")


def search_path() -> list[Path]:
    """Folders searched for named styles, in order."""
    paths = [Path(p).expanduser() for p in os.environ.get("XNGL_STYLE_PATH", "").split(":") if p]
    paths.append(Path(os.environ.get("HOME", "~")).expanduser() / ".config" / "xngl" / "styles")
    return paths


def _builtin(name: str) -> dict | None:
    res = files("xngl").joinpath(f"styles/{name}.toml")
    return tomllib.loads(res.read_text()) if res.is_file() else None


def _read_named(name: str) -> dict:
    for folder in search_path():
        p = folder / f"{name}.toml"
        if p.is_file():
            return tomllib.loads(p.read_text())
    data = _builtin(name)
    if data is None:
        where = ", ".join(str(p) for p in search_path())
        raise StyleError(f"style '{name}' not found in {where} or the built-in presets")
    return data


def _validate(data: dict, origin: str) -> None:
    for part, table in data.items():
        if part == "extends":
            continue
        if part not in PARTS:
            raise StyleError(f"{origin}: unknown table '{part}'; valid tables: {', '.join(PARTS)}")
        if not isinstance(table, dict):
            raise StyleError(f"{origin}: table '{part}' must be a table")
        unknown = sorted(set(table) - OPTIONS[part] - {"res"})
        if unknown:
            raise StyleError(f"{origin}: table '{part}' has unknown option(s) "
                             f"{', '.join(unknown)}; valid: {', '.join(sorted(OPTIONS[part]))}")
        locked = sorted(set(table.get("res", {})) & LOCKED)
        if locked:
            raise StyleError(f"{origin}: {locked[0]} is locked: {_LOCK_REASON}")


def _deep_merge(base: dict, child: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in child.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _resolve(data: dict, origin: str, chain: list[str]) -> dict:
    """Merge ``data`` over its parent chain. The root is always the built-in default."""
    _validate(data, origin)
    child = {k: v for k, v in data.items() if k != "extends"}
    if chain == ["default"] and origin == "default" and "extends" not in data:
        return child
    parent_name = data.get("extends", "default")
    if parent_name in chain:
        raise StyleError(f"style extends loop: {' -> '.join([*chain, parent_name])}")
    if parent_name == "default":
        parent = _resolve(_builtin("default"), "default", ["default"])
    else:
        parent = _resolve(_read_named(parent_name), parent_name, [*chain, parent_name])
    return _deep_merge(parent, child)


def load_style(spec: str | Path | dict | None) -> Style:
    """Load a style from a name, a TOML path, a dict, or ``None`` (built-in default)."""
    if spec is None:
        spec = "default"
    if isinstance(spec, dict):
        return Style("dict", _resolve(spec, "dict", ["dict"]))
    path = Path(spec).expanduser()
    if isinstance(spec, Path) or str(spec).endswith(".toml"):
        if not path.is_file():
            raise StyleError(f"style file not found: {path}")
        return Style(path.stem, _resolve(tomllib.loads(path.read_text()), path.stem, [path.stem]))
    name = str(spec)
    if name == "default":  # the built-in root preset; user files cannot replace it
        return Style("default", _resolve(_builtin("default"), "default", ["default"]))
    return Style(name, _resolve(_read_named(name), name, [name]))


def merge_resources(*, style_res: dict, keyword_res: dict, user_res: dict, locked: dict,
                    extra_locked: frozenset = frozenset()) -> dict:
    """Merge in spec order: style < keywords < user ``res=``; locked values last."""
    all_locked = LOCKED | extra_locked
    for source in (style_res, user_res):
        bad = sorted(set(source) & all_locked)
        if bad:
            raise StyleError(f"{bad[0]} is locked: {_LOCK_REASON}")
    out = {**style_res, **keyword_res, **user_res}
    out.update(locked)
    return out


def show(spec: str | Path | dict | None) -> str:
    """The merged style as TOML-like text."""
    style = load_style(spec)
    lines = [f"# style: {style.name}"]
    for part in PARTS:
        table = style.data.get(part, {})
        lines.append(f"\n[{part}]")
        lines += [f"{k} = {_fmt(v)}" for k, v in table.items() if k != "res"]
        if table.get("res"):
            lines.append(f"[{part}.res]")
            lines += [f"{k} = {_fmt(v)}" for k, v in table["res"].items()]
    return "\n".join(lines) + "\n"


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return f'"{v}"'
    return repr(v)
