from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.models.document import DocumentType
from app.viewmodels.surface_viewmodel import SurfaceViewModel


class DocumentViewModel(QObject):
    """
    Document viewmodel.

    Signals:
        surfaces_changed (Signal()): Emitted when a surface is changed.
        document_type_changed (Signal(str)): Emitted when the document type is changed.
        current_page_index_changed (Signal(int)): Emitted when the current page index is changed.
        file_path_changed (Signal(object)): Emitted when the file path is changed.
        dirty_changed (Signal(bool)): Emitted when the dirty state is changed.
        selected_zone_index_changed (Signal(object)): Emitted when the selected zone index is changed.
    """
    surfaces_changed = Signal()
    document_type_changed = Signal(str)
    current_page_index_changed = Signal(int)
    file_path_changed = Signal(object)
    dirty_changed = Signal(bool)
    selected_zone_index_changed = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        """
        Initializer.

        :param parent: Parent QObject.
        """
        super().__init__(parent)
        self._surfaces: tuple[SurfaceViewModel, ...] = ()
        self._document_type: DocumentType = "TEI"
        self._current_page_index = 0
        self._file_path: Path | None = None
        self._dirty = False
        self._selected_zone_index: int | None = None

    @property
    def surfaces(self) -> tuple[SurfaceViewModel, ...]:
        return self._surfaces

    @surfaces.setter
    def surfaces(self, value: tuple[SurfaceViewModel, ...]) -> None:
        if value == self._surfaces:
            return
        self._surfaces = value
        self.surfaces_changed.emit()

    @property
    def document_type(self) -> DocumentType:
        return self._document_type

    @document_type.setter
    def document_type(self, value: DocumentType) -> None:
        if value not in ("TEI", "MEI"):
            raise ValueError(f"Unsupported document type: {value!r}")
        if value == self._document_type:
            return
        self._document_type = value
        self.document_type_changed.emit(self._document_type)

    @property
    def current_page_index(self) -> int:
        return self._current_page_index

    @current_page_index.setter
    def current_page_index(self, value: int) -> None:
        if value == self._current_page_index:
            return
        self._current_page_index = int(value)
        self.current_page_index_changed.emit(self._current_page_index)

    @property
    def file_path(self) -> Path | None:
        return self._file_path

    @file_path.setter
    def file_path(self, value: Path | None) -> None:
        if value == self._file_path:
            return
        self._file_path = value
        self.file_path_changed.emit(self._file_path)

    @property
    def dirty(self) -> bool:
        return self._dirty

    @dirty.setter
    def dirty(self, value: bool) -> None:
        if value == self._dirty:
            return
        self._dirty = bool(value)
        self.dirty_changed.emit(self._dirty)

    @property
    def selected_zone_index(self) -> int | None:
        return self._selected_zone_index

    @selected_zone_index.setter
    def selected_zone_index(self, value: int | None) -> None:
        if value == self._selected_zone_index:
            return
        self._selected_zone_index = value
        self.selected_zone_index_changed.emit(self._selected_zone_index)
