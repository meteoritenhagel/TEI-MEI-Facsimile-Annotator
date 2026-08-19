from abc import ABC, abstractmethod
from pathlib import Path
from typing import Literal

from PySide6.QtCore import Signal

from app.models.document import Zone, Surface
from app.services.mapping_service import zone_to_viewmodel, surface_to_viewmodel
from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.surface_viewmodel import SurfaceViewModel
from app.viewmodels.zone_viewmodel import ZoneViewModel


class Command(ABC):
    """
    Encapsulates an action that can be done/undone.
    """

    @abstractmethod
    def name(self) -> str:
        """
        Returns the name of the command.
        """
        ...

    @abstractmethod
    def do(self):
        """
        Execute the command.
        """
        ...

    @abstractmethod
    def undo(self):
        """
        Undo the command.
        :return:
        """
        ...


class AddZoneCommand(Command):
    """
    Adds a zone to the document viewmodel.
    """

    def __init__(self, document_vm: DocumentViewModel, surface_index: int, zone: Zone):
        """
        :param document_vm: Document viewmodel.
        :param surface_index: Surface the new zone is associated with.
        :param zone: Zone to add.
        """
        self.document_vm = document_vm
        self.surface_index = surface_index
        self.zone = zone
        self.zone_vm = None  # Will hold the created ZoneViewModel

        if not 0 <= surface_index < len(self.document_vm.surfaces):
            raise IndexError(f"Surface index out of range: {surface_index}")

    def name(self):
        return "Add Zone"

    def do(self):
        surface_vm: SurfaceViewModel = self.document_vm.surfaces[self.surface_index]
        self.zone_vm = ZoneViewModel(parent=surface_vm)
        zone_to_viewmodel(self.zone, self.zone_vm)
        surface_vm.zones = (*surface_vm.zones, self.zone_vm)
        self.document_vm.dirty = True

    def undo(self):
        surface_vm: SurfaceViewModel = self.document_vm.surfaces[self.surface_index]
        # Remove the last zone (the one we just added)
        if surface_vm.zones and surface_vm.zones[-1] is self.zone_vm:
            surface_vm.zones = surface_vm.zones[:-1]
            self.document_vm.dirty = True


class RemoveZoneCommand(Command):
    """
    Removes a zone from the document viewmodel.
    """

    def __init__(self, document_vm: DocumentViewModel, surface_index: int, zone_index: int):
        """
        :param document_vm: Document viewmodel.
        :param surface_index: Index of surface which contains the zone to be removed.
        :param zone_index: Index of zone to be removed.
        """
        self.document_vm = document_vm
        self.surface_index = surface_index
        self.zone_index = zone_index

        self._removed_zone_vm = None # Contains the removed zone for later undo

        if not 0 <= surface_index < len(self.document_vm.surfaces):
            raise IndexError(f"Surface index out of range: {surface_index}")

        if not 0 <= zone_index < len(self.document_vm.surfaces[surface_index].zones):
            raise IndexError(f"Surface index out of range: {zone_index}")

    def name(self):
        return "Remove Zone"

    def do(self):
        surface_vm: SurfaceViewModel = self.document_vm.surfaces[self.surface_index]

        self._removed_zone_vm = surface_vm.zones[self.zone_index]  # Save for undo

        surface_vm.zones = (
            *surface_vm.zones[:self.zone_index],
            *surface_vm.zones[self.zone_index + 1:],
        )
        self.document_vm.dirty = True
        self._adjust_selected_zone_index_do()

    def undo(self):
        surface_vm: SurfaceViewModel = self.document_vm.surfaces[self.surface_index]
        zones = list(surface_vm.zones)
        zones.insert(self.zone_index, self._removed_zone_vm)
        surface_vm.zones = tuple(zones)
        self.document_vm.dirty = True
        self._adjust_selected_zone_index_undo()

    def _adjust_selected_zone_index_do(self):
        if self.surface_index != self.document_vm.current_page_index:
            return
        selected = self.document_vm.selected_zone_index
        if selected is None:
            return
        if selected == self.zone_index:
            self.document_vm.selected_zone_index = None
        elif self.zone_index < selected:
            self.document_vm.selected_zone_index = selected - 1

    def _adjust_selected_zone_index_undo(self):
        if self.surface_index != self.document_vm.current_page_index:
            return
        selected = self.document_vm.selected_zone_index
        if selected is None:
            return
        elif self.zone_index < selected:
            self.document_vm.selected_zone_index = selected + 1

