from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Literal

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QColor


class int_range(int):
    """
    An int subclass parameterized with inclusive [low, high] bounds.

    Usage: int_range[0, 255]  -> a class, subclass of int, with .low/.high set.

    Properties:
        low (int): The lower bound of the range.
        high (int): The upper bound of the range.
    """
    low: int
    high: int

    _cache: dict[tuple[int, int], type] = {}

    def __class_getitem__(cls, params):
        if not (isinstance(params, tuple) and len(params) == 2):
            raise TypeError("int_range expects two parameters: int_range[low, high]")
        low, high = params
        if low > high:
            raise ValueError(f"low ({low}) must be <= high ({high})")

        key = (low, high)
        cached = cls._cache.get(key)
        if cached is None:
            cached = type(
                f"int_range[{low},{high}]",
                (cls,),
                {"low": low, "high": high},
            )
            cls._cache[key] = cached
        return cached

    def __new__(cls, value):
        # Optional: validate at construction time (not at class-annotation time)
        if hasattr(cls, "low") and not (cls.low <= int(value) <= cls.high):
            raise ValueError(f"{value} not in range [{cls.low}, {cls.high}]")
        return super().__new__(cls, value)


class float_range(float):
    """
    A float subclass parameterized with inclusive [low, high] bounds and a step value.

    Usage: float_range[0., 2., 0.5]  -> a class, subclass of float, with .low/.high/.step set.

    Properties:
        low (float): The lower bound of the range.
        high (float): The upper bound of the range.
        step (float): The step value of the range.
    """
    low: float
    high: float
    step: float

    _cache: dict[tuple[float, float], type] = {}

    def __class_getitem__(cls, params):
        if not (isinstance(params, tuple) and len(params) == 3):
            raise TypeError("float_range expects three parameters: float_range[low, high]")
        low, high, step = params
        if low > high:
            raise ValueError(f"low ({low}) must be <= high ({high})")
        if not 0. < step < high:
            raise ValueError(f"step ({step}) must be greater than 0. and smaller than high ({high})")

        key = (low, high)
        cached = cls._cache.get(key)
        if cached is None:
            cached = type(
                f"float_range[{low},{high},{step}]",
                (cls,),
                {"low": low, "high": high, "step": step},
            )
            cls._cache[key] = cached
        return cached

    def __new__(cls, value):
        # Optional: validate at construction time (not at class-annotation time)
        if hasattr(cls, "low") and not (cls.low <= float(value) <= cls.high):
            raise ValueError(f"{value} not in range [{cls.low}, {cls.high}]")
        return super().__new__(cls, value)


@dataclass(frozen=True)
class QtWindowSettings:
    """
    Qt window layout settings.

    Properties:
        geometry (QByteArray): Main window geometry.
        windowState (QByteArray): Window state (minimized/maximized/etc.).
    """
    geometry: QByteArray = dataclasses.field(default_factory=QByteArray)
    windowState: QByteArray = dataclasses.field(default_factory=QByteArray)


@dataclass(frozen=True)
class ImageSettings:
    """
    Image display settings.

    Properties:
        image_brightness (float_range): Brightness of the image.
        image_contrast (float_range): Contrast of the image.
        image_saturation (float_range): Saturation of the image.
    """
    image_brightness: float_range[0., 2., 0.1] = 1.0
    image_contrast: float_range[0., 2., 0.1] = 1.0
    image_saturation: float_range[0., 2., 0.1] = 1.0


@dataclass(frozen=True)
class DisplaySettings:
    """
    Object display settings:

    Properties:
        canvas_background_color (QColor): Default background color of the canvas.

        create_zone_border_thickness (float_range): When creating a new zone, the thickness of the border.
        create_zone_border_color (QColor): When creating a new zone, the color of the border.
        create_zone_fill_color (QColor): When creating a new zone, the color of the fill.
        create_zone_fill_opacity (int_range): When creating a new zone, the opacity of the fill.

        unselected_zone_border_thickness (float_range): The thickness of the border of an unselected zone.
        unselected_zone_border_color (QColor): The color of the border of an unselected zone.
        unselected_zone_fill_color (QColor): The color of the fill of an unselected zone.
        unselected_zone_fill_opacity (int_range): The opacity of the fill of an unselected zone.

        selected_zone_border_thickness (float_range): The thickness of the border of a selected zone.
        selected_zone_border_color (QColor): The color of the border of a selected zone.
        selected_zone_fill_color (QColor): The color of the fill of a selected zone.
        selected_zone_fill_opacity (int_range): The opacity of the fill of a selected zone.
    """
    canvas_background_color: QColor = field(default_factory=lambda: QColor("#e6e6e6"))

    create_zone_border_thickness: float_range[0.5, 5, 0.5] = 1.5
    create_zone_border_color: QColor = field(default_factory=lambda: QColor("#247a42"))
    create_zone_fill_color: QColor = field(default_factory=lambda: QColor("#54b464"))
    create_zone_fill_opacity: int_range[0, 255] = 35

    unselected_zone_border_thickness: float_range[0.5, 5, 0.5] = 1.5
    unselected_zone_border_color: QColor = field(default_factory=lambda: QColor("#d24d1f"))
    unselected_zone_fill_color: QColor = field(default_factory=lambda: QColor("#ffe066"))
    unselected_zone_fill_opacity: int_range[0, 255] = 40

    selected_zone_border_thickness: float_range[0.5, 5, 0.5] = 3.0
    selected_zone_border_color: QColor = field(default_factory=lambda: QColor("#0b63ce"))
    selected_zone_fill_color: QColor = field(default_factory=lambda: QColor("#ffe066"))
    selected_zone_fill_opacity: int_range[0, 255] = 85


