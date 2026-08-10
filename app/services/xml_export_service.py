import io
import os

from PIL import Image
from bs4 import BeautifulSoup, Tag
from lxml import etree

from app.constants import IMAGE_DIRECTORY, APPLICATION_NAME, DOMAIN_NAME
from app.services.xml_id_service import XmlIdService
from app.viewmodels.document_viewmodel import DocumentViewModel


def viewmodel_to_xml(vm: DocumentViewModel) -> str:
    """
    Returns a string representation of the TEI/MEI XML data to be exported.

    :param vm: Document viewmodel.
    :return: String representation of the TEI/MEI XML data.
    """
    if vm.document_type == "TEI":
        return _viewmodel_to_tei(vm)
    elif vm.document_type == "MEI":
        return _viewmodel_to_mei(vm)
    else:
        raise NotImplementedError(f"{vm.document_type} is not supported.")


def _beautifulsoup_to_pretty_string(bs: BeautifulSoup) -> str:
    xml_bytes = str(bs).encode("utf-8")
    root = etree.fromstring(xml_bytes)
    pretty_xml = etree.tostring(root, pretty_print=True, encoding="unicode")
    return pretty_xml


def _viewmodel_to_tei(vm: DocumentViewModel) -> str:
    """
    Builds a minimal TEI containing the facsimile information from the viewmodel.

    :param vm: Document viewmodel.
    :return: String containing the TEI XML data.
    """
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_model_1 = ('<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" '
                   'type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
    xml_model_2 = ('<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" '
                   'type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>\n')

    # Create the root TEI element with the namespace
    tei = BeautifulSoup(features="xml")
    root_element = tei.new_tag("TEI", xmlns="http://www.tei-c.org/ns/1.0")
    tei.append(root_element)

    # Build teiHeader
    teiHeader = tei.new_tag("teiHeader")
    fileDesc = tei.new_tag("fileDesc")

    # titleStmt
    titleStmt = tei.new_tag("titleStmt")
    title = tei.new_tag("title")
    title.string = _viewmodel_to_title_string(vm)
    titleStmt.append(title)
    fileDesc.append(titleStmt)

    # publicationStmt
    publicationStmt = tei.new_tag("publicationStmt")

    p_pub = tei.new_tag("p")
    p_pub.append("Document created using: ")
    ref = tei.new_tag("ref", target=DOMAIN_NAME)
    ref.string = APPLICATION_NAME
    p_pub.append(ref)
    p_pub.append(".")

    publicationStmt.append(p_pub)
    fileDesc.append(publicationStmt)

    # sourceDesc
    sourceDesc = tei.new_tag("sourceDesc")
    p_source = tei.new_tag("p")
    p_source.string = "Information about the source"
    sourceDesc.append(p_source)
    fileDesc.append(sourceDesc)

    teiHeader.append(fileDesc)
    root_element.append(teiHeader)

    # Build facsimile element
    if len(vm.surfaces) > 0:
        facsimile_element = _viewmodel_to_facsimile(vm, "TEI", tei)
        root_element.append(facsimile_element)

    # Build text/body
    text = tei.new_tag("text")
    body = tei.new_tag("body")
    p_body = tei.new_tag("p")

    # Build pb and lb elements from viewmodel
    for milestone_element in _viewmodel_to_milestones(vm, "TEI", tei):
        p_body.append(milestone_element)

    body.append(p_body)
    text.append(body)
    root_element.append(text)

    return xml_declaration + xml_model_1 + xml_model_2 + _beautifulsoup_to_pretty_string(tei)


def _viewmodel_to_mei(vm: DocumentViewModel) -> str:
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_model_1 = ('<?xml-model href="https://music-encoding.org/schema/5.1/mei-all.rng" type="application/xml" '
                   'schematypens="http://relaxng.org/ns/structure/1.0"?>\n')
    xml_model_2 = ('<?xml-model href="https://music-encoding.org/schema/5.1/mei-all.rng" type="application/xml" '
                   'schematypens="http://purl.oclc.org/dsdl/schematron"?>\n')

    # Create the root mei element with namespace and version
    mei = BeautifulSoup(features="xml")
    root_element = mei.new_tag("mei", xmlns="http://www.music-encoding.org/ns/mei", meiversion="5.1")
    mei.append(root_element)

    # Build meiHead
    meiHead = mei.new_tag("meiHead")
    fileDesc = mei.new_tag("fileDesc")

    # titleStmt
    titleStmt = mei.new_tag("titleStmt")
    title = mei.new_tag("title")
    title.string = _viewmodel_to_title_string(vm)
    titleStmt.append(title)
    fileDesc.append(titleStmt)

    # pubStmt
    pubStmt = mei.new_tag("pubStmt")
    respStmt = mei.new_tag("respStmt")
    resp = mei.new_tag("resp")
    resp.string = "Document created using:"
    name = mei.new_tag("name")
    name.string = f"{APPLICATION_NAME} ({DOMAIN_NAME})"
    respStmt.append(resp)
    respStmt.append(name)
    pubStmt.append(respStmt)
    fileDesc.append(pubStmt)

    meiHead.append(fileDesc)
    root_element.append(meiHead)

    # Build music/body/mdiv/score/sb
    music = mei.new_tag("music")

    # Build facsimile element
    if len(vm.surfaces) > 0:
        facsimile_element = _viewmodel_to_facsimile(vm, "MEI", mei)
        music.append(facsimile_element)

    body = mei.new_tag("body")
    mdiv = mei.new_tag("mdiv")
    score = mei.new_tag("score")

    # Build pb and sb elements from viewmodel
    for milestone_element in _viewmodel_to_milestones(vm, "MEI", mei):
        score.append(milestone_element)

    mdiv.append(score)
    body.append(mdiv)
    music.append(body)
    root_element.append(music)

    return xml_declaration + xml_model_1 + xml_model_2 + _beautifulsoup_to_pretty_string(mei)


def _viewmodel_to_facsimile(vm: DocumentViewModel, document_type: str, parent: BeautifulSoup) -> Tag:
    if document_type == "TEI":
        image_path_tag = "url"
        surface_suffix = "px"
    elif document_type == "MEI":
        image_path_tag = "target"
        surface_suffix = ""
    else:
        raise NotImplementedError(f"Unsupported document type: {document_type}")

    facsimile_element = parent.new_tag("facsimile")
    for surface_index, surface in enumerate(vm.surfaces):
        img = Image.open(io.BytesIO(surface.image))
        surface_element = parent.new_tag(
            "surface",
            ulx="0",
            uly="0",
            lrx=f"{img.width}",
            lry=f"{img.height}",
        )
        surface_element.attrs["xml:id"] = f"{XmlIdService.surface_xml_id(surface_index)}"

        # Add graphic elements
        graphic_element = parent.new_tag(
            "graphic",
            width=f"{img.width}{surface_suffix}",
            height=f"{img.height}{surface_suffix}",
        )
        graphic_element.attrs[image_path_tag] = f"{os.path.join(IMAGE_DIRECTORY, os.path.basename(surface.image_path))}"
        surface_element.append(graphic_element)

        # Add zone elements
        for zone_index, zone in enumerate(surface.zones):
            zone_element = parent.new_tag(
                "zone",
                ulx=f"{zone.ulx}",
                uly=f"{zone.uly}",
                lrx=f"{zone.lrx}",
                lry=f"{zone.lry}",
            )
            zone_element.attrs["xml:id"] = f"{XmlIdService.zone_xml_id(surface_index, zone_index)}"
            surface_element.append(zone_element)

        facsimile_element.append(surface_element)
    return facsimile_element


def _viewmodel_to_milestones(vm: DocumentViewModel, document_type: str, parent: BeautifulSoup) -> list[Tag]:
    tags = []

    if document_type == "TEI":
        line_break_tag = "lb"
    elif document_type == "MEI":
        line_break_tag = "sb"
    else:
        raise NotImplementedError(f"Unsupported document type: {document_type}")

    for surface_index, surface in enumerate(vm.surfaces):
        pb_element = parent.new_tag(
            "pb", n=f"{surface_index+1}", facs=f"#{XmlIdService.surface_xml_id(surface_index)}"
        )
        tags.append(pb_element)

        for zone_index, zone in enumerate(surface.zones):
            line_break_element = parent.new_tag(
                line_break_tag, facs=f"#{XmlIdService.zone_xml_id(surface_index, zone_index)}"
            )
            tags.append(line_break_element)

    return tags

def _viewmodel_to_title_string(vm: DocumentViewModel) -> str:
    string = os.path.basename(vm.file_path) if vm.file_path else "Untitled"
    string += " Facsimile Data Export"
    return string