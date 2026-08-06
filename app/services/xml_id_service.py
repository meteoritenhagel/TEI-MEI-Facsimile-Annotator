from __future__ import annotations


class XmlIdService:
    """Derive facsimile xml:id values in one place for UI and future export."""

    def surface_xml_id(self, surface_index: int) -> str:
        return f"facs_{surface_index + 1}"

    def zone_xml_id(self, surface_index: int, zone_index: int) -> str:
        return f"{self.surface_xml_id(surface_index)}_zone_{zone_index + 1}"
