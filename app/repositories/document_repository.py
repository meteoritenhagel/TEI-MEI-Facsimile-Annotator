from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import msgpack

from app.models.document import Document, DocumentType, Surface, Zone


class DocumentRepository:
    """
    Repository for loading/saving documents from/to the file system.

    Methods:
        load (Path): Loads the serialized document data from the file system into the Document model.
        save (Path, Document): Saves the Document model data into a serialized file on the file system.

    Private Methods:
        _surface_from_dict (dict[str, Any]): Creates a Surface model from the serialized document data.
        _document_type (object): Checks the document type for validity and returns it.
    """
    @classmethod
    def load(cls, path: Path) -> Document:
        """
        Loads the serialized document data from the file system into the Document model.

        :param path: Path to load from.
        :return: Document model.
        """
        data = msgpack.unpackb(path.read_bytes(), raw=False)
        surfaces = tuple(cls._surface_from_dict(item) for item in data["surfaces"])
        return Document(
            surfaces=surfaces,
            document_type=cls._document_type(data["document_type"]),
            current_page_index=int(data["current_page_index"]),
        )

    @classmethod
    def save(cls, path: Path, doc: Document) -> None:
        """
        Saves the serialized document data from the file system into the file system into the Document model.

        :param path: Path to save to.
        :param doc: Document to save.
        """
        payload = asdict(doc)
        packed = msgpack.packb(payload, use_bin_type=True)
        tmp_path = path.with_name(f"{path.name}.tmp")
        tmp_path.write_bytes(packed)
        tmp_path.replace(path)

    @classmethod
    def _surface_from_dict(cls, data: dict[str, Any]) -> Surface:
        """
        Creates a Surface model from the serialized document data.

        :param data: Serialized surface data.
        :return: Surface model.
        """
        zones = tuple(
            Zone(
                ulx=int(zone["ulx"]),
                uly=int(zone["uly"]),
                lrx=int(zone["lrx"]),
                lry=int(zone["lry"]),
            )
            for zone in data["zones"]
        )
        return Surface(
            image=bytes(data["image"]),
            image_path=str(data["image_path"]),
            zones=zones,
        )

    @classmethod
    def _document_type(cls, value: object) -> DocumentType:
        """
        Checks the document type for validity and returns it.

        :param value: Document type value.
        :raise ValueError: If document type is invalid.
        :return: Document type value if valid.
        """
        if value not in ("TEI", "MEI"):
            raise ValueError(f"Unsupported document type: {value!r}")
        return value
