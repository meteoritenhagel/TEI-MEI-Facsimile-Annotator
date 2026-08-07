from __future__ import annotations

import sys

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from app.app_state import AppState
from app.repositories.document_repository import DocumentRepository
from app.repositories.settings_repository import SettingsRepository
from app.services.document_service import DocumentService
from app.services.settings_service import SettingsService
from app.services.xml_id_service import XmlIdService
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    document_repository = DocumentRepository()
    settings_repository = SettingsRepository()

    app_state = AppState()
    thread_pool = QThreadPool.globalInstance()

    document_service = DocumentService(document_repository, app_state.document, thread_pool)
    settings_service = SettingsService(settings_repository, app_state.settings)
    xml_id_service = XmlIdService()

    settings_service.load_settings()

    window = MainWindow(app_state.document, app_state.settings, document_service, settings_service, xml_id_service)
    document_service.new_document()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
