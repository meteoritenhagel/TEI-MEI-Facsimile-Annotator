from __future__ import annotations

import dataclasses
import typing

from PySide6.QtCore import QObject
from PySide6.QtGui import QColor

from app.models.settings import QtWindowSettings, ImageSettings, DisplaySettings
from app.repositories.settings_repository import SettingsRepository
from app.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsService(QObject):
    """
    Settings service is a service class for manipulation of SettingsViewModel instances.

    Properties:
        SETTINGS_KEYS (list[str]): All unique settings identifiers are registered here.
        settings_types (dict[str, type]): Maps each unique settings identifier to its value type.
        settings_defaults (dict[str, object]): Maps each unique settings identifier to its default value.

    Methods:
        load_settings: Load all settings from the settings repository into the current class instance.
        save_settings: Save all settings from the current class instance into the settings repository.
        create_temporary_settings_viewmodel: Create a deep copy of the associated SettingsViewModel instance.
        apply_temporary_settings_viewmodel (SettingsViewModel): Applies the state of a provided SettingsViewModel
                to the current class instance.
        load_settings_to_temporary_viewmodel (SettingsViewModel, bool): Loads either all the settings from the
                current instance into the provided SettingsViewModel, or loads all default setting values into
                the provided SettingsViewModel.

    Private Methods:
        _load_setting (str, bool): Loads the default setting or the setting with the provided settings key from the
                repository into the current class instance.
        _save_setting (str): Saves the current instance's setting with the provided settings key into the
                settings repository.
    """

    # Register new settings here
    SETTINGS_KEYS: list[str] = [
        "geometry",
        "windowState",
        "image_brightness",
        "image_contrast",
        "image_saturation",
        "canvas_background_color",
        "create_zone_border_thickness",
        "create_zone_border_color",
        "create_zone_fill_color",
        "create_zone_fill_opacity",
        "unselected_zone_border_thickness",
        "unselected_zone_border_color",
        "unselected_zone_fill_color",
        "unselected_zone_fill_opacity",
        "selected_zone_border_thickness",
        "selected_zone_border_color",
        "selected_zone_fill_color",
        "selected_zone_fill_opacity",
    ]

    def __init__(
        self,
        repository: SettingsRepository,
        settings_viewmodel: SettingsViewModel,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._repository = repository
        self._settings_vm = settings_viewmodel

        settings_classes = (
            QtWindowSettings,
            ImageSettings,
            DisplaySettings
        )

        # Set settings types
        settings_types = {}
        for cls in settings_classes:
            settings_types.update(typing.get_type_hints(cls))
        self.settings_types = settings_types

        # Set settings default values
        settings_defaults = {}
        for cls in settings_classes:
            settings_defaults.update(dataclasses.asdict(cls()))
        self.settings_defaults = settings_defaults

    def load_settings(self) -> None:
        """
        Load all settings from the settings repository into the current class instance.
        :return:
        """
        self.load_settings_to_temporary_viewmodel(self._settings_vm, load_default_values=False)

    def save_settings(self) -> None:
        """
        Load all settings from the current class instance into the settings repository.
        """
        for key in self.SETTINGS_KEYS:
            self._save_setting(key, getattr(self._settings_vm, key))

    def create_temporary_settings_viewmodel(self) -> SettingsViewModel:
        """
        Create a deep copy of the associated SettingsViewModel instance.
        :return: SettingsViewModel deep copy.
        """
        return self._settings_vm.copy()

    def apply_temporary_settings_viewmodel(self, temporary_settings_viewmodel: SettingsViewModel) -> None:
        """
        Applies the state of a provided SettingsViewModel to the current class instance.
        :param temporary_settings_viewmodel: SettingsViewModel instance from which the state should be applied.
        """
        for key in self.SETTINGS_KEYS:
            setattr(self._settings_vm, key, getattr(temporary_settings_viewmodel, key))

    def load_settings_to_temporary_viewmodel(
            self, settings_vm: SettingsViewModel, load_default_values: bool = False) -> None:
        """
        Loads either all the settings from the current instance's SettingsViewModel into the provided SettingsViewModel,
        or loads all default setting values into the provided SettingsViewModel.
        :param settings_vm: SettingsViewModel instance to which the state should be applied.
        :param load_default_values: If True, load the default values, otherwise, load the current instance's values.
        """
        for key in self.SETTINGS_KEYS:
            value = self._load_setting(key, load_default_values)
            setattr(settings_vm, key, value)

    def _load_setting(self, settings_key: str, load_default_values: bool = False) -> object:
        """
        Loads the default setting or the setting with the provided settings key from the repository into the current
        class instance.

        :param settings_key: Unique setting identifier.
        :param load_default_values: If True, load the default values. Otherwise, load from the settings repository.
        :return: Value of setting.
        """
        setting_type = self.settings_types[settings_key]
        value = self._repository.load(settings_key)

        if value is None or load_default_values:  # if unset, return default value
            return self.settings_defaults[settings_key]

        if issubclass(setting_type, QColor):
            return QColor(value)
        elif issubclass(setting_type, bool):
            return value in [True, 'true', 'True', 1, '1']
        elif issubclass(setting_type, int) or issubclass(setting_type, float):
            return setting_type(value)

        return value

    def _save_setting(self, settings_key: str, value: object) -> None:
        """
        Saves the current instance's setting with the provided settings key into the settings repository.

        :param settings_key: Unique setting identifier.
        :param value: Value of setting.
        """
        setting_type = self.settings_types[settings_key]

        if issubclass(setting_type, QColor):
            value = value.name(QColor.NameFormat.HexArgb)
        elif issubclass(setting_type, int):  # Our custom int_range type is not pickable
            value = int(value)
        elif issubclass(setting_type, float):  # Our custom float_range type is not pickable
            value = float(value)

        self._repository.save(settings_key, value)
