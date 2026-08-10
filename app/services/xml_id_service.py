from __future__ import annotations


class XmlIdService:
    """
    Derive facsimile xml:id values in one place for UI and future export.

    Methods:
        surface_xml_id (int): Generates the surface xml:id.
        zone_xml_id (int, int): Generates the zone xml:id.
    """

    @classmethod
    def surface_xml_id(cls, surface_index: int) -> str:
        """
        Generates the surface xml:id.
        :param surface_index: Index of the surface.
        :return: Surface xml:id.
        """
        return f"facs_{surface_index + 1}"

    @classmethod
    def zone_xml_id(cls, surface_index: int, zone_index: int) -> str:
        """
        Generates the zone xml:id.

        :param surface_index: Index of the surface the zone is part of.
        :param zone_index: Index of the zone.
        :return: Zone xml:id.
        """
        return f"{cls.surface_xml_id(surface_index)}_zone_{zone_index + 1}"
