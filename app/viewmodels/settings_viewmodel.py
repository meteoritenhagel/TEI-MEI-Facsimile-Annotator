from __future__ import annotations

from PySide6.QtCore import QObject, Signal, QByteArray, QTimer
from PySide6.QtGui import QColor

from app.constants import DEBOUNCE_INTERVAL_MS
from app.models.settings import float_range, int_range


class SettingsViewModel(QObject):
    """
    Settings viewmodel.

    Signals:
        qt_window_settings_changed (Signal()): Emitted when a Qt window setting was changed.
        image_settings_changed (Signal()): Emitted (debounced) when an image setting was changed.
        display_settings_changed (Signal()): Emitted when a display setting was changed.
    """
    qt_window_settings_changed = Signal()
    image_settings_changed = Signal()
    display_settings_changed = Signal()

    def __init__(
        self,

        geometry: QByteArray | None = None,
        windowState: QByteArray | None = None,

        image_brightness: float_range[0., 2., 0.1] | None = None,
        image_contrast: float_range[0., 2., 0.1] | None = None,
        image_saturation: float_range[0., 2., 0.1] | None = None,

        canvas_background_color: QColor | None = None,
        create_zone_border_thickness: float_range[0.5, 5, 0.5] | None = None,
        create_zone_border_color: QColor | None = None,
        create_zone_fill_color: QColor | None = None,
        create_zone_fill_opacity: int_range[0, 255] | None = None,
        unselected_zone_border_thickness: float_range[0.5, 5, 0.5] | None = None,
        unselected_zone_border_color: QColor | None = None,
        unselected_zone_fill_color: QColor | None = None,
        unselected_zone_fill_opacity: int_range[0, 255] | None = None,
        selected_zone_border_thickness: float_range[0.5, 5, 0.5] | None = None,
        selected_zone_border_color: QColor | None = None,
        selected_zone_fill_color: QColor | None = None,
        selected_zone_fill_opacity: int_range[0, 255] | None = None,

        parent: QObject | None = None,
    ) -> None:
        """
        Initializer.
        """
        super().__init__(parent)

        self._geometry = geometry
        self._windowState = windowState

        self._image_brightness = image_brightness
        self._image_contrast = image_contrast
        self._image_saturation = image_saturation

        self._canvas_background_color = canvas_background_color
        self._create_zone_border_thickness = create_zone_border_thickness
        self._create_zone_border_color = create_zone_border_color
        self._create_zone_fill_color = create_zone_fill_color
        self._create_zone_fill_opacity = create_zone_fill_opacity
        self._unselected_zone_border_thickness = unselected_zone_border_thickness
        self._unselected_zone_border_color = unselected_zone_border_color
        self._unselected_zone_fill_color = unselected_zone_fill_color
        self._unselected_zone_fill_opacity = unselected_zone_fill_opacity
        self._selected_zone_border_thickness = selected_zone_border_thickness
        self._selected_zone_border_color = selected_zone_border_color
        self._selected_zone_fill_color = selected_zone_fill_color
        self._selected_zone_fill_opacity = selected_zone_fill_opacity

        # Debounce timer for image settings
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(DEBOUNCE_INTERVAL_MS)
        self._debounce_timer.timeout.connect(self._emit_image_settings_changed)

    def _emit_image_settings_changed(self):
        self.image_settings_changed.emit()

    def _debounce_image_settings_changed(self):
        self._debounce_timer.start()

    def copy(self) -> SettingsViewModel:
        def copy_color(c):
            return QColor(c) if c is not None else None

        def copy_q_bytearray(qb):
            return QByteArray(qb.data()) if qb is not None else None

        def copy_int_range(val):
            return type(val)(val) if val is not None else None

        def copy_float_range(val):
            return type(val)(val) if val is not None else None

        return SettingsViewModel(
            geometry=copy_q_bytearray(self.geometry),
            windowState=copy_q_bytearray(self.windowState),

            image_brightness=copy_float_range(self.image_brightness),
            image_contrast=copy_float_range(self.image_contrast),
            image_saturation=copy_float_range(self.image_saturation),

            canvas_background_color=copy_color(self.canvas_background_color),
            create_zone_border_thickness=copy_float_range(self.create_zone_border_thickness),
            create_zone_border_color=copy_color(self.create_zone_border_color),
            create_zone_fill_color=copy_color(self.create_zone_fill_color),
            create_zone_fill_opacity=copy_int_range(self.create_zone_fill_opacity),
            unselected_zone_border_thickness=copy_float_range(self.unselected_zone_border_thickness),
            unselected_zone_border_color=copy_color(self.unselected_zone_border_color),
            unselected_zone_fill_color=copy_color(self.unselected_zone_fill_color),
            unselected_zone_fill_opacity=copy_int_range(self.unselected_zone_fill_opacity),
            selected_zone_border_thickness=copy_float_range(self.selected_zone_border_thickness),
            selected_zone_border_color=copy_color(self.selected_zone_border_color),
            selected_zone_fill_color=copy_color(self.selected_zone_fill_color),
            selected_zone_fill_opacity=copy_int_range(self.selected_zone_fill_opacity),
            parent=None
        )

    # --- Geometry ---
    @property
    def geometry(self) -> QByteArray:
        return self._geometry

    @geometry.setter
    def geometry(self, value: QByteArray) -> None:
        if self._geometry != value:
            self._geometry = value
            self.qt_window_settings_changed.emit()

    @property
    def windowState(self) -> QByteArray:
        return self._windowState

    @windowState.setter
    def windowState(self, value: QByteArray) -> None:
        if self._windowState != value:
            self._windowState = value
            self.qt_window_settings_changed.emit()

    # --- Image Settings ---
    @property
    def image_brightness(self) -> float_range[0., 2., 0.1]:
        return self._image_brightness

    @image_brightness.setter
    def image_brightness(self, value: float_range[0., 2., 0.1]) -> None:
        if self._image_brightness != value:
            self._image_brightness = value
            self._debounce_image_settings_changed()

    @property
    def image_contrast(self) -> float_range[0., 2., 0.1]:
        return self._image_contrast

    @image_contrast.setter
    def image_contrast(self, value: float_range[0., 2., 0.1]) -> None:
        if self._image_contrast != value:
            self._image_contrast = value
            self._debounce_image_settings_changed()

    @property
    def image_saturation(self) -> float_range[0., 2., 0.1]:
        return self._image_saturation

    @image_saturation.setter
    def image_saturation(self, value: float_range[0., 2., 0.1]) -> None:
        if self._image_saturation != value:
            self._image_saturation = value
            self._debounce_image_settings_changed()

    # --- Display Settings ---
    @property
    def canvas_background_color(self) -> QColor:
        return self._canvas_background_color

    @canvas_background_color.setter
    def canvas_background_color(self, value: QColor) -> None:
        if self._canvas_background_color != value:
            self._canvas_background_color = value
            self.display_settings_changed.emit()

    @property
    def create_zone_border_thickness(self) -> float_range[0.5, 5, 0.5]:
        return self._create_zone_border_thickness

    @create_zone_border_thickness.setter
    def create_zone_border_thickness(self, value: float_range[0.5, 5, 0.5]) -> None:
        if self._create_zone_border_thickness != value:
            self._create_zone_border_thickness = value
            self.display_settings_changed.emit()

    @property
    def create_zone_border_color(self) -> QColor:
        return self._create_zone_border_color

    @create_zone_border_color.setter
    def create_zone_border_color(self, value: QColor) -> None:
        if self._create_zone_border_color != value:
            self._create_zone_border_color = value
            self.display_settings_changed.emit()

    @property
    def create_zone_fill_color(self) -> QColor:
        return self._create_zone_fill_color

    @create_zone_fill_color.setter
    def create_zone_fill_color(self, value: QColor) -> None:
        if self._create_zone_fill_color != value:
            self._create_zone_fill_color = value
            self.display_settings_changed.emit()

    @property
    def create_zone_fill_opacity(self) -> int_range[0, 255]:
        return self._create_zone_fill_opacity

    @create_zone_fill_opacity.setter
    def create_zone_fill_opacity(self, value: int_range[0, 255]) -> None:
        if self._create_zone_fill_opacity != value:
            self._create_zone_fill_opacity = value
            self.display_settings_changed.emit()

    @property
    def unselected_zone_border_thickness(self) -> float_range[0.5, 5, 0.5]:
        return self._unselected_zone_border_thickness

    @unselected_zone_border_thickness.setter
    def unselected_zone_border_thickness(self, value: float_range[0.5, 5, 0.5]) -> None:
        if self._unselected_zone_border_thickness != value:
            self._unselected_zone_border_thickness = value
            self.display_settings_changed.emit()

    @property
    def unselected_zone_border_color(self) -> QColor:
        return self._unselected_zone_border_color

    @unselected_zone_border_color.setter
    def unselected_zone_border_color(self, value: QColor) -> None:
        if self._unselected_zone_border_color != value:
            self._unselected_zone_border_color = value
            self.display_settings_changed.emit()

    @property
    def unselected_zone_fill_color(self) -> QColor:
        return self._unselected_zone_fill_color

    @unselected_zone_fill_color.setter
    def unselected_zone_fill_color(self, value: QColor) -> None:
        if self._unselected_zone_fill_color != value:
            self._unselected_zone_fill_color = value
            self.display_settings_changed.emit()

    @property
    def unselected_zone_fill_opacity(self) -> int_range[0, 255]:
        return self._unselected_zone_fill_opacity

    @unselected_zone_fill_opacity.setter
    def unselected_zone_fill_opacity(self, value: int_range[0, 255]) -> None:
        if self._unselected_zone_fill_opacity != value:
            self._unselected_zone_fill_opacity = value
            self.display_settings_changed.emit()

    @property
    def selected_zone_border_thickness(self) -> float_range[0.5, 5, 0.5]:
        return self._selected_zone_border_thickness

    @selected_zone_border_thickness.setter
    def selected_zone_border_thickness(self, value: float_range[0.5, 5, 0.5]) -> None:
        if self._selected_zone_border_thickness != value:
            self._selected_zone_border_thickness = value
            self.display_settings_changed.emit()

    @property
    def selected_zone_border_color(self) -> QColor:
        return self._selected_zone_border_color

    @selected_zone_border_color.setter
    def selected_zone_border_color(self, value: QColor) -> None:
        if self._selected_zone_border_color != value:
            self._selected_zone_border_color = value
            self.display_settings_changed.emit()

    @property
    def selected_zone_fill_color(self) -> QColor:
        return self._selected_zone_fill_color

    @selected_zone_fill_color.setter
    def selected_zone_fill_color(self, value: QColor) -> None:
        if self._selected_zone_fill_color != value:
            self._selected_zone_fill_color = value
            self.display_settings_changed.emit()

    @property
    def selected_zone_fill_opacity(self) -> int_range[0, 255]:
        return self._selected_zone_fill_opacity

    @selected_zone_fill_opacity.setter
    def selected_zone_fill_opacity(self, value: int_range[0, 255]) -> None:
        if self._selected_zone_fill_opacity != value:
            self._selected_zone_fill_opacity = value
            self.display_settings_changed.emit()
