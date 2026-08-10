from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


"""
Holds whether the document is in TEI or MEI XML format.
"""
DocumentType = Literal["TEI", "MEI"]


@dataclass(frozen=True)
class Zone:
    """
    Holds the coordinates of a single zone.

    Properties:
        ulx (int): Upper left x coordinate.
        uly (int): Upper left y coordinate.
        lrx (int): Lower right x coordinate.
        lry (int): Lower right y coordinate.
    """
    ulx: int
    uly: int
    lrx: int
    lry: int


@dataclass(frozen=True)
class Surface:
    """
    Holds the state of a surface.

    Properties:
        image (bytes): Bytestring containing the raw image data.
        image_path (str): Path to the image file.
        zones (tuple[Zone, ...]): The zones associated with this surface.
    """
    image: bytes
    image_path: str
    zones: tuple[Zone, ...]


@dataclass(frozen=True)
class Document:
    """
    Holds the state of a document.

    Properties:
        surfaces (tuple[Surface, ...]): The surfaces associated with this document.
        document_type (DocumentType): Type of the document.
        current_page_index (int): The index of the page currently being edited.
    """
    surfaces: tuple[Surface, ...]
    document_type: DocumentType
    current_page_index: int
