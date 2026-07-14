import builtins
from enum import Enum

from PySide6.QtCore import QSettings, QByteArray
from PySide6.QtGui import QColor

from src.constants import Constants


class Setting:
    """
    Class Setting stores setting properties.

    Attributes:
        key (str): The key under which the setting is stored.
        type (builtins.type): The type of the setting.
        default_value (object): The default value of the setting.
        in_menu (bool): Whether the setting should be displayed in the settings dialog.
    """
    def __init__(self, key: str, type: builtins.type, default_value: object = None, in_menu: bool = False):
        self.key: str = key
        self.type: builtins.type = type
        self.default_value: object = default_value
        self.in_menu: bool = in_menu


class Settings(Setting, Enum):
    """
    Enum for application settings keys.
    """
    GEOMETRY = ("geometry", QByteArray, False)               # Main window geometry (QByteArray)
    WINDOW_STATE = ("windowState", QByteArray, False)        # Main window state (QByteArray)

    DEBUG_ENABLED = ("debugEnabled", bool, False)            # True if detailed debug logging is activated (bool)

    ### Image Options ###
    IMAGE_BRIGHTNESS = ("imageBrightness", float, 1.)        # Displayed image brightness, value between 0 and 2
    IMAGE_CONTRAST = ("imageContrast", float, 1.)            # Displayed image contrast, value between 0 and 2
    IMAGE_SATURATION = ("imageSaturation", float, 1.)        # Displayed image saturation, value between 0 and 2

    ### Colors and Display Options ###
    BOUNDING_BOX_COLOR =(
        ("boundingBoxColor", QColor, QColor(0, 114, 178)))   # Bounding box color (QColor)


def _get_settings() -> QSettings:
    """
    Returns the applications current user-specific settings (as opposed to project-specific
    properties that are saved in the project files). This includes window positioning, font colors, etc.
    Do not use this function directly, it is recommended to use settings_get and settings_set instead!

    :return: QSettings instance.
    """
    return QSettings(Constants.ORGANIZATION, Constants.APPLICATION)


def settings_set(setting: Settings, value: object) -> None:
    """
    Sets the settings value.
    :param setting: Setting to modify.
    :param value: Settings value to set.
    """
    if isinstance(value, QColor):
        value = value.name(QColor.NameFormat.HexArgb)
    _get_settings().setValue(setting.key, value)


def settings_get(setting: Settings) -> object:
    """
    Returns the settings value.
    :param setting: Setting to return.
    :return: The settings value.
    """
    value = _get_settings().value(setting.key)

    if issubclass(setting.type, QColor):
        if value is not None:
            return QColor(value)
        else:
            return QColor(255, 255, 255, 255)
    elif issubclass(setting.type, bool):
        return value in [True, 'true', 'True', 1, '1']
    elif issubclass(setting.type, int):
        try:
            return int(value)
        except ValueError:
            return 255
    elif issubclass(setting.type, float):
        try:
            return float(value)
        except ValueError:
            return 1.
    else:
        return value


def settings_revert_to_default_values():
    """
    Reverts all settings values to their default values.
    :return:
    """
    for setting in Settings:
        settings_set(setting, setting.default_value)
