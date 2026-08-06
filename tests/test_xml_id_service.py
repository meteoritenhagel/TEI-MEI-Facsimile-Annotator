from __future__ import annotations

from app.services.xml_id_service import XmlIdService


def test_surface_xml_ids_are_one_based() -> None:
    service = XmlIdService()

    assert service.surface_xml_id(0) == "facs_1"
    assert service.surface_xml_id(9) == "facs_10"
    assert service.surface_xml_id(12) == "facs_13"


def test_zone_xml_ids_include_surface_and_zone_positions() -> None:
    service = XmlIdService()

    assert service.zone_xml_id(0, 0) == "facs_1_zone_1"
    assert service.zone_xml_id(2, 1) == "facs_3_zone_2"
    assert service.zone_xml_id(10, 14) == "facs_11_zone_15"