class UpdateZoneRectCommand(Command):
    """
    Updates a specific zone's coordinates in the document viewmodel.
    """

    def __init__(self, document_vm: DocumentViewModel,
        surface_index: int,
        zone_index: int,
        ulx: int,
        uly: int,
        lrx: int,
        lry: int
    ):
        """
        :param document_vm: Document viewmodel.
        :param surface_index: Surface index of the zone to be updated.
        :param zone_index: Zone index of the zone to be updated.
        :param ulx: Upper left x coordinate.
        :param uly: Upper left y coordinate.
        :param lrx: Lower right x coordinate.
        :param lry: Lower right y coordinate.
        """
        self.document_vm = document_vm
        self.surface_index = surface_index
        self.zone_index = zone_index
        self.new_coordinates = (ulx, uly, lrx, lry)
        self.old_coordinates = None  # Holds the old zone coordinates for undo

        if not 0 <= surface_index < len(self.document_vm.surfaces):
            raise IndexError(f"Surface index out of range: {surface_index}")

        if not 0 <= zone_index < len(self.document_vm.surfaces[surface_index].zones):
            raise IndexError(f"Surface index out of range: {zone_index}")

    def name(self):
        return "Change Zone Coords"

    def do(self):
        surface_vm: SurfaceViewModel = self.document_vm.surfaces[self.surface_index]
        zone_vm: ZoneViewModel = surface_vm.zones[self.zone_index]
        self.old_coordinates = (zone_vm.ulx, zone_vm.uly, zone_vm.lrx, zone_vm.lry)
        zone_vm.set_rect(*self.new_coordinates)
        self.document_vm.dirty = True

    def undo(self):
        surface_vm: SurfaceViewModel = self.document_vm.surfaces[self.surface_index]
        zone_vm: ZoneViewModel = surface_vm.zones[self.zone_index]
        zone_vm.set_rect(*self.old_coordinates)
        self.document_vm.dirty = True


class SetDocumentTypeCommand(Command):
    """
    Sets the document viewmodel's document type.
    """

    def __init__(self, document_vm: DocumentViewModel, doc_type: Literal["TEI", "MEI"]):
        """
        :param document_vm: Document viewmodel.
        :param doc_type: Document type.
        """
        self.document_vm = document_vm
        self.new_doc_type = doc_type
        self.old_doc_type = None  # Will hold the old document type for undo

    def name(self):
        return "Change Document Type"

    def do(self):
        self.old_doc_type = self.document_vm.document_type
        if self.new_doc_type == self.old_doc_type:
            return
        self.document_vm.document_type = self.new_doc_type
        self.document_vm.dirty = True

    def undo(self):
        if self.new_doc_type == self.old_doc_type:
            return
        self.document_vm.document_type = self.old_doc_type
        self.document_vm.dirty = True


class GoToPageCommand(Command):
    """
    Navigates to the document page of specified index.
    """

    def __init__(self, document_vm: DocumentViewModel, page_index: int):
        """
        :param document_vm: Document viewmodel.
        :param page_index: Page index.
        """
        self.document_vm = document_vm
        self.new_page_index = page_index
        self.old_page_index = None  # Will hold the old page index for undo

        if not 0 <= page_index < len(self.document_vm.surfaces):
            raise IndexError(f"Page index out of range: {page_index}")

    def name(self):
        return "Go to Page"

    def do(self):
        self.old_page_index = self.document_vm.current_page_index
        if self.new_page_index == self.old_page_index:
            return
        self.document_vm.current_page_index = self.new_page_index
        self.document_vm.selected_zone_index = None

    def undo(self):
        if self.new_page_index == self.old_page_index:
            return
        self.document_vm.current_page_index = self.old_page_index
        self.document_vm.selected_zone_index = None


