from __future__ import annotations

from app.models.document import Document, Surface, Zone
from app.viewmodels.document_viewmodel import DocumentViewModel
from app.viewmodels.surface_viewmodel import SurfaceViewModel
from app.viewmodels.zone_viewmodel import ZoneViewModel


def zone_to_viewmodel(zone: Zone, vm: ZoneViewModel) -> None:
    vm.set_rect(zone.ulx, zone.uly, zone.lrx, zone.lry)


def viewmodel_to_zone(vm: ZoneViewModel) -> Zone:
    return Zone(ulx=vm.ulx, uly=vm.uly, lrx=vm.lrx, lry=vm.lry)


def surface_to_viewmodel(surface: Surface, vm: SurfaceViewModel) -> None:
    zones = []
    for zone in surface.zones:
        zone_vm = ZoneViewModel(parent=vm)
        zone_to_viewmodel(zone, zone_vm)
        zones.append(zone_vm)
    vm.image = surface.image
    vm.image_path = surface.image_path
    vm.zones = tuple(zones)


def viewmodel_to_surface(vm: SurfaceViewModel) -> Surface:
    return Surface(
        image=vm.image,
        image_path=vm.image_path,
        zones=tuple(viewmodel_to_zone(zone_vm) for zone_vm in vm.zones),
    )


def document_to_viewmodel(doc: Document, vm: DocumentViewModel) -> None:
    surfaces = []
    for surface in doc.surfaces:
        surface_vm = SurfaceViewModel(parent=vm)
        surface_to_viewmodel(surface, surface_vm)
        surfaces.append(surface_vm)
    vm.surfaces = tuple(surfaces)
    vm.document_type = doc.document_type
    vm.current_page_index = doc.current_page_index


def viewmodel_to_document(vm: DocumentViewModel) -> Document:
    return Document(
        surfaces=tuple(viewmodel_to_surface(surface_vm) for surface_vm in vm.surfaces),
        document_type=vm.document_type,
        current_page_index=vm.current_page_index,
    )
