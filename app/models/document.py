from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


DocumentType = Literal["TEI", "MEI"]


@dataclass(frozen=True)
class Zone:
    ulx: int
    uly: int
    lrx: int
    lry: int


@dataclass(frozen=True)
class Surface:
    image: bytes
    image_path: str
    zones: tuple[Zone, ...]


@dataclass(frozen=True)
class Document:
    surfaces: tuple[Surface, ...]
    document_type: DocumentType
    current_page_index: int
