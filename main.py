import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from src.dialog.main_dialog import MainWindow
from src.logger import LoggerSingleton
from src.program_state import ProgramStateSingleton
from src.settings import settings_get, settings_set, Settings


def start_gui():
    """
    Starts the GUI.
    """

    def qt_message_handler(mode, context, message):
        # Choose logging level based on message type
        logger = LoggerSingleton().logger
        if mode == QtMsgType.QtDebugMsg:
            logger.log_debug(message)
        elif mode == QtMsgType.QtInfoMsg:
            logger.log_info(message)
        elif mode == QtMsgType.QtWarningMsg:
            logger.log_warning(message)
        elif mode == QtMsgType.QtCriticalMsg:
            logger.log_error(message)
        elif mode == QtMsgType.QtFatalMsg:
            logger.log_error(message)
        else:
            logger.log_info(message)

    try:
        app = QApplication(sys.argv)

        # Redirect Qt stderr output to the logger
        qInstallMessageHandler(qt_message_handler)

        settings_set(Settings.DEBUG_ENABLED, False)  # DEBUG

        #icon = QIcon()
        #icon.addFile("./gui_files/icon.png")
        #app.setWindowIcon(icon)
        #ProgramStateSingleton().program_state.icon = icon
        window = MainWindow()
        #window.setWindowIcon(icon)
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        LoggerSingleton().logger.log_exception(e)


if __name__ == "__main__":
    start_gui()