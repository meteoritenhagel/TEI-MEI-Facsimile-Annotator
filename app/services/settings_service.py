from __future__ import annotations

import dataclasses
import typing

from PySide6.QtCore import QObject
from PySide6.QtGui import QColor

from app.models.settings import QtWindowSettings, ImageSettings, DisplaySettings
from app.repositories.settings_repository import SettingsRepository
from app.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsService(QObject):
    # TODO: Add new settings here
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
        "unselected_zone_border_thickness",
        "unselected_zone_border_color",
        "unselected_zone_fill_color",
        "selected_zone_border_thickness",
        "selected_zone_border_color",
        "selected_zone_fill_color",
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

    def create_temporary_settings_viewmodel(self) -> SettingsViewModel:
        return self._settings_vm.copy()

    def apply_temporary_settings_viewmodel(self, temporary_settings_viewmodel: SettingsViewModel) -> None:
        for key in self.SETTINGS_KEYS:
            setattr(self._settings_vm, key, getattr(temporary_settings_viewmodel, key))

    def load_settings(self) -> None:
        self.load_settings_to_viewmodel(self._settings_vm, load_default_values=False)

    def save_settings(self) -> None:
        for key in self.SETTINGS_KEYS:
            self._save_setting(key, getattr(self._settings_vm, key))

    def load_settings_to_viewmodel(self, settings_vm: SettingsViewModel, load_default_values: bool = False) -> None:
        for key in self.SETTINGS_KEYS:
            value = self._load_setting(key, load_default_values)
            setattr(settings_vm, key, value)

    def _load_setting(self, settings_key: str, load_default_values: bool = False) -> object:
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
        setting_type = self.settings_types[settings_key]

        if issubclass(setting_type, QColor):
            value = value.name(QColor.NameFormat.HexArgb)
        elif issubclass(setting_type, int):  # Our custom int_range type is not pickable
            value = int(value)
        elif issubclass(setting_type, float):  # Our custom float_range type is not pickable
            value = float(value)

        self._repository.save(settings_key, value)
