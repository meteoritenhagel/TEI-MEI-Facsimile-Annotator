from __future__ import annotations

from pathlib import Path
from typing import Callable, Generic, Literal, TypeVar

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from app.models.document import Document, Surface, Zone
from app.repositories.document_repository import DocumentRepository
from app.services.mapping_service import (
    document_to_viewmodel,
    surface_to_viewmodel,
    viewmodel_to_document,
    zone_to_viewmodel,
)
from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.surface_viewmodel import SurfaceViewModel
from app.viewmodels.zone_viewmodel import ZoneViewModel


T = TypeVar("T")


class RepoTaskSignals(QObject):
    finished = Signal(object)
    failed = Signal(object)


class RepoTask(QRunnable, Generic[T]):
    def __init__(self, work: Callable[[], T]) -> None:
        super().__init__()
        self._work = work
        self.signals = RepoTaskSignals()

    @Slot()
    def run(self) -> None:
        try:
            result = self._work()
        except Exception as error:
            self.signals.failed.emit(error)
            return
        self.signals.finished.emit(result)


class DocumentService(QObject):
    open_succeeded = Signal()
    save_succeeded = Signal()
    save_failed = Signal(object)
    open_failed = Signal(object)
    add_surface_succeeded = Signal()
    add_surface_failed = Signal(object)

    def __init__(
        self,
        repository: DocumentRepository,
        document_viewmodel: DocumentViewModel,
        thread_pool: QThreadPool | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._document_vm = document_viewmodel
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._active_tasks: set[RepoTask] = set()

    def new_document(self) -> None:
        self._document_vm.surfaces = ()
        self._document_vm.document_type = "TEI"
        self._document_vm.current_page_index = 0
        self._document_vm.file_path = None
        self._document_vm.dirty = False
        self._document_vm.selected_zone_index = None

    def open_file(self, path: Path) -> None:
        task: RepoTask[Document] = RepoTask(lambda: self._repository.load(path))
        task.signals.finished.connect(lambda doc: self._open_finished(path, doc))
        task.signals.failed.connect(self.open_failed.emit)
        self._run_task(task)

    def save_file(self) -> bool:
        if self._document_vm.file_path is None:
            return False
        self._save_to_path(self._document_vm.file_path)
        return True

    def save_file_as(self, path: Path) -> None:
        self._save_to_path(path)

    def go_to_page(self, index: int) -> None:
        if not 0 <= index < len(self._document_vm.surfaces):
            return
        self._document_vm.current_page_index = index
        self._document_vm.selected_zone_index = None

    def add_surface_from_images(self, paths: list[Path]) -> bool:
        for path in paths:
            try:
                image = path.read_bytes()
            except Exception as error:
                self.add_surface_failed.emit(error)
                return False
            surface = Surface(image=image, image_path=str(path), zones=())
            surface_vm = SurfaceViewModel(parent=self._document_vm)
            surface_to_viewmodel(surface, surface_vm)
            self._document_vm.surfaces = (*self._document_vm.surfaces, surface_vm)

        # Go to first newly added page!
        self._document_vm.current_page_index = len(self._document_vm.surfaces) - len(paths)
        self._document_vm.selected_zone_index = None
        self._document_vm.dirty = True
        self.add_surface_succeeded.emit()
        return True

    def remove_surface(self, surface_index: int) -> None:
        self._surface_at(surface_index)
        old_current_page_index = self._document_vm.current_page_index
        self._document_vm.surfaces = (
            *self._document_vm.surfaces[:surface_index],
            *self._document_vm.surfaces[surface_index + 1 :],
        )
        if not self._document_vm.surfaces:
            new_current_page_index = 0
        elif old_current_page_index > surface_index:
            new_current_page_index = old_current_page_index - 1
        elif old_current_page_index >= len(self._document_vm.surfaces):
            new_current_page_index = len(self._document_vm.surfaces) - 1
        else:
            new_current_page_index = old_current_page_index
        self._document_vm.current_page_index = new_current_page_index
        if surface_index <= old_current_page_index:
            self._document_vm.selected_zone_index = None
        self._document_vm.dirty = True

    def add_zone(self, surface_index: int, zone: Zone) -> None:
        surface_vm = self._surface_at(surface_index)
        zone_vm = ZoneViewModel(parent=surface_vm)
        zone_to_viewmodel(zone, zone_vm)
        surface_vm.zones = (*surface_vm.zones, zone_vm)
        self._document_vm.dirty = True

    def remove_zone(self, surface_index: int, zone_index: int) -> None:
        surface_vm = self._surface_at(surface_index)
        self._zone_at(surface_vm, zone_index)
        surface_vm.zones = (
            *surface_vm.zones[:zone_index],
            *surface_vm.zones[zone_index + 1 :],
        )
        self._document_vm.dirty = True
        self._adjust_selection_after_zone_removed(surface_index, zone_index)

    def update_zone_rect(
        self,
        surface_index: int,
        zone_index: int,
        ulx: int,
        uly: int,
        lrx: int,
        lry: int,
    ) -> None:
        surface_vm = self._surface_at(surface_index)
        zone_vm = self._zone_at(surface_vm, zone_index)
        zone_vm.set_rect(ulx, uly, lrx, lry)
        self._document_vm.dirty = True

    def select_zone(self, zone_index: int | None) -> None:
        if zone_index is not None:
            surface_vm = self._current_surface()
            self._zone_at(surface_vm, zone_index)
        self._document_vm.selected_zone_index = zone_index

    def set_document_type(self, doc_type: Literal["TEI", "MEI"]) -> None:
        if doc_type == self._document_vm.document_type:
            return
        self._document_vm.document_type = doc_type
        self._document_vm.dirty = True

    def _open_finished(self, path: Path, doc: Document) -> None:
        document_to_viewmodel(doc, self._document_vm)
        self._document_vm.file_path = path
        self._document_vm.dirty = False
        self._document_vm.selected_zone_index = None
        self.open_succeeded.emit()

    def _save_to_path(self, path: Path) -> None:
        doc = viewmodel_to_document(self._document_vm)
        task: RepoTask[None] = RepoTask(lambda: self._repository.save(path, doc))
        task.signals.finished.connect(lambda _: self._save_finished(path))
        task.signals.failed.connect(self.save_failed.emit)
        self._run_task(task)

    def _save_finished(self, path: Path) -> None:
        self._document_vm.file_path = path
        self._document_vm.dirty = False
        self.save_succeeded.emit()

    def _run_task(self, task: RepoTask) -> None:
        self._active_tasks.add(task)

        def discard_task(_result: object = None) -> None:
            self._active_tasks.discard(task)

        task.signals.finished.connect(discard_task)
        task.signals.failed.connect(discard_task)
        self._thread_pool.start(task)

    def _surface_at(self, index: int):
        if not 0 <= index < len(self._document_vm.surfaces):
            raise IndexError(f"Surface index out of range: {index}")
        return self._document_vm.surfaces[index]

    def _current_surface(self):
        return self._surface_at(self._document_vm.current_page_index)

    def _zone_at(self, surface_vm, index: int) -> ZoneViewModel:
        if not 0 <= index < len(surface_vm.zones):
            raise IndexError(f"Zone index out of range: {index}")
        return surface_vm.zones[index]

    def _adjust_selection_after_zone_removed(
        self, surface_index: int, removed_zone_index: int
    ) -> None:
        if surface_index != self._document_vm.current_page_index:
            return
        selected = self._document_vm.selected_zone_index
        if selected is None:
            return
        if selected == removed_zone_index:
            self._document_vm.selected_zone_index = None
        elif removed_zone_index < selected:
            self._document_vm.selected_zone_index = selected - 1
