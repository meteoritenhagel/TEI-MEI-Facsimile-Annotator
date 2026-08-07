from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import msgpack

from app.models.document import Document, DocumentType, Surface, Zone


class DocumentRepository:
    def load(self, path: Path) -> Document:
        data = msgpack.unpackb(path.read_bytes(), raw=False)
        surfaces = tuple(self._surface_from_dict(item) for item in data["surfaces"])
        return Document(
            surfaces=surfaces,
            document_type=self._document_type(data["document_type"]),
            current_page_index=int(data["current_page_index"]),
        )

    def save(self, path: Path, doc: Document) -> None:
        payload = asdict(doc)
        packed = msgpack.packb(payload, use_bin_type=True)
        tmp_path = path.with_name(f"{path.name}.tmp")
        tmp_path.write_bytes(packed)
        tmp_path.replace(path)

    def _surface_from_dict(self, data: dict[str, Any]) -> Surface:
        zones = tuple(
            Zone(
                ulx=float(zone["ulx"]),
                uly=float(zone["uly"]),
                lrx=float(zone["lrx"]),
                lry=float(zone["lry"]),
            )
            for zone in data["zones"]
        )
        return Surface(
            image=bytes(data["image"]),
            image_path=str(data["image_path"]),
            zones=zones,
        )

    def _document_type(self, value: object) -> DocumentType:
        if value not in ("TEI", "MEI"):
            raise ValueError(f"Unsupported document type: {value!r}")
        return value
