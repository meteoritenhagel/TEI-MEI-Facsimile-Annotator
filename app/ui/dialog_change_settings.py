from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtGui import QIcon, QColor
from PySide6.QtWidgets import QDialog, QCheckBox, QHBoxLayout, QVBoxLayout, QPushButton, \
    QLabel, QSlider, QLayout, QTabWidget, QWidget

from app.models.settings import int_range, float_range
from app.services.settings_service import SettingsService
from app.ui.widgets import LabeledSlider, ColorButton


class DialogChangeSettings(QDialog):
    """
    This dialog is for modifying the application settings.

    Methods:
        exec: Override. Executes the dialog in the main loop and returns the settings dict on accept, else None.
        reject: Override.

    Private Methods:
        _setupUI: Setups the dialog UI widgets.

    Private Class Methods:
        _create_slider (str, QLayout, bool): Create a LabeledSlider widget with a label indicating its purpose.
        _create_color_button (str, QLayout): Create a ColorButton widget with a label indicating its purpose.
        _widget_get_value (Settings): Extracts the value of the widget that is registered with a Settings.
        _widget_set_value (Settings, object): Sets a new value for the widget that is registered with a Settings.
        _load_settings (dict[Settings, object] | None): Loads the settings from a dictionary or from the global
                                                           application settings.
        _save_settings: Collects the settings from the dialog in a dictionary and accepts the dialog.
        _restore_default: Loads the default application settings and applies them to the widgets.
    """

    # TODO: Here, register settings that should be accessible in the dialog!
    # The settings must be available as properties in the SettingsViewModel.
    SETTINGS_BY_TAB = [
        {
            "title": "Image",
            "settings": [
                {
                    "label": "Brightness",
                    "property": "image_brightness",
                },
                {
                    "label": "Contrast",
                    "property": "image_contrast",
                },
                {
                    "label": "Saturation",
                    "property": "image_saturation",
                }
            ]
        },
        {
            "title": "Display",
            "settings": [
                {
                    "label": "Canvas Background Color",
                    "property": "canvas_background_color",
                },
                {
                    "label": "Create Zone Border Thickness",
                    "property": "create_zone_border_thickness",
                },
                {
                    "label": "Create Zone Border Color",
                    "property": "create_zone_border_color",
                },
                {
                    "label": "Create Zone Fill Color",
                    "property": "create_zone_fill_color",
                },
                {
                    "label": "Unselected Zone Border Thickness",
                    "property": "unselected_zone_border_thickness",
                },
                {
                    "label": "Unselected Zone Border Color",
                    "property": "unselected_zone_border_color",
                },
                {
                    "label": "Unselected Zone Fill Color",
                    "property": "unselected_zone_fill_color",
                },
                {
                    "label": "Selected Zone Border Thickness",
                    "property": "selected_zone_border_thickness",
                },
                {
                    "label": "Selected Zone Border Color",
                    "property": "selected_zone_border_color",
                },
                {
                    "label": "Selected Zone Fill Color",
                    "property": "selected_zone_fill_color",
                },
            ]
        }
    ]

    def __init__(self, settings_service: SettingsService):
        """
        Initialize the class instance.
        """
        super().__init__()

        self.setWindowTitle("Change Settings")

        self._settings_service = settings_service
        self._temporary_settings = settings_service.create_temporary_settings_viewmodel()

        self._property_to_widget = {}

        self._build_layout()
        self._update_widgets_from_settings()

    def _build_layout(self):
        """
        Build the dialog UI widgets.
        """
        layout = QVBoxLayout(self)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        for tab in self.SETTINGS_BY_TAB:
            tab_widget = QWidget()
            tab_layout = QVBoxLayout(tab_widget)
            tab_title = tab["title"]

            for setting in tab["settings"]:
                prop = setting["property"]
                value = getattr(self._temporary_settings, prop)

                # TODO: register types here and in self._update_setting_from_widget
                if isinstance(value, (int_range, float_range)):
                    slider = self._create_slider(setting["label"], tab_layout, type(value))
                    slider.valueChanged.connect(partial(self._update_setting_from_widget, prop, slider))
                    self._property_to_widget[prop] = slider
                elif isinstance(value, QColor):
                    color_button = self._create_color_button(setting["label"], tab_layout)
                    color_button.colorChanged.connect(partial(self._update_setting_from_widget, prop, color_button))
                    self._property_to_widget[prop] = color_button
                elif isinstance(value, bool):
                    checkbox = QCheckBox(setting["label"])
                    checkbox.toggled.connect(partial(self._update_setting_from_widget, prop, checkbox))
                    self._property_to_widget[prop] = checkbox
                    tab_layout.addWidget(checkbox)
                else:
                    raise NotImplementedError(f"Settings type {type(value)} is not supported.")

            self.tabs.addTab(tab_widget, tab_title)

        # Save and Cancel buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave)))
        self.default_btn = QPushButton("Revert to Default")
        self.default_btn.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditUndo)))
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditDelete)))
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.default_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Connect signals
        self.save_btn.clicked.connect(self.accept)
        self.default_btn.clicked.connect(self._restore_default)
        self.cancel_btn.clicked.connect(self.reject)

    @classmethod
    def _create_slider(cls, label_text: str, parent_layout: QLayout, data_type: type) -> LabeledSlider:
        """
        Create a LabeledSlider widget with a label indicating its purpose.
        :param label_text: Text label indicating the slider's purpose.
        :param parent_layout: Parent layout.
        :param data_type: Data type of the slider (either int_range or float_range).
        :return: QSlider or FloatSlider instance.
        """
        label = QLabel(label_text)

        slider = LabeledSlider(data_type=data_type)
        slider.setMinimum(data_type.low)
        slider.setMaximum(data_type.high)

        if issubclass(data_type, float_range):
            slider.setTickInterval(data_type.step)

        slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        parent_layout.addWidget(label)
        parent_layout.addWidget(slider)
        return slider

    @classmethod
    def _create_color_button(cls, label_text: str, parent_layout: QLayout) -> ColorButton:
        """
        Create a ColorButton widget with a label indicating its purpose.
        :param label_text: Label indicating the color button's purpose.
        :param parent_layout: Parent layout.
        :return: ColorButton instance.
        """
        layout = QHBoxLayout()
        label = QLabel(label_text)
        color_button = ColorButton(label=label_text)
        layout.addWidget(label)
        layout.addWidget(color_button)
        parent_layout.addLayout(layout)
        return color_button

    def _update_setting_from_widget(self, prop, widget):
        # TODO: Implement types here, too
        if isinstance(widget, LabeledSlider):
            setattr(self._temporary_settings, prop, widget.value())
        elif isinstance(widget, ColorButton):
            setattr(self._temporary_settings, prop, widget.color())
        elif isinstance(widget, QCheckBox):
            setattr(self._temporary_settings, prop, widget.isChecked())

    def _update_widgets_from_settings(self):
        for prop, widget in self._property_to_widget.items():
            value = getattr(self._temporary_settings, prop)
            if isinstance(widget, LabeledSlider):
                widget.setValue(value)
            elif isinstance(widget, ColorButton):
                widget.set_color(value)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(value)

    def _restore_default(self):
        """
        Loads the default application settings and applies them to the widgets.
        """
        self._settings_service.load_settings_to_viewmodel(self._temporary_settings, load_default_values=True)
        self._update_widgets_from_settings()

    def accept(self):
        """
        Accepts the dialog, i.e., the window settings are applied to the global settings state.
        """
        self._settings_service.apply_temporary_settings_viewmodel(self._temporary_settings)
        super().accept()
