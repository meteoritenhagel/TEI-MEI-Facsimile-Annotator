from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal, QEvent, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget, QLineEdit,
)

from app.constants import APPLICATION_NAME, DOCUMENT_FILE_EXTENSION
from app.services.document_service import DocumentService
from app.services.settings_service import SettingsService
from app.services.xml_id_service import XmlIdService
from app.ui.dialog_change_settings import DialogChangeSettings
from app.ui.facsimile_canvas import FacsimileCanvas
from app.ui.widgets import FocusableLineEdit
from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.settings_viewmodel import SettingsViewModel
from app.viewmodels.surface_viewmodel import SurfaceViewModel
from app.viewmodels.zone_viewmodel import ZoneViewModel


class MainWindow(QMainWindow):
    def __init__(
        self,
        document_vm: DocumentViewModel,
        settings_vm: SettingsViewModel,
        document_service: DocumentService,
        settings_service: SettingsService,
        xml_id_service: XmlIdService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._document_vm = document_vm
        self._settings_vm = settings_vm
        self._document_service = document_service
        self._settings_service = settings_service
        self._xml_id_service = xml_id_service
        self._current_surface: SurfaceViewModel | None = None
        self._zone_connections: list[ZoneViewModel] = []
        self._editing_spinboxes = False

        self._canvas = FacsimileCanvas(document_vm, settings_vm, document_service, self)
        self._zone_table = QTableWidget(0, 5, self)
        self._zone_table.setHorizontalHeaderLabels(["xml:id", "ulx", "uly", "lrx", "lry"])
        self._zone_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._zone_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._zone_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._zone_table.verticalHeader().setVisible(False)
        header = self._zone_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(56)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, 5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self._zone_table.setColumnWidth(column, 58)
        self._zone_table.itemSelectionChanged.connect(self._zone_table_selection_changed)

        self._document_type_combo = QComboBox(self)
        self._document_type_combo.addItems(["TEI", "MEI"])
        self._document_type_combo.currentTextChanged.connect(self._document_type_changed)

        self._page_label = FocusableLineEdit("0 / 0", self)
        self._page_label.setMaximumWidth(80)
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.inFocus.connect(self._page_text_gained_focus)
        self._page_label.returnPressed.connect(self._page_text_press_enter)

        self._status_label = QLabel("", self)
        self._image_label = QLabel("No page image", self)
        self._delete_zone_button = QPushButton("Delete Zone", self)
        self._delete_zone_button.clicked.connect(self._delete_selected_zone)

        self._ulx_spin = self._coordinate_spinbox()
        self._uly_spin = self._coordinate_spinbox()
        self._lrx_spin = self._coordinate_spinbox()
        self._lry_spin = self._coordinate_spinbox()
        for spinbox in (self._ulx_spin, self._uly_spin, self._lrx_spin, self._lry_spin):
            spinbox.valueChanged.connect(self._coordinate_spinbox_changed)

        self._build_menu()
        self._build_toolbar()
        self._build_layout()
        self._connect_document_signals()
        self._refresh_all()

        self._restore_window_settings()

    def _build_menu(self) -> None:
        # --- File Menu ---
        file_menu = self.menuBar().addMenu("File")
        action_new = file_menu.addAction("New", self._new_document)
        action_new.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentNew))
        action_new.setShortcut("Ctrl+N")

        action_open = file_menu.addAction("Open...", self._open_document)
        action_open.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen))
        action_open.setShortcut("Ctrl+O")

        file_menu.addAction("Add Page Images...", self._add_page_image)
        file_menu.addAction("Remove Current Page", self._remove_current_page)

        action_save = file_menu.addAction("Save", self._save_document)
        action_save.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave))
        action_save.setShortcut("Ctrl+S")

        action_save_as = file_menu.addAction("Save As...", self._save_document_as)
        action_save_as.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSaveAs))
        action_save_as.setShortcut("Ctrl+Shift+S")

        # --- Edit Menu ---
        edit_menu = self.menuBar().addMenu("Edit")

        action_settings = edit_menu.addAction("Settings...", self._open_settings_dialog)
        action_settings.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentProperties))

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Document", self)
        toolbar.setMovable(False)
        toolbar.setObjectName("toolbar")
        self.addToolBar(toolbar)
        toolbar.addWidget(QLabel("Type: ", self))
        toolbar.addWidget(self._document_type_combo)
        toolbar.addSeparator()
        toolbar.addAction("Add Pages", self._add_page_image)
        toolbar.addAction("Remove Page", self._remove_current_page)
        toolbar.addSeparator()
        toolbar.addAction("Previous Page", self._previous_page)
        toolbar.addWidget(self._page_label)
        toolbar.addAction("Next Page", self._next_page)
        toolbar.addSeparator()
        toolbar.addWidget(self._status_label)

    def _build_layout(self) -> None:
        root = QWidget(self)
        main_layout = QHBoxLayout(root)
        main_layout.addWidget(self._canvas, stretch=1)

        side_panel = QWidget(self)
        side_layout = QVBoxLayout(side_panel)
        side_layout.addWidget(self._image_label)
        side_layout.addWidget(QLabel("Zones", self))
        side_layout.addWidget(self._zone_table)

        coordinate_layout = QVBoxLayout()
        for label, spinbox in (
            ("ulx", self._ulx_spin),
            ("uly", self._uly_spin),
            ("lrx", self._lrx_spin),
            ("lry", self._lry_spin),
        ):
            row = QHBoxLayout()
            row.addWidget(QLabel(label, self))
            row.addWidget(spinbox)
            coordinate_layout.addLayout(row)
        side_layout.addLayout(coordinate_layout)
        side_layout.addWidget(self._delete_zone_button)
        side_panel.setMinimumWidth(340)
        main_layout.addWidget(side_panel)
        self.setCentralWidget(root)
        self.resize(1280, 850)

    def _connect_document_signals(self) -> None:
        self._document_vm.surfaces_changed.connect(self._rewire_current_surface)
        self._document_vm.surfaces_changed.connect(self._refresh_all)
        self._document_vm.current_page_index_changed.connect(self._rewire_current_surface)
        self._document_vm.current_page_index_changed.connect(self._refresh_all)
        self._document_vm.document_type_changed.connect(self._sync_document_type_combo)
        self._document_vm.file_path_changed.connect(self._update_window_title)
        self._document_vm.dirty_changed.connect(self._update_window_title)
        self._document_vm.selected_zone_index_changed.connect(self._sync_selection)
        self._document_service.open_succeeded.connect(lambda: self._status_label.setText("Opened"))
        self._document_service.add_surface_succeeded.connect(lambda: self._status_label.setText("Page added"))
        self._document_service.save_succeeded.connect(lambda: self._status_label.setText("Saved"))
        self._document_service.save_failed.connect(self._save_failed)
        self._document_service.open_failed.connect(self._open_failed)
        self._document_service.add_surface_failed.connect(self._add_surface_failed)

    def _rewire_current_surface(self, *_args) -> None:
        self._disconnect_surface()
        self._current_surface = self._current_page()
        if self._current_surface is not None:
            self._current_surface.zones_changed.connect(self._rewire_zones)
            self._current_surface.zones_changed.connect(self._rebuild_zone_table)
            self._current_surface.image_path_changed.connect(self._refresh_image_label)
        self._rewire_zones()

    def _disconnect_surface(self) -> None:
        if self._current_surface is not None:
            try:
                self._current_surface.zones_changed.disconnect(self._rewire_zones)
                self._current_surface.zones_changed.disconnect(self._rebuild_zone_table)
                self._current_surface.image_path_changed.disconnect(self._refresh_image_label)
            except RuntimeError:
                pass
        self._disconnect_zones()
        self._current_surface = None

    def _rewire_zones(self) -> None:
        self._disconnect_zones()
        surface = self._current_page()
        if surface is None:
            return
        for zone_vm in surface.zones:
            zone_vm.rect_changed.connect(self._zone_rect_changed)
            self._zone_connections.append(zone_vm)
        self._rebuild_zone_table()

    def _disconnect_zones(self) -> None:
        for zone_vm in self._zone_connections:
            try:
                zone_vm.rect_changed.disconnect(self._zone_rect_changed)
            except RuntimeError:
                pass
        self._zone_connections.clear()

    def _refresh_all(self, *_args) -> None:
        self._rewire_current_surface()
        self._sync_document_type_combo()
        self._refresh_page_label()
        self._refresh_image_label()
        self._rebuild_zone_table()
        self._sync_selection()
        self._update_window_title()

    def _current_page(self) -> SurfaceViewModel | None:
        surfaces = self._document_vm.surfaces
        index = self._document_vm.current_page_index
        if not 0 <= index < len(surfaces):
            return None
        return surfaces[index]

    def _new_document(self) -> None:
        self._document_service.new_document()
        self._status_label.setText("New document")

    def _open_document(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open Document",
            "",
            f"Facsimile Annotation (*.{DOCUMENT_FILE_EXTENSION});;Legacy Msgpack (*.msgpack *.mpack);;All Files (*)",
        )
        if not filename:
            return
        self._status_label.setText("Opening...")
        self._document_service.open_file(Path(filename))

    def _save_document(self) -> None:
        if self._document_vm.file_path is None:
            self._save_document_as()
            return
        self._status_label.setText("Saving...")
        self._document_service.save_file()

    def _save_document_as(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Document",
            "",
            f"Facsimile Annotation (*.{DOCUMENT_FILE_EXTENSION});;All Files (*)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix == "":
            path = path.with_suffix(f".{DOCUMENT_FILE_EXTENSION}")
        self._status_label.setText("Saving...")
        self._document_service.save_file_as(path)

    def _add_page_image(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self,
            "Add Page Images",
            "",
            "Images (*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif);;All Files (*)",
        )
        if not filenames:
            return
        self._document_service.add_surface_from_images([Path(filename) for filename in filenames])

    def _remove_current_page(self) -> None:
        if not self._document_vm.surfaces:
            return
        page_number = self._document_vm.current_page_index + 1
        result = QMessageBox.question(
            self,
            "Remove Page",
            f"Remove page {page_number} and all of its zones?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result != QMessageBox.StandardButton.Yes:
            return
        self._document_service.remove_surface(self._document_vm.current_page_index)
        self._status_label.setText("Page removed")

    def _previous_page(self) -> None:
        self._document_service.go_to_page(self._document_vm.current_page_index - 1)

    def _next_page(self) -> None:
        self._document_service.go_to_page(self._document_vm.current_page_index + 1)

    def _delete_selected_zone(self) -> None:
        self._canvas.delete_selected_zone()

    def _document_type_changed(self, value: str) -> None:
        if value in ("TEI", "MEI"):
            self._document_service.set_document_type(value)

    def _sync_document_type_combo(self, *_args) -> None:
        self._document_type_combo.blockSignals(True)
        self._document_type_combo.setCurrentText(self._document_vm.document_type)
        self._document_type_combo.blockSignals(False)

    def _refresh_page_label(self, *_args) -> None:
        total = len(self._document_vm.surfaces)
        current = self._document_vm.current_page_index + 1 if total else 0
        self._page_label.setText(f" {current} / {total} ")

    def _page_text_gained_focus(self) -> None:
        total = len(self._document_vm.surfaces)
        current = self._document_vm.current_page_index + 1 if total else 0
        if self._page_label.text() == f" {current} / {total} ":
            # wrap in single shot timer to have enough time that the selection occurs
            QTimer.singleShot(0, lambda: self._page_label.setSelection(1, len(str(current))))

    def _page_text_press_enter(self) -> None:
        total = len(self._document_vm.surfaces)

        suffix = f" / {total} "
        current_text = self._page_label.text()

        try:
            if current_text.endswith(suffix):
                number = int(current_text.split("/")[0].strip())
            else:
                number = int(current_text)
            number -= 1

            self._document_service.go_to_page(number)
        except ValueError as e:
            pass
        finally:
            self._refresh_page_label()
            self._page_label.clearFocus()

    def _refresh_image_label(self, *_args) -> None:
        surface = self._current_page()
        self._image_label.setText(surface.image_path if surface and surface.image_path else "No page image")

    def _rebuild_zone_table(self, *_args) -> None:
        surface = self._current_page()
        self._zone_table.blockSignals(True)
        self._zone_table.setRowCount(0)
        if surface is not None:
            self._zone_table.setRowCount(len(surface.zones))
            for row, zone_vm in enumerate(surface.zones):
                self._populate_zone_row(row, zone_vm)
        self._zone_table.blockSignals(False)
        self._sync_selection()

    def _populate_zone_row(self, row: int, zone_vm: ZoneViewModel) -> None:
        surface_index = self._document_vm.current_page_index
        values = [
            self._xml_id_service.zone_xml_id(surface_index, row),
            f"{zone_vm.ulx}",
            f"{zone_vm.uly}",
            f"{zone_vm.lrx}",
            f"{zone_vm.lry}",
        ]
        for column, value in enumerate(values):
            self._zone_table.setItem(row, column, QTableWidgetItem(value))

    def _zone_rect_changed(self, *_args) -> None:
        surface = self._current_page()
        sender = self.sender()
        if surface is None:
            return
        for row, zone_vm in enumerate(surface.zones):
            if zone_vm is sender:
                self._populate_zone_row(row, zone_vm)
                if row == self._document_vm.selected_zone_index:
                    self._sync_coordinate_spinboxes()
                return

    def _zone_table_selection_changed(self) -> None:
        selected_rows = self._zone_table.selectionModel().selectedRows()
        if not selected_rows:
            self._document_service.select_zone(None)
            return
        self._document_service.select_zone(selected_rows[0].row())

    def _sync_selection(self, *_args) -> None:
        selected = self._document_vm.selected_zone_index
        self._zone_table.blockSignals(True)
        self._zone_table.clearSelection()
        if selected is not None and 0 <= selected < self._zone_table.rowCount():
            self._zone_table.selectRow(selected)
        self._zone_table.blockSignals(False)
        self._sync_coordinate_spinboxes()
        self._delete_zone_button.setEnabled(selected is not None)

    def _coordinate_spinbox(self) -> QDoubleSpinBox:
        spinbox = QDoubleSpinBox(self)
        spinbox.setRange(-1_000_000, 1_000_000)
        spinbox.setDecimals(0)
        spinbox.setSingleStep(1)
        return spinbox

    def _sync_coordinate_spinboxes(self) -> None:
        zone_vm = self._selected_zone()
        self._editing_spinboxes = True
        for spinbox in (self._ulx_spin, self._uly_spin, self._lrx_spin, self._lry_spin):
            spinbox.setEnabled(zone_vm is not None)
        if zone_vm is not None:
            self._ulx_spin.setValue(zone_vm.ulx)
            self._uly_spin.setValue(zone_vm.uly)
            self._lrx_spin.setValue(zone_vm.lrx)
            self._lry_spin.setValue(zone_vm.lry)
        else:
            for spinbox in (self._ulx_spin, self._uly_spin, self._lrx_spin, self._lry_spin):
                spinbox.setValue(0)
        self._editing_spinboxes = False

    def _coordinate_spinbox_changed(self, *_args) -> None:
        if self._editing_spinboxes:
            return
        selected = self._document_vm.selected_zone_index
        if selected is None:
            return
        self._document_service.update_zone_rect(
            self._document_vm.current_page_index,
            selected,
            self._ulx_spin.value(),
            self._uly_spin.value(),
            self._lrx_spin.value(),
            self._lry_spin.value(),
        )

    def _selected_zone(self) -> ZoneViewModel | None:
        surface = self._current_page()
        selected = self._document_vm.selected_zone_index
        if surface is None or selected is None or not 0 <= selected < len(surface.zones):
            return None
        return surface.zones[selected]

    def _update_window_title(self, *_args) -> None:
        name = self._document_vm.file_path.name if self._document_vm.file_path else "Untitled"
        dirty = " *" if self._document_vm.dirty else ""
        self.setWindowTitle(f"{APPLICATION_NAME} - {name}{dirty}")

    def _save_failed(self, error: object) -> None:
        message = f"Failed to save: {error}"
        self._status_label.setText(message)
        QMessageBox.warning(self, "Save Failed", message)

    def _open_failed(self, error: object) -> None:
        message = f"Failed to open: {error}"
        self._status_label.setText(message)
        QMessageBox.warning(self, "Open Failed", message)

    def _add_surface_failed(self, error: object) -> None:
        message = f"Failed to add page: {error}"
        self._status_label.setText(message)
        QMessageBox.warning(self, "Add Page Failed", message)

    def _save_window_settings(self):
        self._settings_vm.geometry = self.saveGeometry()
        self._settings_vm.windowState = self.saveState()

    def _restore_window_settings(self):
        geometry = self._settings_vm.geometry
        window_state = self._settings_vm.windowState

        if geometry is not None:
            self.restoreGeometry(geometry)
        if window_state is not None:
            self.restoreState(window_state)

    def _open_settings_dialog(self):
        dialog_change_settings = DialogChangeSettings(self._settings_service, self._settings_vm)
        dialog_change_settings.exec()

    def closeEvent(self, event: QEvent) -> None:
        """
        Handles the window close event. Saves settings before closing.
        """
        self._save_window_settings()
        try:
            self._settings_service.save_settings()
        except Exception as e:
            # Optionally show a warning or log the error
            QMessageBox.warning(self, "Save Settings Failed", f"Failed to save settings: {e}")
        # Accept the event to proceed with closing
        event.accept()
