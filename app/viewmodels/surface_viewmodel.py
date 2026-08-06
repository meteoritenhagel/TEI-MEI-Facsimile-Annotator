from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from app.viewmodels.zone_viewmodel import ZoneViewModel


class SurfaceViewModel(QObject):
    image_changed = Signal(bytes)
    image_path_changed = Signal(str)
    zones_changed = Signal()

    def __init__(
        self,
        image: bytes = b"",
        image_path: str = "",
        zones: tuple[ZoneViewModel, ...] = (),
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._image = image
        self._image_path = image_path
        self._zones = zones

    @property
    def image(self) -> bytes:
        return self._image

    @image.setter
    def image(self, value: bytes) -> None:
        if value == self._image:
            return
        self._image = value
        self.image_changed.emit(self._image)

    @property
    def image_path(self) -> str:
        return self._image_path

    @image_path.setter
    def image_path(self, value: str) -> None:
        if value == self._image_path:
            return
        self._image_path = value
        self.image_path_changed.emit(self._image_path)

    @property
    def zones(self) -> tuple[ZoneViewModel, ...]:
        return self._zones

    @zones.setter
    def zones(self, value: tuple[ZoneViewModel, ...]) -> None:
        if value == self._zones:
            return
        self._zones = value
        self.zones_changed.emit()
