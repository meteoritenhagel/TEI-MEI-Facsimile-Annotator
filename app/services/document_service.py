from __future__ import annotations

from pathlib import Path
from typing import Callable, Generic, Literal, TypeVar

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from app.models.document import Document, Surface, Zone
from app.repositories.document_repository import DocumentRepository
from app.repositories.text_repository import TextRepository
from app.services.mapping_service import (
    document_to_viewmodel,
    surface_to_viewmodel,
    viewmodel_to_document,
    zone_to_viewmodel,
)
from app.services.xml_export_service import viewmodel_to_xml
from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.surface_viewmodel import SurfaceViewModel
from app.viewmodels.zone_viewmodel import ZoneViewModel


T = TypeVar("T")


class RepoTaskSignals(QObject):
    """
    Signals for repository tasks to be run in a separate thread.

    Signals:
        finished (Signal(object)): Emitted if the task was completed successfully.
        failed (Signal(object)): Emitted if the task failed.
    """
    finished = Signal(object)
    failed = Signal(object)


class RepoTask(QRunnable, Generic[T]):
    """
    Encapsulates a repository tasks to be run in a separate thread.

    Methods:
        run: Starts the execution of the task.
    """
    def __init__(self, work: Callable[[], T]) -> None:
        """
        Initializes a task.
        :param work: Callable containing the task.
        """
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
    """
    Service class for document viewmodel manipulation.

    Signals:
        open_succeeded (Signal()): Emitted when opening a file was successful.
        save_succeeded (Signal()): Emitted when saving a file was successful.
        xml_export_succeeded (Signal()): Emitted when exporting the XML file was successful.

        open_failed (Signal(object)): Emitted when opening a file has failed.
        save_failed (Signal(object)): Emitted when saving a file has failed.
        xml_export_failed (Signal(object)): Emitted when exporting the XML file has failed.

        add_surface_succeeded (Signal()): Emitted when adding surfaces was successful.
        add_surface_failed (Signal(object)): Emitted when adding surfaces has failed.

    Methods:
        new_document: Creates a new document. Sets the viewmodel to an empty document state.
        open_file (Path): Opens the document file at the provided path.
        save_file: Saves the app state into a file on the file system.
        save_file_as (Path): Saves the app state at a specified path on the file system.
        export_xml_as (Path): Exports the app state into a minimal TEI/MEI XML file on the file system.

        go_to_page (int): Navigates to the document page of specified index.
        add_surfaces_from_images (list[Path]): Adds surfaces created from image files to the document.
        remove_surface (int): Removes a surface from the document.
        add_zone (int, Zone): Adds a zone to the document.
        remove_zone (int, int): Removes a zone from the document.
        update_zone_rect (int, int, int, int, int, int): Updates a specific zone's coordinates.
        select_zone (int): Marks a zone in the document as selected.
        set_document_type (Literal["TEI", "MEI"]): Sets the document type.
    """
    open_succeeded = Signal()
    save_succeeded = Signal()
    xml_export_succeeded = Signal()

    save_failed = Signal(object)
    open_failed = Signal(object)
    xml_export_failed = Signal(object)

    add_surface_succeeded = Signal()
    add_surface_failed = Signal(object)

    def __init__(
        self,
        document_repository: DocumentRepository,
        text_repository: TextRepository,
        document_viewmodel: DocumentViewModel,
        thread_pool: QThreadPool | None = None,
        parent: QObject | None = None,
    ) -> None:
        """
        Initialize the service class.

        :param document_repository: Document repository.
        :param text_repository: Text repository.
        :param document_viewmodel: Document viewmodel.
        :param thread_pool: Thread pool to use.
        :param parent: QObject parent.
        """
        super().__init__(parent)
        self._document_repository = document_repository
        self._text_repository = text_repository
        self._document_vm = document_viewmodel
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._active_tasks: set[RepoTask] = set()

    def new_document(self) -> None:
        """
        Creates a new document. Sets the viewmodel to an empty document state.
        """
        self._document_vm.surfaces = ()
        self._document_vm.document_type = "TEI"
        self._document_vm.current_page_index = 0
        self._document_vm.file_path = None
        self._document_vm.dirty = False
        self._document_vm.selected_zone_index = None

    def open_file(self, path: Path) -> None:
        """
        Opens the document file at the provided path.

        :param path: Path to the file to open.
        """
        task: RepoTask[Document] = RepoTask(lambda: self._document_repository.load(path))
        task.signals.finished.connect(lambda doc: self._open_finished(path, doc))
        task.signals.failed.connect(self.open_failed.emit)
        self._run_task(task)

    def save_file(self) -> bool:
        """
        Saves the app state into a file on the file system.
        :return: True if the saving operation was successful.
        """
        if self._document_vm.file_path is None:
            return False
        self._save_to_path(self._document_vm.file_path)
        return True

    def save_file_as(self, path: Path) -> None:
        """
        Saves the app state at a specified path on the file system.

        :param path: Path to save the app state to.
        """
        self._save_to_path(path)

    def export_xml_as(self, path: Path) -> None:
        """
        Exports the app state into a minimal TEI/MEI XML file on the file system.

        :param path: Path to save the TEI/MEI XML data to.
        """
        xml_text = viewmodel_to_xml(self._document_vm)
        task: RepoTask[None] = RepoTask(lambda: self._text_repository.save(path, xml_text))
        task.signals.finished.connect(lambda: self.xml_export_succeeded.emit())
        task.signals.failed.connect(self.xml_export_failed.emit)
        self._run_task(task)


    def go_to_page(self, index: int) -> None:
        """
        Navigates to the document page of specified index.

        :param index: Page index.
        """
        if not 0 <= index < len(self._document_vm.surfaces):
            return
        self._document_vm.current_page_index = index
        self._document_vm.selected_zone_index = None

    def add_surfaces_from_images(self, paths: list[Path]) -> bool:
        """
        Adds surfaces created from image files to the document.

        :param paths: List of paths to images.
        :return: True if all surfaces could be added to the document.
        """
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
        """
        Removes a surface from the document.

        :param surface_index: Index to remove.
        """
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
        """
        Adds a zone to the document.

        :param surface_index: Surface the new zone is associated with.
        :param zone: Zone to add.
        """
        surface_vm = self._surface_at(surface_index)
        zone_vm = ZoneViewModel(parent=surface_vm)
        zone_to_viewmodel(zone, zone_vm)
        surface_vm.zones = (*surface_vm.zones, zone_vm)
        self._document_vm.dirty = True

    def remove_zone(self, surface_index: int, zone_index: int) -> None:
        """
        Removes a zone from the document.

        :param surface_index: Index of surface which contains the zone to be removed.
        :param zone_index: Index of zone to be removed.
        """
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
        """
        Updates a specific zone's coordinates.

        :param surface_index: Surface index of the zone to be updated.
        :param zone_index: Zone index of the zone to be updated.
        :param ulx: Upper left x coordinate.
        :param uly: Upper left y coordinate.
        :param lrx: Lower right x coordinate.
        :param lry: Lower right y coordinate.
        """
        surface_vm = self._surface_at(surface_index)
        zone_vm = self._zone_at(surface_vm, zone_index)
        zone_vm.set_rect(ulx, uly, lrx, lry)
        self._document_vm.dirty = True

    def select_zone(self, zone_index: int | None) -> None:
        """
        Marks a zone in the document as selected.

        :param zone_index: Index of the zone to be selected.
        """
        if zone_index is not None:
            surface_vm = self._current_surface()
            self._zone_at(surface_vm, zone_index)
        self._document_vm.selected_zone_index = zone_index

    def set_document_type(self, doc_type: Literal["TEI", "MEI"]) -> None:
        """
        Sets the document type.

        :param doc_type: Document type.
        """
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
        task: RepoTask[None] = RepoTask(lambda: self._document_repository.save(path, doc))
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
