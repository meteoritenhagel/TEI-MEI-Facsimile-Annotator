from __future__ import annotations

from PySide6.QtCore import QSettings, QByteArray

from app.constants import ORGANIZATION_NAME, APPLICATION_NAME


class SettingsRepository:
    """
    Repository for saving/loading settings data to/from QSettings.

    Methods:
        load (str): Load settings with settings key from QSettings.
        save (str, value): Save settings with settings key to QSettings.

    """
    _q_settings: QSettings = QSettings(ORGANIZATION_NAME, APPLICATION_NAME)

    def load(self, key: str) -> object:
        """
        Load settings with settings key from QSettings.

        :param key: Unique setting identifier.
        :return: Object associated with setting.
        """
        try:
            return self._q_settings.value(key)
        except EOFError:
            return None

    def save(self, key: str, value: QByteArray | str | float | int) -> None:
        """
        Save settings with settings key to QSettings.

        :param key: Unique setting identifier.
        :param value: Object to save in setting.
        :raise TypeError: In case the type is not a basic type.
        """
        # Only these basic types are serialized correctly!
        if isinstance(value, QByteArray) or isinstance(value, str) or isinstance(value, float) or isinstance(value, int):
            self._q_settings.setValue(key, value)
        else:
            raise TypeError(f"Value must be QByteArray, str, float, or int. Received: {value} ({type(value)})")
