from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DocumentType = Literal["TEI", "MEI"]


@dataclass(frozen=True)
class ImageSettings:
    brightness: float_range[0, 255] = 50
