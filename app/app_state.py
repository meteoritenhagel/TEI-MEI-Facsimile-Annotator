from __future__ import annotations

from dataclasses import dataclass, field

from app.viewmodels.document_viewmodel import DocumentViewModel


@dataclass
class AppState:
    document: DocumentViewModel = field(default_factory=DocumentViewModel)
