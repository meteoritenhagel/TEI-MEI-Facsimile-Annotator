import copy
import dataclasses
import threading
from PIL import ImageEnhance, Image
from PySide6.QtCore import Signal, QObject, QTimer, Slot
from PySide6.QtGui import QColor
from pyqttoast import ToastPreset

from .cyclic_access import CyclicCounter
from .graphics_item import GraphicsItem, PolygonItem
from .logger import LoggerSingleton
from .seriazable_image import SerializableImage
from .settings import Settings, settings_get
from .spatial_database import SpatialDatabase
from .undo_redo import UndoRedoList


class Rectangle:
    def __init__(self, tpl: tuple[int, int, int, int]):
        self.ulx = tpl[0]
        self.uly = tpl[1]
        self.lrx = tpl[2]
        self.lry = tpl[3]

    def to_polygon(self) -> list[tuple[int, int]]:
        return [
            (self.ulx, self.uly),
            (self.lrx, self.uly),
            (self.lrx, self.lry),
            (self.ulx, self.lry),
        ]


class ObjectState:
    def __init__(self, objects: list[Rectangle] = None, selection: Rectangle = None):
        self.objects = objects if objects is not None else []
        self.selection = selection
        self.has_unsaved_changes: bool = False

    def append(self, obj: tuple):
        self.objects.append(Rectangle(obj))

    def construct_graphics(self):
        graphics = []
        for obj in self.objects:
            graphics.append(PolygonItem(obj.to_polygon(), QColor(0, 0, 0), filled=False))
        return graphics

    def to_dict(self):
        pass

    @classmethod
    def from_dict(cls, d):
        pass

    def copy(self):
        return ObjectState(copy.copy(self.objects), self.selection)


class ObjectHandler:
    def __init__(self, objects_per_page: list[ObjectState] | None = None):
        self._objects_per_page = objects_per_page if objects_per_page is not None else []
        self._buffered_serialization = None

    def __len__(self):
        return len(self._objects_per_page)

    def __iter__(self):
        return iter(self._objects_per_page)

    def to_dict(self):
        # We do not need to construct everything everytime.
        # If there were no changes, we can just return the buffer.
        # If the buffer is old and some object states have changed,
        # use the buffered values for the others and only construct
        # the serializations for those needed.

        objects_to_construct = range(len(self._objects_per_page))
        serialization = [None] * len(self)

        if self._buffered_serialization is not None:
            if not self.has_unsaved_changes:
                return self._buffered_serialization
            else:
                objects_to_construct = [idx for idx, object_state in enumerate(self._objects_per_page) if
                                           object_state.has_unsaved_changes]

        for state_idx in range(len(self._objects_per_page)):
            object_state = self._objects_per_page[state_idx]

            if state_idx in objects_to_construct:  # construct the connector serializations that are needed
                serialization[state_idx] = object_state.to_dict()
            else:  # for pages that have not changed, take the buffer
                serialization[state_idx] = self._buffered_serialization[state_idx]

        self._buffered_serialization = serialization  # update the buffer
        return serialization

    def from_dict(self, l: list[dict]):
        self._objects_per_page = []
        for entry in l:
            self._objects_per_page.append(ObjectState.from_dict(entry))

    def get_state(self, state_idx: int):
        return self._objects_per_page[state_idx]

    def set_state(self, state_idx: int, state: ObjectState):
        self._objects_per_page[state_idx] = state

    def construct_graphics(self, index: int):
        return self._objects_per_page[index].construct_graphics()

    def append(self, state_idx: int, obj: object):
        self._objects_per_page[state_idx].append(obj)

    def reset(self):
        self._objects_per_page = []
        self._buffered_serialization = None

    @property
    def has_unsaved_changes(self):
        has_changes = False
        for object_state in self._objects_per_page:
            has_changes = has_changes or object_state.has_unsaved_changes
        return has_changes

    @has_unsaved_changes.setter
    def has_unsaved_changes(self, value: bool):
        for object_state in self._objects_per_page:
            object_state.has_unsaved_changes = value


