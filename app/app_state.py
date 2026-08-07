from __future__ import annotations

from dataclasses import dataclass, field

from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.settings_viewmodel import SettingsViewModel


@dataclass
class AppState:
    document: DocumentViewModel = field(default_factory=DocumentViewModel)
    settings: SettingsViewModel = field(default_factory=SettingsViewModel)
