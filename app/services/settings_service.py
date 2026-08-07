from __future__ import annotations

import dataclasses
import typing

from PySide6.QtCore import QObject
from PySide6.QtGui import QColor

from app.models.settings import QtWindowSettings, ImageSettings, DisplaySettings
from app.repositories.settings_repository import SettingsRepository
from app.viewmodels.settings_viewmodel import SettingsViewModel


class SettingsService(QObject):
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
        self._settings_vm.geometry = self._load_setting("geometry")
        self._settings_vm.windowState = self._load_setting("windowState")
        self._settings_vm.image_brightness = self._load_setting("image_brightness")
        self._settings_vm.image_contrast = self._load_setting("image_contrast")
        self._settings_vm.image_saturation = self._load_setting("image_saturation")
        self._settings_vm.canvas_background_color = self._load_setting("canvas_background_color")
        self._settings_vm.create_zone_border_thickness = self._load_setting("create_zone_border_thickness")
        self._settings_vm.create_zone_border_color = self._load_setting("create_zone_border_color")
        self._settings_vm.create_zone_fill_color = self._load_setting("create_zone_fill_color")
        self._settings_vm.unselected_zone_border_thickness = self._load_setting("unselected_zone_border_thickness")
        self._settings_vm.unselected_zone_border_color = self._load_setting("unselected_zone_border_color")
        self._settings_vm.unselected_zone_fill_color = self._load_setting("unselected_zone_fill_color")
        self._settings_vm.selected_zone_border_thickness = self._load_setting("selected_zone_border_thickness")
        self._settings_vm.selected_zone_border_color = self._load_setting("selected_zone_border_color")
        self._settings_vm.selected_zone_fill_color = self._load_setting("selected_zone_fill_color")

    def save_settings(self) -> None:
        self._save_setting("geometry", self._settings_vm.geometry)
        self._save_setting("windowState", self._settings_vm.windowState)
        self._save_setting("image_brightness", self._settings_vm.image_brightness)
        self._save_setting("image_contrast", self._settings_vm.image_contrast)
        self._save_setting("image_saturation", self._settings_vm.image_saturation)
        self._save_setting("canvas_background_color", self._settings_vm.canvas_background_color)
        self._save_setting("create_zone_border_thickness", self._settings_vm.create_zone_border_thickness)
        self._save_setting("create_zone_border_color", self._settings_vm.create_zone_border_color)
        self._save_setting("create_zone_fill_color", self._settings_vm.create_zone_fill_color)
        self._save_setting("unselected_zone_border_thickness", self._settings_vm.unselected_zone_border_thickness)
        self._save_setting("unselected_zone_border_color", self._settings_vm.unselected_zone_border_color)
        self._save_setting("unselected_zone_fill_color", self._settings_vm.unselected_zone_fill_color)
        self._save_setting("selected_zone_border_thickness", self._settings_vm.selected_zone_border_thickness)
        self._save_setting("selected_zone_border_color", self._settings_vm.selected_zone_border_color)
        self._save_setting("selected_zone_fill_color", self._settings_vm.selected_zone_fill_color)

    def _load_setting(self, settings_key: str) -> object:
        setting_type = self.settings_types[settings_key]
        value = self._repository.load(settings_key)

        if value is None:  # if unset, return default value
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
