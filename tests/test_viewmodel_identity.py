from __future__ import annotations

from app.models.document import Document, Surface, Zone
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.mapping_service import document_to_viewmodel
from app.viewmodels.document_viewmodel import DocumentViewModel


def test_nested_edits_preserve_unaffected_viewmodel_identity() -> None:
    document_vm = DocumentViewModel()
    document_to_viewmodel(
        Document(
            document_type="MEI",
            current_page_index=0,
            surfaces=(
                Surface(
                    image=b"one",
                    image_path="one.png",
                    zones=(Zone(1, 2, 3, 4), Zone(5, 6, 7, 8)),
                ),
                Surface(
                    image=b"two",
                    image_path="two.png",
                    zones=(Zone(9, 10, 11, 12),),
                ),
            ),
        ),
        document_vm,
    )
    service = DocumentService(DocumentRepository(), document_vm)

    first_surface = document_vm.surfaces[0]
    second_surface = document_vm.surfaces[1]
    first_zone = first_surface.zones[0]
    second_zone = first_surface.zones[1]
    other_surface_zone = second_surface.zones[0]

    service.add_zone(0, Zone(13, 14, 15, 16))

    assert document_vm.surfaces[0] is first_surface
    assert document_vm.surfaces[1] is second_surface
    assert first_surface.zones[0] is first_zone
    assert first_surface.zones[1] is second_zone
    assert second_surface.zones[0] is other_surface_zone

    added_zone = first_surface.zones[2]
    service.update_zone_rect(0, 1, 50, 60, 70, 80)

    assert document_vm.surfaces[0] is first_surface
    assert document_vm.surfaces[1] is second_surface
    assert first_surface.zones[0] is first_zone
    assert first_surface.zones[1] is second_zone
    assert first_surface.zones[2] is added_zone
    assert second_surface.zones[0] is other_surface_zone
    assert (second_zone.ulx, second_zone.uly, second_zone.lrx, second_zone.lry) == (
        50,
        60,
        70,
        80,
    )

    service.remove_zone(0, 0)

    assert document_vm.surfaces[0] is first_surface
    assert document_vm.surfaces[1] is second_surface
    assert first_surface.zones[0] is second_zone
    assert first_surface.zones[1] is added_zone
    assert second_surface.zones[0] is other_surface_zone


def test_add_surface_from_image_appends_page_and_preserves_existing_surfaces(tmp_path) -> None:
    image_path = tmp_path / "page-2.png"
    image_path.write_bytes(b"new-image")
    document_vm = DocumentViewModel()
    document_to_viewmodel(
        Document(
            document_type="MEI",
            current_page_index=0,
            surfaces=(
                Surface(
                    image=b"existing-image",
                    image_path="page-1.png",
                    zones=(Zone(1, 2, 3, 4),),
                ),
            ),
        ),
        document_vm,
    )
    service = DocumentService(DocumentRepository(), document_vm)
    existing_surface = document_vm.surfaces[0]

    assert service.add_surface_from_image(image_path) is True

    assert len(document_vm.surfaces) == 2
    assert document_vm.surfaces[0] is existing_surface
    assert document_vm.surfaces[1].image == b"new-image"
    assert document_vm.surfaces[1].image_path == str(image_path)
    assert document_vm.current_page_index == 1
    assert document_vm.selected_zone_index is None
    assert document_vm.dirty is True


def test_remove_current_surface_selects_valid_page_and_clears_selection() -> None:
    document_vm = DocumentViewModel()
    document_to_viewmodel(
        Document(
            document_type="MEI",
            current_page_index=1,
            surfaces=(
                Surface(image=b"one", image_path="one.png", zones=()),
                Surface(image=b"two", image_path="two.png", zones=(Zone(1, 2, 3, 4),)),
                Surface(image=b"three", image_path="three.png", zones=()),
            ),
        ),
        document_vm,
    )
    service = DocumentService(DocumentRepository(), document_vm)
    first_surface = document_vm.surfaces[0]
    third_surface = document_vm.surfaces[2]
    document_vm.selected_zone_index = 0

    service.remove_surface(1)

    assert document_vm.surfaces == (first_surface, third_surface)
    assert document_vm.current_page_index == 1
    assert document_vm.selected_zone_index is None
    assert document_vm.dirty is True


def test_remove_surface_before_current_shifts_current_index_and_preserves_surface() -> None:
    document_vm = DocumentViewModel()
    document_to_viewmodel(
        Document(
            document_type="MEI",
            current_page_index=2,
            surfaces=(
                Surface(image=b"one", image_path="one.png", zones=()),
                Surface(image=b"two", image_path="two.png", zones=()),
                Surface(image=b"three", image_path="three.png", zones=(Zone(1, 2, 3, 4),)),
            ),
        ),
        document_vm,
    )
    service = DocumentService(DocumentRepository(), document_vm)
    second_surface = document_vm.surfaces[1]
    current_surface = document_vm.surfaces[2]
    selected_zone = current_surface.zones[0]
    document_vm.selected_zone_index = 0

    service.remove_surface(0)

    assert document_vm.surfaces == (second_surface, current_surface)
    assert document_vm.surfaces[1].zones[0] is selected_zone
    assert document_vm.current_page_index == 1
    assert document_vm.selected_zone_index is None
    assert document_vm.dirty is True
