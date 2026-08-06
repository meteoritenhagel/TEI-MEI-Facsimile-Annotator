from __future__ import annotations

from pathlib import Path

from app.models.document import Document, Surface, Zone
from app.repositories.document_repository import DocumentRepository


def test_repository_round_trips_nested_document(tmp_path: Path) -> None:
    repository = DocumentRepository()
    path = tmp_path / "document.fca"
    original = Document(
        document_type="MEI",
        current_page_index=1,
        surfaces=(
            Surface(
                image=b"page-one",
                image_path="images/page-1.png",
                zones=(
                    Zone(1.25, 2.5, 30.75, 40.0),
                    Zone(50.0, 60.0, 70.0, 80.0),
                ),
            ),
            Surface(
                image=b"page-two",
                image_path="images/page-2.png",
                zones=(Zone(100.0, 110.0, 120.0, 130.0),),
            ),
        ),
    )

    repository.save(path, original)

    assert repository.load(path) == original


def test_repository_saves_by_replacing_sibling_tmp_file(
    tmp_path: Path, monkeypatch
) -> None:
    repository = DocumentRepository()
    path = tmp_path / "document.fca"
    doc = Document(
        document_type="TEI",
        current_page_index=0,
        surfaces=(Surface(image=b"page", image_path="page.png", zones=()),),
    )
    original_replace = Path.replace
    replace_calls: list[tuple[Path, Path]] = []

    def recording_replace(self: Path, target: Path) -> Path:
        replace_calls.append((self, target))
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", recording_replace)

    repository.save(path, doc)

    assert replace_calls == [(path.with_name("document.fca.tmp"), path)]
    assert path.exists()
    assert not path.with_name("document.fca.tmp").exists()
