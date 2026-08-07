from __future__ import annotations

from PySide6.QtCore import QSettings, QByteArray

from app.constants import ORGANIZATION_NAME, APPLICATION_NAME


class SettingsRepository:
    _q_settings: QSettings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

    def load(self, key: str) -> object:
        try:
            return self._q_settings.value(key)
        except EOFError:
            return None

    def save(self, key: str, value: QByteArray | str | float | int) -> None:
        # Only these basic types are serialized correctly!
        if isinstance(value, QByteArray) or isinstance(value, str) or isinstance(value, float) or isinstance(value, int):
            self._q_settings.setValue(key, value)
        else:
            raise TypeError(f"Value must be QByteArray, str, float, or int. Received: {value} ({type(value)})")
