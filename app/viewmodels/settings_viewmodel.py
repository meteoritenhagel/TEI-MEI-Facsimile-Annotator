from __future__ import annotations

from PySide6.QtCore import QObject, Signal, QByteArray
from PySide6.QtGui import QColor

from app.models.settings import float_range


class SettingsViewModel(QObject):
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
        unselected_zone_border_thickness: float_range[0.5, 5, 0.5] | None = None,
        unselected_zone_border_color: QColor | None = None,
        unselected_zone_fill_color: QColor | None = None,
        selected_zone_border_thickness: float_range[0.5, 5, 0.5] | None = None,
        selected_zone_border_color: QColor | None = None,
        selected_zone_fill_color: QColor | None = None,

        parent: QObject | None = None,
    ) -> None:
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
        self._unselected_zone_border_thickness = unselected_zone_border_thickness
        self._unselected_zone_border_color = unselected_zone_border_color
        self._unselected_zone_fill_color = unselected_zone_fill_color
        self._selected_zone_border_thickness = selected_zone_border_thickness
        self._selected_zone_border_color = selected_zone_border_color
        self._selected_zone_fill_color = selected_zone_fill_color

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
            self.image_settings_changed.emit()

    @property
    def image_contrast(self) -> float_range[0., 2., 0.1]:
        return self._image_contrast

    @image_contrast.setter
    def image_contrast(self, value: float_range[0., 2., 0.1]) -> None:
        if self._image_contrast != value:
            self._image_contrast = value
            self.image_settings_changed.emit()

    @property
    def image_saturation(self) -> float_range[0., 2., 0.1]:
        return self._image_saturation

    @image_saturation.setter
    def image_saturation(self, value: float_range[0., 2., 0.1]) -> None:
        if self._image_saturation != value:
            self._image_saturation = value
            self.image_settings_changed.emit()

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