class _ProgramState(QObject):
    """
    Class _ProgramState stores the program's current state, meaning everything that affects
    what should be displayed in the widgets, the results of user interactions, etc.

    Properties:
        data_changed (Signal): Signal that is emitted when data has been changed in the program state.
                               NEVER emit when not in the main loop! Use _schedule_emit instead.
        show_toast (Signal[str, str, ToastPreset]): Signal that is emitted when a toast should be displayed.
                                                    The arguments are title, message, and ToastPreset.
        _request_debounce (Signal): Signal that is emitted when the debouncing is requested.

        has_unsaved_changes (bool): If True, the program state has unsaved changes.
        icon (QIcon | None): Stores the application icon.
        path_to_images (str | None): Stores the path to the image file.
        save_file_path (str | None): Stores the path to which file the user has saved the project.
        object_handler (TODO):
        project_images (SerializableImage | None): Stores the project image data.
        graphics_image (Image.Image | None): The image of the manuscript that is to be drawn in the view.
        draw_word_gloss_objects (list[GraphicsItem] | None): List of words and glosses on the current METSPage in
                                                             drawable form.
        draw_connection_objects (list[GraphicsItem] | None): List of gloss connections on the current METSPage in
                                                             drawable form.
        spatial_database (SpatialDatabase): Database for quick lookup of objects in the scene based on their
                                            coordinates. Used for selecting the right object when clicking on
                                            it in the ImageGraphicsView widget.
        current_page_index (int | None): Read-only. The index of the currently selected page.
        number_of_pages (int | None): Read-only. Returns the currently available number of pages.
        page_counter_text (str): Read-only. The text representation of the currently selected page index, e.g., '1 / 9'.
        unconnected_gloss_lines (CyclicList): Read-only. Contains all gloss line ids that are not connected.

    Methods:
        reset: Resets all member variables to None and frees the memory.
        to_dict: Returns a dictionary of the most important features for saving.
        from_dict: Resets the _ProgramState class with the values loaded from a save file dictionary.
        construct_view: Updates the graphics for the currently selected page for display.
                                         Call from separate thread!
        has_undo_actions: Return True if there are actions that can be undone.
        has_redo_actions: Return True if there are actions that can be redone.
        undo: If possible, undo the last action.
        redo: If possible, redo the last action.

    Private Attributes:
        _debounce_timer (QTimer): Timer for debouncing change signals, i.e., the signal is only emitted after
                                  a certain time period to prevent too frequent GUI updates.
        _pending_changes (bool): Is set to True if a signal must be emitted after the debounce timer has timed out.

    Private Methods:
        _start_debounce_timer: Starts the debounce timer (on timeout, the signal data_changed may be emitted).
        _emit_data_changed: If pending changes are present, the data_changed signal is emitted with a summary of
                            changes.
        _schedule_emit (str): Adds a program state change (with change name provided) to the list of _pending_changes.
    """
    data_changed = Signal(str)
    show_toast = Signal(str, str, ToastPreset)
    _request_debounce = Signal()

    def __init__(self):
        """
        Initializes an instance of the _ProgramState class.
        """
        super().__init__()

        self._request_debounce.connect(self._start_debounce_timer)

        self.icon = None

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_data_changed)
        self._pending_changes = set()

        self.path_to_image: str | None = None
        self.save_file_path: str | None = None

        self._project_images: list[Image.Image] | None = None

        self._page_counter: CyclicCounter | None = None

        self._currently_selected_object: object | None = None
        self._graphics_image: SerializableImage | None = None
        self._graphics_objects: list[GraphicsItem] | None = None
        self._spatial_database: SpatialDatabase | None = None

        self._object_handler = ObjectHandler()

        self._undo_redo_list: UndoRedoList = UndoRedoList[ObjectState]()

    def __repr__(self):
        return (f"ProgramState(\n"
                f"   Path to Project Image: {self.path_to_image}\n"
                f")"
                )

    def reset(self):
        """
        Resets all member variables to None and frees the memory.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.reset()")
        self.path_to_image = None

        del self._currently_selected_object
        self._currently_selected_object = None

        del self._graphics_image
        self._graphics_image = None

        del self._graphics_objects
        self._graphics_objects = None

        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(ObjectState())

        self._object_handler.reset()

    def to_dict(self) -> dict:
        """
        Returns a dictionary of the most important features for saving.
        :return: Dictionary of the most important _ProgramState features.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.to_dict(...)")

        return {
            "image": self.graphics_image.to_bytestring(),
            "objects": self._object_handler.to_dict(),
        }

    def from_dict(self, dictionary: dict):
        """
        Resets the _ProgramState class with the values loaded from a save file dictionary.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.from_dict(...)")
        self.reset()

        self._graphics_image = SerializableImage.from_bytestring(dictionary["image"])
        self._object_handler.from_dict(
            dictionary["objects"],
        )

        self._currently_selected_object = None
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(
            self._object_handler.get_state(self.current_page_index)
        )
        self._schedule_emit("from_save_file")

    def go_to_next_page(self):
        """
        Sets the page counter object to the next page. Call from separate thread!
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.go_to_next_page()")
        self._page_counter.next_index()
        self.construct_view()
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(
            self._object_handler.get_state(self.current_page_index)
        )
        self._schedule_emit("go_to_next_page")

    def go_to_previous_page(self):
        """
        Sets the page counter object to the previous page. Call from separate thread!
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.go_to_previous_page()")
        self._page_counter.previous_index()
        self.construct_view()
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(
            self._object_handler.get_state(self.current_page_index)
        )
        self._schedule_emit("go_to_previous_page")

    def go_to_page(self, page_idx: int):
        """
        Sets the page counter object to the page of index page_idx. Call from separate thread!
        :param page_idx: Page index to which the page counter should be set.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.go_to_page(page_idx={page_idx})")
        self._page_counter.go_to_index(page_idx)
        self.construct_view()
        self._undo_redo_list.reset()
        self._undo_redo_list.add_element(
            self._object_handler.get_state(self.current_page_index)
        )
        self._schedule_emit("go_to_page")

    def construct_view(self):
        """
        Updates the graphics for the currently selected page for display. Call from separate thread!
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.construct_view()")

        # brightness
        enhancer = ImageEnhance.Brightness(
            self.project_images[self.current_page_index]
        )
        self._graphics_image = enhancer.enhance(settings_get(Settings.IMAGE_BRIGHTNESS))

        # contrast
        enhancer = ImageEnhance.Contrast(
            self._graphics_image
        )
        self._graphics_image = enhancer.enhance(settings_get(Settings.IMAGE_CONTRAST))

        # brightness
        enhancer = ImageEnhance.Color(
            self._graphics_image
        )
        self._graphics_image = enhancer.enhance(settings_get(Settings.IMAGE_SATURATION))

        self._graphics_objects = self._object_handler.construct_graphics(self.current_page_index)
        self._currently_selected_object = None

        self._schedule_emit("construct_view")

    def page_index_is_valid(self, page_idx: int) -> bool:
        """
        Check if the given page index is valid.
        :param page_idx: Page index to check.
        :return: True if the page index is valid.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.page_index_is_valid(page_idx={page_idx})")
        return self._page_counter.index_is_valid(page_idx)

    def has_undo_actions(self):
        """
        Return True if there are actions that can be undone.
        :return: True if there are actions that can be undone.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.has_undo_actions()")
        return self._undo_redo_list.has_elements_before()

    def has_redo_actions(self):
        """
        Return True if there are actions that can be redone.
        :return: True if there are actions that can be redone.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.has_redo_actions()")
        return self._undo_redo_list.has_elements_after()

    def undo(self):
        """
        If possible, undo the last action.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.undo()")
        if self._undo_redo_list.has_elements_before():
            previous_state = self._undo_redo_list.previous_element()

            # update object handler
            self._object_handler.set_state(self.current_page_index, previous_state)
            # update view
            self._graphics_objects = self._object_handler.construct_graphics(self.current_page_index)
            self._schedule_emit("undo")

    def redo(self):
        """
        If possible, redo the last action.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState.redo()")
        if self._undo_redo_list.has_elements_after():
            next_state = self._undo_redo_list.next_element()

            # update object handler
            self._object_handler.set_state(self.current_page_index, next_state)
            # update view
            self._graphics_objects = self._object_handler.construct_graphics(self.current_page_index)
            self._schedule_emit("redo")

    def add_object(self, obj: object):
        self._object_handler.append(self.current_page_index, obj)
        self._graphics_objects = self._object_handler.construct_graphics(self.current_page_index)
        self._undo_redo_list.add_element(self.get_current_state())
        self._schedule_emit("add_object")

    @Slot()
    def _start_debounce_timer(self):
        """
        Starts the debounce timer (on timeout, the signal data_changed may be emitted).
        """
        LoggerSingleton().logger.log_info(f"_ProgramState._start_debounce_timer()")
        self._debounce_timer.start(100)  # 100 ms debounce interval

    @Slot()
    def _emit_data_changed(self):
        """
        If pending changes are present, the data_changed signal is emitted with a summary of changes.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState._emit_data_changed()")
        LoggerSingleton().logger.log_info(f"Emitting _ProgramState.data_changed signal {self._pending_changes}")
        if self._pending_changes:
            # Emit the signal with a summary of changes
            self.data_changed.emit(", ".join(self._pending_changes))
            self._pending_changes.clear()

    def _schedule_emit(self, property_name):
        """
        Adds a program state change (with change name provided) to the list of _pending_changes.

        :param property_name: Name of the property to be changed.
        """
        LoggerSingleton().logger.log_info(f"_ProgramState._schedule_emit(property_name={property_name})")
        self._pending_changes.add(property_name)
        self._request_debounce.emit()

    def get_current_state(self):
        if self.current_page_index is not None:
            return self._object_handler.get_state(self.current_page_index)
        else:
            return None

    def get_current_objects(self):
        if self.current_page_index is not None:
            return self._object_handler.get_state(self.current_page_index).objects
        else:
            return None

    @property
    def has_unsaved_changes(self):
        return self._object_handler.has_unsaved_changes

    @has_unsaved_changes.setter
    def has_unsaved_changes(self, value: bool):
        if self._object_handler.has_unsaved_changes != value:
            self._object_handler.has_unsaved_changes = value
            self._schedule_emit("has_unsaved_changes")

    @property
    def object_handler(self):
        return self._object_handler

    @object_handler.setter
    def object_handler(self, value):
        if self._object_handler != value:
            self._object_handler = value
            self._graphics_objects = self._object_handler.construct_graphics(self._page_counter.current_index)
            self._schedule_emit("object_handler")

    @property
    def currently_selected_object(self):
        return self.get_current_state().selection

    @currently_selected_object.setter
    def currently_selected_object(self, value):
        if self._currently_selected_object != value:
            self._currently_selected_object = value
            self._schedule_emit(f"currently_selected_object ({value})")

    @property
    def project_images(self) -> list[Image.Image]:
        return self._project_images

    @project_images.setter
    def project_images(self, value: list[Image.Image]):
        self.reset()
        self._project_images = value
        self._page_counter = CyclicCounter(len(value))
        self._object_handler = ObjectHandler([ObjectState() for _ in range(len(value))])
        self._schedule_emit("project_images")

    @property
    def graphics_image(self):
        return self._graphics_image

    @graphics_image.setter
    def graphics_image(self, value):
        if self._graphics_image != value:
            self._graphics_image = value
            self._schedule_emit("graphics_image")

    @property
    def graphics_objects(self):
        return self._graphics_objects

    @graphics_objects.setter
    def graphics_objects(self, value):
        if self._graphics_objects != value:
            self._graphics_objects = value
            self._schedule_emit("graphics_objects")

    @property
    def spatial_database(self):
        return self._spatial_database

    @spatial_database.setter
    def spatial_database(self, value):
        if self._spatial_database != value:
            self._spatial_database = value
            self._schedule_emit("spatial_database")

    @property
    def current_page_index(self):
        if self._page_counter is not None:
            return self._page_counter.current_index

    @property
    def number_of_pages(self):
        if self._page_counter is not None:
            return self._page_counter.number_of_indices

    @property
    def page_counter_text(self):
        return str(self._page_counter) if self._page_counter is not None else ""


class ProgramStateSingleton:
    """
    Class ProgramStateSingleton encapsulates the _ProgramState in a global singleton.

    Attributes:
        program_state: The program state that is held by the singleton.

    Private Attributes:
        _instance: The global instance of the singleton.
        _lock: The mechanism ensuring thread safety.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ProgramStateSingleton, cls).__new__(cls)
                    cls._instance.program_state = _ProgramState()
        return cls._instance
