from PySide6.QtWidgets import QTextEdit

from src.program_state import ObjectHandler, ProgramStateSingleton


class FacsimileViewer(QTextEdit):
    """
    FacsimileViewer endows a QTextEdit with functions for facsimile data display.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)

    def from_state(self, handler: ObjectHandler):
        default_tab = "    "
        display_text = ""

        program_state = ProgramStateSingleton().program_state

        display_text += "<facsimile>\n"

        for page_idx, state in enumerate(handler):
            width = program_state.project_images[page_idx].width
            height = program_state.project_images[page_idx].height
            filename = program_state.path_to_images[page_idx]
            display_text += default_tab + (f'<surface ulx="0" uly="0" '
                                           f'lrx="{width}" lry="{height}" xml:id="facs_{page_idx+1}">\n')
            display_text += 2*default_tab + f'<graphic width="{width}" height="{height}" target="{filename}"/>\n'  # TODO: MEI uses @target, TEI uses @url
            for zone_idx, obj in enumerate(state.objects):
                display_text += 2*default_tab + (f'<zone ulx="{int(obj.ulx)}" uly="{int(obj.uly)}" '
                                                 f'lrx="{int(obj.lrx)}" lry="{int(obj.lry)}" '
                                                 f'xml:id="facs_{page_idx+1}_zone_{zone_idx+1}"/>\n')

            display_text += default_tab + "</surface>\n"
        display_text += "</facsimile>"

        self.setText(display_text)


