from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import override

from PySide6.QtCore import QEvent, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QDragEnterEvent,
    QDropEvent,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent, QResizeEvent,
)
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QApplication,
)

from app.models.document import Zone
from app.services.document_service import DocumentService
from app.services.image_service import apply_image_properties
from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.settings_viewmodel import SettingsViewModel
from app.viewmodels.surface_viewmodel import SurfaceViewModel
from app.viewmodels.zone_viewmodel import ZoneViewModel


@dataclass
class _DragState:
    mode: str
    start: QPointF
    zone_index: int | None = None
    original_rect: tuple[float, float, float, float] | None = None
    moved: bool = False
    drag_offset: QPointF | None = None


class FacsimileCanvas(QGraphicsView):
    """
    Widget for displaying and interacting with the image, drawing zones, etc.

    Methods:
        rebuild_for_current_page: Rebuild the widgets to correctly display the current page/surface.
        delete_selected_zone: Deletes the currently selected zone.

        resizeEvent (QResizeEvent): Event that is triggered when the widget is resized.
        viewportEvent (QViewportEvent): Event that is triggered for viewport-specific events, such as mouse
                wheel actions.
        wheelEvent (QWheelEvent): Event that is triggered when the mouse wheel is used.
        mousePressEvent (QMouseEvent): Event that is triggered when a mouse button is pressed.
        mouseMoveEvent (QMouseEvent): Event that is triggered when the mouse is moved.
        mouseReleaseEvent (QMouseEvent): Event that is triggered when a mouse button is released.
        keyPressEvent (QKeyEvent): Event that is triggered when a key is pressed.
        dragEnterEvent (QDragEnterEvent): Event that is triggered when a drag action enters the widget.
        dropEvent (QDropEvent): Event that is triggered when a drop action occurs on the widget.
    """
    _MIN_ZOOM = 0.05
    _MAX_ZOOM = 12.0
    _IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}

    def __init__(
        self,
        document_vm: DocumentViewModel,
        settings_vm: SettingsViewModel,
        document_service: DocumentService,
        parent=None,
    ) -> None:
        """
        Initialize the widget.

        :param document_vm: Document viewmodel.
        :param settings_vm: Settings viewmodel.
        :param document_service: Document service class.
        :param parent: Parent widget.
        """
        super().__init__(parent)
        self._document_vm = document_vm
        self._settings_vm = settings_vm
        self._document_service = document_service
        self._scene = QGraphicsScene(self)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zone_items: dict[int, QGraphicsRectItem] = {}
        self._zone_connections: list[ZoneViewModel] = []
        self._current_surface: SurfaceViewModel | None = None
        self._drag: _DragState | None = None
        self._draft_rect_item: QGraphicsRectItem | None = None
        self._image_rect = QRectF()
        self._user_zoomed = False

        self.setScene(self._scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(self._settings_vm.canvas_background_color))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        self._document_vm.surfaces_changed.connect(self.rebuild_for_current_page)
        self._document_vm.current_page_index_changed.connect(self.rebuild_for_current_page)
        self._document_vm.selected_zone_index_changed.connect(self._refresh_selection)
        self.rebuild_for_current_page()

        self._settings_vm.image_settings_changed.connect(self.rebuild_for_current_page)
        self._settings_vm.display_settings_changed.connect(self.rebuild_for_current_page)

    def rebuild_for_current_page(self) -> None:
        """
        Rebuild the widgets to correctly display the current page/surface.
        """
        self._disconnect_surface()
        self._scene.clear()
        self._zone_items.clear()
        self._pixmap_item = None
        self._draft_rect_item = None
        self._image_rect = QRectF()
        self._user_zoomed = False

        surface = self._current_page()
        if surface is None:
            self._scene.setSceneRect(0, 0, 900, 600)
            self.resetTransform()
            self.centerOn(self._scene.sceneRect().center())
            return

        self._current_surface = surface
        surface.image_changed.connect(self._load_image)
        surface.image_path_changed.connect(self._load_image)
        self._settings_vm.image_settings_changed.connect(self._load_image)
        surface.zones_changed.connect(self._rebuild_zones)
        self._load_image()
        self._rebuild_zones()

    def delete_selected_zone(self) -> None:
        """
        Deletes the currently selected zone.
        """
        selected = self._document_vm.selected_zone_index
        if selected is None:
            return
        self._document_service.remove_zone(self._document_vm.current_page_index, selected)

    @override
    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Event that is triggered when the widget is resized.

        :param event: QResizeEvent object containing the new and old size.
        """
        super().resizeEvent(event)
        self._update_scene_padding()
        if not self._user_zoomed:
            self._fit_and_center()

    @override
    def viewportEvent(self, event: QEvent) -> bool:
        """
        Event that is triggered for viewport-specific events, such as mouse wheel actions.

        :param event: QEvent object representing the viewport event.
        :return: True if the event was handled, otherwise False.
        """
        if event.type() == QEvent.Type.Wheel and self._is_ctrl_zoom_event(event):
            self._zoom_from_wheel(event)
            return True
        return super().viewportEvent(event)

    @override
    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Event that is triggered when the mouse wheel is used.

        :param event: QWheelEvent object containing information about the wheel action.
        """
        if self._is_ctrl_zoom_event(event):
            self._zoom_from_wheel(event)
            return
        super().wheelEvent(event)

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Event that is triggered when a mouse button is pressed.

        :param event: QMouseEvent object containing information about the mouse press.
        """
        if (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self._drag = _DragState(mode="pan", start=event.position())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if self._current_page() is None:
            return super().mousePressEvent(event)
        scene_pos = self.mapToScene(event.position().toPoint())
        if event.button() == Qt.MouseButton.RightButton:
            self._start_create(scene_pos)
            return
        if event.button() == Qt.MouseButton.LeftButton:
            zone_index = self._zone_at(scene_pos)
            if zone_index is not None:
                zone_vm = self._current_page().zones[zone_index]  # type: ignore[union-attr]
                self._drag = _DragState(
                    mode="move",
                    start=scene_pos,
                    zone_index=zone_index,
                    original_rect=(zone_vm.ulx, zone_vm.uly, zone_vm.lrx, zone_vm.lry),
                )
                self._document_service.select_zone(zone_index)
                return
            self._document_service.select_zone(None)
        super().mousePressEvent(event)

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Event that is triggered when the mouse is moved.

        :param event: QMouseEvent object containing information about the mouse movement.
        """
        if self._drag is None:
            return super().mouseMoveEvent(event)
        if self._drag.mode == "pan":
            previous = self._drag.start
            current = event.position()
            delta = current - previous
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            self._drag.start = current
            event.accept()
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        if self._drag.mode == "create":
            self._drag.moved = True
            self._update_draft_rect(self._drag.start, scene_pos)
            return
        if self._drag.mode == "move" and self._drag.zone_index is not None:
            self._drag.moved = True
            ulx, uly, lrx, lry = self._drag.original_rect or (0, 0, 0, 0)
            delta = scene_pos - self._drag.start
            self._drag.drag_offset = delta  # Store the offset for use in mouseReleaseEvent

            # Update the QGraphicsRectItem visually, but do not update the viewmodel yet! Only on mouse release
            item = self._zone_items.get(self._drag.zone_index)
            if item is not None:
                item.setRect(
                    ulx + delta.x(),
                    uly + delta.y(),
                    (lrx - ulx),
                    (lry - uly),
                )
            return
        super().mouseMoveEvent(event)

    @override
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """
        Event that is triggered when a mouse button is released.

        :param event: QMouseEvent object containing information about the mouse release.
        """
        if self._drag is None:
            super().mouseReleaseEvent(event)
            return
        scene_pos = self.mapToScene(event.position().toPoint())
        drag = self._drag
        self._drag = None
        if drag.mode == "pan":
            self.unsetCursor()
            event.accept()
            return
        if drag.mode == "create":
            self._finish_create(drag.start, scene_pos)
            return
        if drag.mode == "move" and drag.zone_index is not None:
            if drag.moved:
                ulx, uly, lrx, lry = drag.original_rect or (0, 0, 0, 0)
                delta = drag.drag_offset
                self._document_service.update_zone_rect(
                    self._document_vm.current_page_index,
                    drag.zone_index,
                    ulx + delta.x(),
                    uly + delta.y(),
                    lrx + delta.x(),
                    lry + delta.y(),
                )
            else:
                self._document_service.select_zone(drag.zone_index)
            return
        super().mouseReleaseEvent(event)

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Event that is triggered when a key is pressed.

        :param event: QKeyEvent object containing information about the key press.
        """
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_zone()
            return
        super().keyPressEvent(event)

    @override
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Event that is triggered when a drag action enters the widget.

        :param event: QDragEnterEvent object containing information about the drag action.
        """
        if self._drop_image_path(event) is not None:
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    @override
    def dropEvent(self, event: QDropEvent) -> None:
        """
        Event that is triggered when a drop action occurs on the widget.

        :param event: QDropEvent object containing information about the drop action.
        """
        path = self._drop_image_path(event)
        if path is None:
            return super().dropEvent(event)
        if self._document_service.add_surface_from_image(path):
            event.acceptProposedAction()

    def _start_create(self, scene_pos: QPointF) -> None:
        self._drag = _DragState(mode="create", start=scene_pos)
        brush_color = self._settings_vm.create_zone_fill_color
        brush_color.setAlpha(self._settings_vm.create_zone_fill_opacity)
        self._draft_rect_item = self._scene.addRect(
            scene_pos.x(),
            scene_pos.y(),
            0,
            0,
            QPen(self._settings_vm.create_zone_border_color, self._settings_vm.create_zone_border_thickness, Qt.PenStyle.DashLine),
            QBrush(brush_color),
        )
        self._draft_rect_item.setZValue(20)

    def _update_draft_rect(self, start: QPointF, end: QPointF) -> None:
        if self._draft_rect_item is None:
            return
        ulx, uly, lrx, lry = self._normalized_rect(start, end)
        self._draft_rect_item.setRect(ulx, uly, lrx - ulx, lry - uly)

    def _finish_create(self, start: QPointF, end: QPointF) -> None:
        if self._draft_rect_item is not None:
            self._scene.removeItem(self._draft_rect_item)
            self._draft_rect_item = None
        ulx, uly, lrx, lry = self._normalized_rect(start, end)
        if abs(lrx - ulx) < 2 or abs(lry - uly) < 2:
            return
        self._document_service.add_zone(
            self._document_vm.current_page_index,
            Zone(ulx=ulx, uly=uly, lrx=lrx, lry=lry),
        )

    def _normalized_rect(self, start: QPointF, end: QPointF) -> tuple[int, int, int, int]:
        return (
            int(min(start.x(), end.x())),
            int(min(start.y(), end.y())),
            int(max(start.x(), end.x())),
            int(max(start.y(), end.y())),
        )

    def _zone_at(self, scene_pos: QPointF) -> int | None:
        for index in sorted(self._zone_items.keys(), reverse=True):
            if self._zone_items[index].rect().contains(scene_pos):
                return index
        return None

    def _fit_and_center(self) -> None:
        rect = self._image_rect if not self._image_rect.isEmpty() else self._scene.sceneRect()
        if rect.isEmpty():
            return
        self.resetTransform()
        self.fitInView(rect, Qt.AspectRatioMode.KeepAspectRatio)
        self.centerOn(rect.center())

    def _update_scene_padding(self) -> None:
        if self._image_rect.isEmpty():
            return
        viewport_size = self.viewport().size()
        visible_width = max(1, viewport_size.width())
        visible_height = max(1, viewport_size.height())
        current_scale = max(self.transform().m11(), self._MIN_ZOOM)
        margin_x = max(self._image_rect.width() * 0.25, visible_width / current_scale)
        margin_y = max(self._image_rect.height() * 0.25, visible_height / current_scale)
        self._scene.setSceneRect(self._image_rect.adjusted(-margin_x, -margin_y, margin_x, margin_y))

    def _is_ctrl_zoom_event(self, event) -> bool:
        modifiers = event.modifiers() | QApplication.keyboardModifiers()
        return bool(modifiers & Qt.KeyboardModifier.ControlModifier)

    def _zoom_from_wheel(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y() or event.pixelDelta().y()
        if delta == 0:
            event.accept()
            return
        current = self.transform().m11()
        if current <= 0:
            current = 1.0
        factor = 1.0015**delta
        target = max(self._MIN_ZOOM, min(self._MAX_ZOOM, current * factor))
        if target != current:
            self.scale(target / current, target / current)
            self._user_zoomed = True
            self._update_scene_padding()
        event.accept()

    def _drop_image_path(self, event: QDragEnterEvent | QDropEvent) -> Path | None:
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() in self._IMAGE_EXTENSIONS:
                return path
        return None

    def _disconnect_surface(self) -> None:
        if self._current_surface is not None:
            try:
                self._current_surface.image_changed.disconnect(self._load_image)
                self._current_surface.image_path_changed.disconnect(self._load_image)
                self._current_surface.zones_changed.disconnect(self._rebuild_zones)
            except RuntimeError:
                pass
        self._disconnect_zones()
        self._current_surface = None

    def _disconnect_zones(self) -> None:
        for zone_vm in self._zone_connections:
            try:
                zone_vm.rect_changed.disconnect(self._update_zone_item)
            except RuntimeError:
                pass
        self._zone_connections.clear()

    def _current_page(self) -> SurfaceViewModel | None:
        surfaces = self._document_vm.surfaces
        index = self._document_vm.current_page_index
        if not 0 <= index < len(surfaces):
            return None
        return surfaces[index]

    def _load_image(self, *_args) -> None:
        surface = self._current_page()
        if surface is None:
            return
        pixmap = QPixmap()
        if surface.image:
            img_data = apply_image_properties(
                surface.image,
                self._settings_vm.image_brightness,
                self._settings_vm.image_contrast,
                self._settings_vm.image_saturation
            )

            pixmap.loadFromData(img_data)
        if pixmap.isNull():
            self._scene.setSceneRect(0, 0, 900, 600)
            self._image_rect = QRectF()
            self.resetTransform()
            self.centerOn(self._scene.sceneRect().center())
            return
        if self._pixmap_item is None:
            self._pixmap_item = self._scene.addPixmap(pixmap)
            self._pixmap_item.setZValue(0)
        else:
            self._pixmap_item.setPixmap(pixmap)
        self._pixmap_item.setOffset(0, 0)
        self._image_rect = QRectF(pixmap.rect())
        self._update_scene_padding()
        self._fit_and_center()

    def _rebuild_zones(self) -> None:
        self._disconnect_zones()
        for item in self._zone_items.values():
            self._scene.removeItem(item)
        self._zone_items.clear()

        surface = self._current_page()
        if surface is None:
            return
        for index, zone_vm in enumerate(surface.zones):
            item = self._make_rect_item(zone_vm, index)
            self._zone_items[index] = item
            zone_vm.rect_changed.connect(self._update_zone_item)
            self._zone_connections.append(zone_vm)
        self._refresh_selection()

    def _make_rect_item(self, zone_vm: ZoneViewModel, index: int) -> QGraphicsRectItem:
        brush_color = self._settings_vm.unselected_zone_fill_color
        brush_color.setAlpha(self._settings_vm.unselected_zone_fill_opacity)
        item = self._scene.addRect(
            zone_vm.ulx,
            zone_vm.uly,
            zone_vm.lrx - zone_vm.ulx,
            zone_vm.lry - zone_vm.uly,
            self._pen_for_zone(index),
            QBrush(brush_color),
        )
        item.setZValue(10)
        item.setData(0, index)
        return item

    def _update_zone_item(self, *_args) -> None:
        surface = self._current_page()
        if surface is None:
            return
        sender = self.sender()
        for index, zone_vm in enumerate(surface.zones):
            if zone_vm is sender and index in self._zone_items:
                self._zone_items[index].setRect(
                    zone_vm.ulx,
                    zone_vm.uly,
                    zone_vm.lrx - zone_vm.ulx,
                    zone_vm.lry - zone_vm.uly,
                )
                return

    def _refresh_selection(self, *_args) -> None:
        for index, item in self._zone_items.items():
            item.setPen(self._pen_for_zone(index))
            selected = index == self._document_vm.selected_zone_index
            brush_color = self._settings_vm.selected_zone_fill_color if selected else self._settings_vm.unselected_zone_fill_color
            brush_color.setAlpha(self._settings_vm.selected_zone_fill_opacity if selected else self._settings_vm.unselected_zone_fill_opacity)
            item.setBrush(QBrush(brush_color))

    def _pen_for_zone(self, index: int) -> QPen:
        selected = index == self._document_vm.selected_zone_index
        pen = QPen(
            self._settings_vm.selected_zone_border_color if selected else self._settings_vm.unselected_zone_border_color
        )
        pen.setWidthF(self._settings_vm.selected_zone_border_thickness if selected else self._settings_vm.unselected_zone_border_thickness)
        return pen
