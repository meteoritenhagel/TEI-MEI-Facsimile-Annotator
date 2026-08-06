from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QTreeView

from src.program_state import Rectangle


class ZoneViewer(QTreeView):
    """
    Class ZoneViewer endows a QTreeView with zone handling capabilities.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel()
        self.setModel(self.model)

    def from_objects(self, zones: list[Rectangle]):
        """
        The ZoneViewer instance is set up with the zones that are provided.
        :param zones: List of zones.
        """
        self.model.clear()
        self.model.setHorizontalHeaderLabels(["Zone", "Coordinates"])

        if zones is not None:
            for idx, zone in enumerate(zones):
                zone_item = QStandardItem(f"Zone {idx+1}")
                coordinates = f"{int(zone.ulx)}, {int(zone.uly)}, {int(zone.lrx)}, {int(zone.lry)}"
                coordinates_item = QStandardItem(coordinates)
                self.model.appendRow([zone_item, coordinates_item])
