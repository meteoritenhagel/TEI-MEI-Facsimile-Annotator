import os
import uuid
import zlib
from typing import Callable

import umsgpack
from PIL import Image
from PySide6.QtCore import Slot, Signal, QThread, QCoreApplication, Qt, QRect, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QMainWindow, QMessageBox, QMenuBar, QVBoxLayout, QFileDialog, QLabel, QWidget, \
    QHBoxLayout, QPushButton, QSizePolicy
from pyqttoast import ToastPreset

from src.constants import Constants
from src.dialog.dialog_loading import LoadingDialogContent, LoadingDialog
from src.dialog.dialog_save_on_exit import DialogSaveOnExit
from src.logger import LoggerSingleton
from src.program_state import ProgramStateSingleton
from src.settings import settings_set, Settings, settings_get, settings_revert_to_default_values
from src.widgets.imagegraphicsview import ImageGraphicsView
from src.widgets.widgets import ToolTipMenu, FocusableLineEdit


class ThreadWrapper(QThread):
    """
    Class ThreadWrapper wraps some intense function into a separate thread,
    such that the main loop is not blocked.

    Attributes:
        finished (Signal[object]): This signal is emitted when the thread has finished executing its assigned function.
                                   It carries the thread_id assigned by MainWindow.thread_function.
        function_to_run (Callable): The costly function that should be run in a separate thread.
        thread_id (uuid.UUID | None): Identifier assigned by MainWindow.thread_function for cleanup bookkeeping.

    Methods:
        run: Starts executing the function passed in a separate thread. Upon finishing, the signal
             finished is emitted.
    """
    finished = Signal(object)

    def __init__(self, function_to_run: Callable = None):
        """
        Constructs an instance of class ThreadWrapper.

        :param function_to_run: The costly function that should be run in a separate thread.
        """
        super().__init__()
        self.function_to_run = function_to_run
        self.thread_id = None

    def run(self):
        """
        Executes the function in the thread and emits the
        :return:
        """
        LoggerSingleton().logger.log_threaded_function(self.function_to_run.__name__)
        try:
            self.function_to_run()
        except Exception as e:
            LoggerSingleton().logger.log_exception(e)
        finally:
            # Always emit, even on exception! Otherwise, the modal LoadingDialog is never closed
            # and the GUI is stuck behind an unclosable dialog
            self.finished.emit(self.thread_id)