class AddSurfacesCommand(Command):
    """
    Adds surfaces created from image files to the document.
    """

    def __init__(self,
                 document_vm: DocumentViewModel,
                 paths: list[Path],
                 add_surface_succeeded: Signal,
                 add_surface_failed: Signal
        ):
        """
        :param document_vm: Document viewmodel.
        :param paths: List of paths to images.
        :param add_surface_succeeded: Signal that is emitted if adding the surfaces succeeded.
        :param add_surface_failed: Signal that is emitted if adding the surfaces failed.
        """
        self.document_vm = document_vm
        self.paths = paths
        self.add_surface_succeeded = add_surface_succeeded
        self.add_surface_failed = add_surface_failed

        self.old_current_page_index = None
        self.surfaces = self.document_vm.surfaces

        try:
            for path in self.paths:
                image = path.read_bytes()
                surface = Surface(image=image, image_path=str(path), zones=())
                surface_vm = SurfaceViewModel(parent=self.document_vm)
                surface_to_viewmodel(surface, surface_vm)
                self.surfaces = (*self.surfaces, surface_vm)
        except Exception as error:
            self.add_surface_failed.emit(error)

    def name(self):
        return "Add Pages"

    def do(self):
        self.old_current_page_index = self.document_vm.current_page_index
        self.document_vm.surfaces = self.surfaces
        self.document_vm.current_page_index = len(self.surfaces) - len(self.paths)
        self.document_vm.selected_zone_index = None
        self.document_vm.dirty = True
        self.add_surface_succeeded.emit()

    def undo(self):
        self.document_vm.surfaces = self.document_vm.surfaces[:len(self.surfaces)-len(self.paths)]
        self.document_vm.current_page_index = self.old_current_page_index
        self.document_vm.selected_zone_index = None
        self.document_vm.dirty = True


class RemoveSurfaceCommand(Command):
    """
    Removes a surface from the document.
    """

    def __init__(self, document_vm: DocumentViewModel, surface_index: int):
        """
        :param document_vm: Document viewmodel.
        :param surface_index: Index to remove.
        """
        self.document_vm = document_vm
        self.surface_index = surface_index

        self.deleted_surface_index = None
        self.deleted_surface = None

        self.surfaces = self.document_vm.surfaces

        if not 0 <= surface_index < len(self.document_vm.surfaces):
            raise IndexError(f"Surface index out of range: {surface_index}")

    def name(self):
        return "Remove Page"

    def do(self):
        self.deleted_surface_index = self.document_vm.current_page_index
        self.deleted_surface = self.document_vm.surfaces[self.surface_index]

        self.document_vm.surfaces = (
            *self.document_vm.surfaces[:self.surface_index],
            *self.document_vm.surfaces[self.surface_index + 1:],
        )
        if not self.document_vm.surfaces:
            new_current_page_index = 0
        elif self.deleted_surface_index > self.surface_index:
            new_current_page_index = self.deleted_surface_index - 1
        elif self.deleted_surface_index >= len(self.document_vm.surfaces):
            new_current_page_index = len(self.document_vm.surfaces) - 1
        else:
            new_current_page_index = self.deleted_surface_index
        self.document_vm.current_page_index = new_current_page_index
        if self.surface_index <= self.deleted_surface_index:
            self.document_vm.selected_zone_index = None
        self.document_vm.dirty = True

    def undo(self):
        self.document_vm.surfaces = (
            *self.document_vm.surfaces[:self.deleted_surface_index],
            self.deleted_surface,
            *self.document_vm.surfaces[self.deleted_surface_index:]
        )
        self.document_vm.current_page_index = self.deleted_surface_index
        self.document_vm.dirty = True