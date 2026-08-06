from __future__ import annotations

import sys

from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from app.app_state import AppState
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.xml_id_service import XmlIdService
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    repository = DocumentRepository()
    app_state = AppState()
    thread_pool = QThreadPool.globalInstance()
    document_service = DocumentService(repository, app_state.document, thread_pool)
    xml_id_service = XmlIdService()
    window = MainWindow(app_state.document, document_service, xml_id_service)
    document_service.new_document()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