class ThreadedMainWindow(QMainWindow):
    """
    Main window class.

    Signals:
        show_error_dialog (Signal[str, str]): This signal is emitted when an error message dialog should be displayed.
                                              First string is the title, second string is the error message.

    Methods:
        closeEvent (QEvent): Overrides QMainWindow.closeEvent for asking the user to save and to enable saving window
                                 geometry.
        thread_function (Callable, LoadingWindowContent, bool): Executes the function in a separate thread and displays
                                                                a LoadingDialog while not finished.

    """
    show_error_dialog = Signal(str, str)

    def __init__(self):
        super().__init__()

        QCoreApplication.setOrganizationName(Constants.ORGANIZATION)
        QCoreApplication.setApplicationName(Constants.APPLICATION)
        QCoreApplication.setOrganizationDomain(Constants.DOMAIN)

        program_state = ProgramStateSingleton().program_state
        program_state._main_window = self

        # Connect to a bound method of this QObject to show toasts
        program_state.show_toast.connect(self._show_toast)

        # Check if all settings are set, otherwise reset them to default values
        for setting in Settings:
            if settings_get(setting) is None:
                settings_revert_to_default_values()
                LoggerSingleton().logger.log_warning(f"Invalid setting value '{settings_get(setting)}' "
                                                     f"for key '{setting.key}'. "
                                                     f"Revert all settings to default.")
                break

        # Load window geometry
        self.restoreGeometry(settings_get(Settings.GEOMETRY))
        self.restoreState(settings_get(Settings.WINDOW_STATE))

        self._threads = dict()

    def closeEvent(self, event):
        """
        Overrides QMainWindow.closeEvent to enable for saving window geometry.
        :param event: Passed close event.
        """
        LoggerSingleton().logger.log_info("MainWindow.closeEvent")

        settings_set(Settings.GEOMETRY, self.saveGeometry())
        settings_set(Settings.WINDOW_STATE, self.saveState())
        event.accept()

    def thread_function(
            self,
            function_to_run: Callable,
            loading_window_content: LoadingDialogContent = None,
            exit_after: bool = False
    ):
        """
        Executes the function in a separate thread and displays a LoadingDialog while not finished.

        :param function_to_run: Function that should be executed.
        :param loading_window_content: Containing information about what should be shown in the loading dialog.
        :param exit_after: Closes the main window after the thread has finished.
        """
        if loading_window_content is None:
            loading_window_content = LoadingDialogContent()
        loading_dialog = LoadingDialog(self, content=loading_window_content)
        loading_dialog.show()
        new_thread = ThreadWrapper(function_to_run)
        thread_id = uuid.uuid4()
        new_thread.thread_id = thread_id
        self._threads[thread_id] = {"thread": new_thread, "loading_dialog": loading_dialog}

        # Connect to the bound method (a slot on this QObject) so the cleanup runs on the
        # main thread via a queued connection. Connecting a plain closure here
        # would make Qt invoke it in the emitting worker thread, where closing the dialog
        # (a GUI operation) is NOT allowed and deadlocks the application!
        new_thread.finished.connect(self._close_thread)

        if exit_after:
            new_thread.finished.connect(self.close)
        new_thread.start()
        return new_thread

    @Slot(str, str, ToastPreset)
    def _show_toast(self, toast_title, toast_text, toast_preset):
        """
        Forwards a show_toast signal to the UI on the main thread.
        """
        self.show_toast(toast_title, toast_text, toast_preset)

    @Slot(object)
    def _close_thread(self, thread_id: uuid.UUID):
        """
        Closes the loading dialog belonging to the finished thread and removes the thread from the
        dictionary threads. Invoked on the main thread via the ThreadWrapper.finished signal.
        :param thread_id: ID of the thread to be closed.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._close_thread(thread_id={thread_id})")
        entry = self._threads.pop(thread_id, None)
        if entry is not None:
            entry["loading_dialog"].close_dialog()
            # The thread has already left its run() method (the signal finished was emitted at its end).
            # Now, wait for the OS thread to fully terminate before dropping the last reference.
            entry["thread"].wait()

    @Slot(str, str)
    def _show_error_dialog(self, title: str, message: str):
        LoggerSingleton().logger.log_info(f"MainWindow._show_error_dialog(title={title}, message={message})")
        QMessageBox.critical(self, title, message)


class MainWindow(ThreadedMainWindow):
    def __init__(self):
        super().__init__()
        self._setup_menu()
        self._setup_ui()
        self._setup_actions()

        # Set debug logging
        LoggerSingleton().logger.enable_debug_logging(settings_get(Settings.DEBUG_ENABLED))

    def closeEvent(self, event):
        if ProgramStateSingleton().program_state.has_unsaved_changes:
            # ask the user how they want to proceed when unsaved changes are present
            action_value = DialogSaveOnExit().exec()

            if action_value == DialogSaveOnExit.CANCEL:
                event.ignore()
                return
            elif action_value == DialogSaveOnExit.DISCARD:
                pass
            elif action_value == DialogSaveOnExit.SAVE:
                event.ignore()
                self._save_project(exit_after=True)
                return
        super().closeEvent(event)


    def _setup_menu(self):
        # Menu bar for file and export operations
        self.menubar = QMenuBar()
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 544, 23))

        file_menu = ToolTipMenu("File")
        self.actionNewProject = QAction(self.centralWidget())
        self.actionNewProject.setText(QCoreApplication.translate("MainWindow", u"New Project", None))
        self.actionNewProject.setToolTip(u"Create a new GlossIT project")
        self.actionNewProject.setObjectName(u"actionNewProject")
        self.actionNewProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentNew)))
        self.actionNewProject.triggered.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("actionNewProject.triggered")
        )
        file_menu.addAction(self.actionNewProject)

        self.actionOpenProject = QAction(self.centralWidget())
        self.actionOpenProject.setText(QCoreApplication.translate("MainWindow", u"Load Project", None))
        self.actionOpenProject.setToolTip(u"Open a GlossIT project from a file")
        self.actionOpenProject.setObjectName(u"actionOpenProject")
        self.actionOpenProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen)))
        self.actionOpenProject.triggered.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("actionOpenProject.triggered")
        )
        file_menu.addAction(self.actionOpenProject)

        self.actionSaveProject = QAction(self.centralWidget())
        self.actionSaveProject.setText(QCoreApplication.translate("MainWindow", u"Save Project", None))
        self.actionSaveProject.setToolTip(u"Save the current GlossIT project")
        self.actionSaveProject.setEnabled(False)
        self.actionSaveProject.setObjectName(u"actionSaveProject")
        self.actionSaveProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSave)))
        self.actionSaveProject.triggered.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("actionSaveProject.triggered")
        )
        file_menu.addAction(self.actionSaveProject)

        self.actionSaveAsProject = QAction(self.centralWidget())
        self.actionSaveAsProject.setText(QCoreApplication.translate("MainWindow", u"Save Project As", None))
        self.actionSaveAsProject.setToolTip(u"Save the current GlossIT project to another file")
        self.actionSaveAsProject.setEnabled(False)
        self.actionSaveAsProject.setObjectName(u"actionSaveAsProject")
        self.actionSaveAsProject.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentSaveAs)))
        self.actionSaveAsProject.triggered.connect(
            lambda: LoggerSingleton().logger.log_user_interaction("actionSaveAsProject.triggered")
        )
        file_menu.addAction(self.actionSaveAsProject)

        self.menubar.addMenu(file_menu)
        self.setMenuBar(self.menubar)

    def _setup_ui(self):
        """
        Set up the UI widgets.
        """
        label = QLabel("abc")
        layout = QVBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.imageGraphicsView = ImageGraphicsView(self)
        layout.addWidget(label)
        layout.addWidget(self.imageGraphicsView)

        pagechange_layout = QHBoxLayout()
        pagechange_layout.setObjectName(u"horizontalLayout_2")
        self.buttonPreviousPage = QPushButton(central_widget)
        self.buttonPreviousPage.setEnabled(False)
        self.buttonPreviousPage.setObjectName(u"buttonPreviousPage")
        self.buttonPreviousPage.setText(QCoreApplication.translate("MainWindow", u"<< Previous Page", None))
        pagechange_layout.addWidget(self.buttonPreviousPage)
        self.lineEditCurrentPage = FocusableLineEdit(central_widget)
        self.lineEditCurrentPage.setEnabled(False)
        self.lineEditCurrentPage.setObjectName(u"lineEditCurrentPage")
        self.lineEditCurrentPage.setText(QCoreApplication.translate("MainWindow", u"", None))
        self.lineEditCurrentPage.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.lineEditCurrentPage.setSizePolicy(sizePolicy)
        pagechange_layout.addWidget(self.lineEditCurrentPage)
        self.buttonNextPage = QPushButton(central_widget)
        self.buttonNextPage.setEnabled(False)
        self.buttonNextPage.setObjectName(u"buttonNextPage")
        self.buttonNextPage.setText(QCoreApplication.translate("MainWindow", u"Next Page >>", None))
        pagechange_layout.addWidget(self.buttonNextPage)
        layout.addLayout(pagechange_layout)

        horizontalLayoutUndoRedo = QHBoxLayout()
        self.buttonUndo = QPushButton(central_widget)
        self.buttonUndo.setObjectName(u"buttonUndo")
        self.buttonUndo.setText(QCoreApplication.translate("MainWindow", u"Undo", None))
        self.buttonUndo.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditUndo)))
        self.buttonUndo.setToolTip(u"Undo the last action (Ctrl+Z)")
        self.buttonUndo.setEnabled(False)
        horizontalLayoutUndoRedo.addWidget(self.buttonUndo)
        self.buttonRedo = QPushButton(central_widget)
        horizontalLayoutUndoRedo.addWidget(self.buttonRedo)
        self.buttonRedo.setObjectName(u"buttonRedo")
        self.buttonRedo.setIcon(QIcon(QIcon.fromTheme(QIcon.ThemeIcon.EditRedo)))
        self.buttonRedo.setToolTip(u"Redo the last action (Ctrl+Y or Ctrl+Shift+Z)")
        self.buttonRedo.setEnabled(False)

        self.buttonRedo.setText(QCoreApplication.translate("MainWindow", u"Redo", None))
        layout.addLayout(horizontalLayoutUndoRedo)



        program_state = ProgramStateSingleton().program_state

        # Connect the Previous Page and Next Page buttons to the corresponding actions, and update the label accordingly
        def on_click_previous_page():
            def to_previous_page():
                program_state.go_to_previous_page()

            self.thread_function(to_previous_page)

        def on_click_next_page():
            def to_next_page():
                program_state.go_to_next_page()

            self.thread_function(to_next_page)

        # Also connect the page selector accordingly
        def on_current_page_changed():
            """
            This function is called when the current page selection is changed and RETURN or ENTER was pressed.
            We use it to check validity of the user input and go to the selected page.
            """

            suffix = f" / {program_state.number_of_pages}"
            current_text = self.lineEditCurrentPage.text()

            LoggerSingleton().logger.log_user_interaction(f"lineEditCurrentPage returnPressed {current_text}")

            try:
                if current_text.endswith(suffix):
                    number = int(current_text.split("/")[0].strip())
                else:
                    number = int(current_text)
                number -= 1  # user expects the numbering to start from 1!

                if not program_state.page_index_is_valid(number):
                    number = None
            except Exception as e:
                number = None

            def go_to_page():
                try:
                    program_state.go_to_page(number)
                except Exception as e:
                    pass

            if number is None:
                # reset the displayed text to the standard value
                self.lineEditCurrentPage.setText(program_state.page_counter_text)
            else:
                self.thread_function(go_to_page)

            self.lineEditCurrentPage.clearFocus()

        def on_page_text_gained_focus():
            """
            This function is called when the page text has gained focus.
            We use this to automatically preselect the number that should be changed
            by the user for easy usability.
            """
            LoggerSingleton().logger.log_user_interaction("lineEditCurrentPage gained focus")
            current_text = self.lineEditCurrentPage.text()
            prefix = f"{program_state.current_page_index + 1}"
            suffix = f" / {program_state.number_of_pages}"
            if current_text == f"{prefix}{suffix}":
                # wrap in single shot timer to have enough time that the selection occurs
                QTimer.singleShot(0, lambda: self.lineEditCurrentPage.setSelection(0, len(prefix)))

        self.buttonPreviousPage.clicked.connect(on_click_previous_page)
        self.buttonNextPage.clicked.connect(on_click_next_page)
        program_state.data_changed.connect(
            lambda: (
                self.lineEditCurrentPage.setText(str(program_state.page_counter_text)),
                LoggerSingleton().logger.log_info(f"update_line_edit_current_page")
            )
        )
        self.lineEditCurrentPage.inFocus.connect(on_page_text_gained_focus)
        self.lineEditCurrentPage.returnPressed.connect(on_current_page_changed)

        # Connect Undo and Redo
        def update_undo_redo_buttons():
            LoggerSingleton().logger.log_info(
                f"update_undo_redo_buttons"
            )
            self.buttonUndo.setEnabled(program_state.has_undo_actions())
            self.buttonRedo.setEnabled(program_state.has_redo_actions())

        def on_undo():
            LoggerSingleton().logger.log_user_interaction("buttonUndo clicked")

            def undo():
                program_state.undo()

            self.main_window.thread_function(undo)

        def on_redo():
            LoggerSingleton().logger.log_user_interaction("buttonRedo clicked")

            def redo():
                program_state.redo()

            self.main_window.thread_function(redo)

        self.buttonUndo.clicked.connect(on_undo)
        self.buttonRedo.clicked.connect(on_redo)
        program_state.data_changed.connect(update_undo_redo_buttons)

        # Connect the ProgramState signal to updating of the image widget
        program_state = ProgramStateSingleton().program_state

        def update_image():
            LoggerSingleton().logger.log_info(
                f"Ui_MainWindow.setupUi.update_image(...)"
            )
            self.imageGraphicsView.scene.clear()
            if program_state.graphics_image is not None:
                self.imageGraphicsView.load_image_from_pil(
                    program_state.graphics_image
                )
            if program_state.graphics_objects is not None:
                for obj in program_state.graphics_objects:
                    for q_object in obj.to_objects():
                        self.imageGraphicsView.scene.addItem(q_object)
            if program_state.currently_selected_object is not None:
                pass

        program_state.data_changed.connect(update_image)


    def _setup_actions(self):
        # connect buttons to actions
        self.actionNewProject.triggered.connect(self._new_project)
        self.actionNewProject.setShortcut(QKeySequence("Ctrl+N"))

        self.actionOpenProject.triggered.connect(self._open_project)
        self.actionOpenProject.setShortcut(QKeySequence("Ctrl+O"))

        self.actionSaveProject.triggered.connect(self._save_project)
        self.actionSaveProject.setShortcut(QKeySequence("Ctrl+S"))

        self.actionSaveAsProject.triggered.connect(self._save_as_project)
        self.actionSaveAsProject.setShortcut(QKeySequence("Ctrl+Shift+S"))

    def keyPressEvent(self, event):
        """
        Overrides QMainWindow.keyPressEvent to enable keyboard shortcuts.
        :param event: Passed event.
        """
        key = event.key()
        LoggerSingleton().logger.log_info(f"MainWindow.keyPressEvent ({key})")
        program_state = ProgramStateSingleton().program_state

        if key == Qt.Key.Key_Escape:
            program_state.currently_selected_object = None
        elif (key == Qt.Key.Key_Z and
              event.modifiers() & Qt.KeyboardModifier.ControlModifier and
              event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            self.thread_function(program_state.redo)
        elif key == Qt.Key.Key_Y and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.thread_function(program_state.redo)
        elif key == Qt.Key.Key_Z and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.thread_function(program_state.undo)

    def _new_project(self):
        """
        Opens an OpenProjectFileSelectDialog and initializes the program state singleton accordingly.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._new_project()")
        program_state = ProgramStateSingleton().program_state

        program_state.save_file_path = None  # Reset save file name to prevent accidentally overriding other data!

        image_paths, _ = QFileDialog.getOpenFileNames(
            self,
            caption="Open Image Files",
            filter=f"Image file (*.jpg *.jpeg *.png *.tiff);;All Files (*.*)"
        )

        if image_paths:
            program_state.path_to_images = image_paths

            loading_window_content = LoadingDialogContent()

            def on_new():
                loading_window_content.action_text = "Loading image"
                loading_window_content.progress_bar_visible = True

                program_state.project_images = [Image.open(image_path) for image_path in image_paths]
                loading_window_content.callback_tqdm.close()

                loading_window_content.progress_bar_visible = False
                loading_window_content.action_text = "Setting up graphics"
                program_state.construct_view()
                loading_window_content.progress_bar_visible = True

            self.thread_function(on_new, loading_window_content=loading_window_content)

            # Now, we allow saving, exporting, and going to previous/next pages
            self._enable_buttons()

    def _open_project(self):
        """
        Asks the user to select a file and loads it into the program state.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._open_project()")
        program_state = ProgramStateSingleton().program_state

        # get path of where the file should be saved
        load_path, _ = QFileDialog.getOpenFileName(
            self,
            caption="Open Project File",
            filter=f"Project File (*.{Constants.PROJECT_FILE_EXTENSION});;All Files (*.*)"
        )
        LoggerSingleton().logger.log_info(f"User selected model path {load_path}")
        if load_path is not None and load_path != "":
            loading_window_content = LoadingDialogContent()

            def on_load():
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Reading from file system"
                program_state.save_file_path = load_path
                try:
                    with open(load_path, "rb") as file:
                        loaded_compressed = file.read()
                except (EOFError, umsgpack.UnpackException) as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to read file from file system.")
                    return

                try:
                    loaded_uncompressed = zlib.decompress(loaded_compressed)
                except zlib.error as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to decompress data.")
                    return

                try:
                    loaded_unserialized = umsgpack.loads(loaded_uncompressed)
                except (EOFError, umsgpack.UnpackException) as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to unserialize data.")
                    return

                loading_window_content.action_text = "Loading file contents into program state"
                loading_window_content.progress_bar_visible = True
                try:
                    program_state.from_dict(loaded_unserialized, tqdm_progress=loading_window_content.callback_tqdm)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error",
                                                "Failed to read file contents. Is this a valid project file?")
                    return

                loading_window_content.callback_tqdm.close()

                try:
                    program_state.construct_view()
                    loading_window_content.action_text = "Setting up spatial database"
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Some error has occurred.")
                    loading_window_content.callback_tqdm.close()
                    return

                program_state.has_unsaved_changes = False

            self.thread_function(on_load, loading_window_content=loading_window_content)

            # Now, we allow saving, exporting, and going to previous/next pages
            self._enable_buttons()

    def _enable_buttons(self):
        """
        Enables all buttons that can only be accessed after a project is loaded or created.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._enable_buttons()")
        self.actionSaveProject.setEnabled(True)
        self.actionSaveAsProject.setEnabled(True)
        self.buttonPreviousPage.setEnabled(True)
        self.lineEditCurrentPage.setEnabled(True)
        self.buttonNextPage.setEnabled(True)

    def _save_project(self, exit_after: bool = False):
        """
        Saves the current project to the previously saved file. If this is the first save,
        _save_as_project is called.
        :param exit_after: Exit after saving the project.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._save_project(exit_after={exit_after})")
        program_state = ProgramStateSingleton().program_state
        default_filename = program_state.save_file_path
        if default_filename is None:
            self._save_as_project(exit_after=exit_after)
        else:
            self._save_project_to_path(default_filename, exit_after=exit_after)

    def _save_as_project(self, exit_after: bool = False):
        """
        Saves the current project to a file.
        :param exit_after: Exit after saving the project.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._save_as_project(exit_after={exit_after})")
        program_state = ProgramStateSingleton().program_state
        default_filename = program_state.save_file_path
        if default_filename is None:
            default_filename = os.path.join(
                os.path.dirname(program_state.path_to_mets), f"project.{Constants.PROJECT_FILE_EXTENSION}"
            )

        # get path of where the file should be saved
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            caption="Save Project File",
            dir=default_filename,
            filter=f"Project File (*.{Constants.PROJECT_FILE_EXTENSION});;All Files (*.*)"
        )
        self._save_project_to_path(save_path, exit_after=exit_after)

    def _save_project_to_path(self, save_path: str, exit_after: bool = False):
        """
        Saves the current project to the location provided.
        :param exit_after: Exit after saving the project.
        """
        LoggerSingleton().logger.log_info(f"MainWindow._save_project_to_path(save_path={save_path}, "
                                          f"exit_after={exit_after})")
        program_state = ProgramStateSingleton().program_state
        if save_path is not None and save_path != "":
            if save_path.split(".")[-1] != Constants.PROJECT_FILE_EXTENSION:
                save_path += f".{Constants.PROJECT_FILE_EXTENSION}"
            program_state.save_file_path = save_path
            loading_window_content = LoadingDialogContent()

            def on_save():
                loading_window_content.status_text = "Please wait..."
                loading_window_content.action_text = "Constructing save file"
                loading_window_content.progress_bar_visible = True
                save_file = program_state.to_dict(tqdm_progress=loading_window_content.callback_tqdm)
                loading_window_content.callback_tqdm.close()
                loading_window_content.progress_bar_visible = False

                loading_window_content.action_text = "Saving to file system"
                loading_window_content.status_text = "Please wait..."
                try:
                    serialized_data = umsgpack.dumps(save_file)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to serialize data.")
                    return

                try:
                    compressed_data = zlib.compress(serialized_data)
                except Exception as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to compress data.")
                    return

                try:
                    with open(save_path, "wb") as file:
                        file.write(compressed_data)
                except umsgpack.PackException as e:
                    LoggerSingleton().logger.log_exception(e)
                    self.show_error_dialog.emit("Error", "Failed to write file to file system.")
                    return
                # Update the status of the saved changes
                program_state.has_unsaved_changes = False

            self.thread_function(on_save, loading_window_content=loading_window_content, exit_after=exit_after)
