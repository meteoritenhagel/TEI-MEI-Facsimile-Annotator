from PIL import Image, ImageQt
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPixmap, QPen
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMainWindow

from src.logger import LoggerSingleton
from src.program_state import ProgramStateSingleton


class ImageGraphicsView(QGraphicsView):
    """
    ImageGraphicsView endows QGraphicsView with scrolling and panning functionality.

    Attributes:
        scene (QGraphicsScene): The scene containing the objects that are displayed in the QGraphicsView.

    Methods:
        wheelEvent (QEvent): Overrides QGraphicsView.wheelEvent. Adds scaling of the view using the mouse wheel.
        keyPressEvent (QEvent): Overrides QGraphicsView.keyPressEvent. We don't need key responsiveness here.
        load_image_from_pil (Image.Image): Loads a PIL Image into the scene causing it to be displayed.
    """
    def __init__(self, parent: QMainWindow = None, enabled: bool = True):
        """
        Constructor.
        :param parent: Parent window.
        :param enabled: Whether the widget should be enabled on construction.
        """
        super().__init__(parent.centralWidget())
        self._main_window = parent
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self.scene = QGraphicsScene(self)

        self.setScene(self.scene)
        self.setEnabled(enabled)

        # --- Rectangle selection state ---
        self._rect_selecting = False
        self._rect_start = None
        self._rect_end = None
        self._rubber_band_rect = None  # QRectF

    def mousePressEvent(self, event):
        scene_coordinates = self.mapToScene(event.pos())
        scene_x, scene_y = int(scene_coordinates.x()), int(scene_coordinates.y())

        LoggerSingleton().logger.log_user_interaction(
            f"imageGraphicsView.mousePressEvent ("
            f"button = {event.button()}, "
            f"pos = {event.pos().x(), event.pos().y()}, "
            f"scene_coordinates = {(scene_x, scene_y)}"
            f")"
        )

        if event.button() == Qt.MouseButton.RightButton:
            # --- Begin rectangle selection ---
            self._rect_selecting = True
            self._rect_start = scene_coordinates
            self._rect_end = scene_coordinates
            self._rubber_band_rect = None
            self.viewport().update()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rect_selecting:
            self._rect_end = self.mapToScene(event.pos())
            self.viewport().update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._rect_selecting and event.button() == Qt.MouseButton.RightButton:
            self._rect_end = self.mapToScene(event.pos())
            self._rect_selecting = False
            self._rubber_band_rect = QRectF(self._rect_start, self._rect_end).normalized()
            self.viewport().update()
            # Rectangle is now available in self._rubber_band_rect
            program_state = ProgramStateSingleton().program_state
            program_state.add_object(self._rubber_band_rect.getCoords())
        else:
            super().mouseReleaseEvent(event)

    def drawForeground(self, painter, rect):
        super().drawForeground(painter, rect)
        if self._rect_selecting and self._rect_start and self._rect_end:
            pen = QPen(Qt.GlobalColor.red, 2, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            selection_rect = QRectF(self._rect_start, self._rect_end).normalized()
            painter.drawRect(selection_rect)

    def get_selected_rectangle(self):
        """Returns the selected rectangle as (x, y, width, height) or None."""
        if self._rubber_band_rect:
            return self._rubber_band_rect.getRect()
        return None

    def wheelEvent(self, event):
        """
        Overrides QGraphicsView.wheelEvent. Adds scaling of the view using the mouse wheel.
        :param event: Passed wheel event.
        """
        LoggerSingleton().logger.log_user_interaction(
            f"imageGraphicsView.wheelEvent (angleDelta = {event.angleDelta()})"
        )
        factor = 1.2  # scaling factor. Larger values mean more scaling per wheel.
        if event.angleDelta().y() < 0:
            factor = 1.0 / factor
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        """
        Overrides QGraphicsView.keyPressEvent. We don't need key responsiveness here.
        :param event: Passed event.
        """
        event.ignore()

    def load_image_from_pil(self, image: Image.Image):
        """
        Loads a PIL Image into the scene causing it to be displayed.
        :param image: PIL Image.
        """
        pixmap = QPixmap.fromImage(ImageQt.ImageQt(image))
        image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(image_item)
        self.setSceneRect(QRectF(pixmap.rect()))
        self.setEnabled(True)
