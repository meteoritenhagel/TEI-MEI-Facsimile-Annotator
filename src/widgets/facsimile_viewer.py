from PySide6.QtWidgets import QTextEdit

from src.program_state import ObjectHandler


class FacsimileViewer(QTextEdit):
    """
    FacsimileViewer endows a QTextEdit with functions for facsimile data display.
    """
    def __init__(self, parent=None):
        super().__init__(parent)

    def from_state(self, handler: ObjectHandler):
        default_tab = "    "
        display_text = ""

        display_text += "<facsimile>\n"
        for idx, state in enumerate(handler):
            #display_text += default_tab + f"<surface lrx="{}" lry="{}" ulx="{}" uly="{}">\n"

            display_text += default_tab + "</surface>\n"
        display_text += "</facsimile>"


