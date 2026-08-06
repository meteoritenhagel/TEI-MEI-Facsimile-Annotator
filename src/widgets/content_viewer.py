from PySide6.QtWidgets import QTextEdit

from src.program_state import ObjectHandler, ProgramStateSingleton


class ContentViewer(QTextEdit):
    """
    FacsimileViewer endows a QTextEdit with functions for content (i.e. text or music) data display.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def from_state(self, handler: ObjectHandler):
        default_tab = "    "
        display_text = ""

        for page_idx, state in enumerate(handler):
            display_text += default_tab + (f'<pb facs="#facs_{page_idx+1}"/>\n')
            for zone_idx, obj in enumerate(state.objects):
                display_text += 2*default_tab + (f'<lb facs="#facs_{page_idx+1}_zone_{zone_idx+1}"/>\n')

        self.setText(display_text)


