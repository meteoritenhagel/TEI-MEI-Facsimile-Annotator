from __future__ import annotations

from app.models.document import Document, Surface, Zone
from app.services.mapping_service import (
    document_to_viewmodel,
    surface_to_viewmodel,
    viewmodel_to_document,
    viewmodel_to_surface,
    viewmodel_to_zone,
    zone_to_viewmodel,
)
from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.surface_viewmodel import SurfaceViewModel
from app.viewmodels.zone_viewmodel import ZoneViewModel


def test_zone_mapping_round_trip() -> None:
    zone = Zone(1.0, 2.0, 3.0, 4.0)
    vm = ZoneViewModel()

    zone_to_viewmodel(zone, vm)

    assert (vm.ulx, vm.uly, vm.lrx, vm.lry) == (1.0, 2.0, 3.0, 4.0)
    assert viewmodel_to_zone(vm) == zone


def test_surface_mapping_round_trip() -> None:
    surface = Surface(
        image=b"image",
        image_path="images/page.png",
        zones=(Zone(1.0, 2.0, 3.0, 4.0), Zone(5.0, 6.0, 7.0, 8.0)),
    )
    vm = SurfaceViewModel()

    surface_to_viewmodel(surface, vm)

    assert vm.image == b"image"
    assert vm.image_path == "images/page.png"
    assert len(vm.zones) == 2
    assert viewmodel_to_surface(vm) == surface


def test_document_mapping_round_trip_does_not_touch_transient_selection() -> None:
    document = Document(
        document_type="TEI",
        current_page_index=1,
        surfaces=(
            Surface(image=b"one", image_path="one.png", zones=()),
            Surface(image=b"two", image_path="two.png", zones=(Zone(9, 10, 11, 12),)),
        ),
    )
    vm = DocumentViewModel()
    vm.selected_zone_index = 42

    document_to_viewmodel(document, vm)

    assert vm.selected_zone_index == 42
    assert viewmodel_to_document(vm) == document
