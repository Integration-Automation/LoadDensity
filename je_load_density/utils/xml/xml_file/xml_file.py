import xml.dom.minidom
from xml.etree import ElementTree
from xml.etree.ElementTree import ParseError
from typing import Optional

from je_load_density.utils.exception.exception_tags import cant_read_xml_error, xml_type_error
from je_load_density.utils.exception.exceptions import XMLException, XMLTypeException


def reformat_xml_file(xml_string: str) -> str:
    """
    將 XML 字串重新格式化為漂亮的排版
    Reformat XML string into pretty-printed format

    :param xml_string: 原始 XML 字串 (Raw XML string)
    :return: 格式化後的 XML 字串 (Pretty-printed XML string)
    """
    dom = xml.dom.minidom.parseString(xml_string)
    return dom.toprettyxml(indent="  ")


class XMLParser:
    """
    XML 解析器
    XML Parser

    支援從字串或檔案解析 XML，並能將 XML 寫入檔案。
    Supports parsing XML from string or file, and writing XML to file.
    """

    def __init__(self, xml_string: str, xml_type: str = "string") -> None:
        """
        初始化 XMLParser
        Initialize XMLParser

        :param xml_string: XML 字串或檔案路徑 (XML string or file path)
        :param xml_type: "string" 或 "file" (Parse from string or file)
        """
        self.tree: Optional[ElementTree.ElementTree] = None
        self.xml_root: Optional[ElementTree.Element] = None
        self.xml_from_type: str = "string"
        self.xml_string: str = xml_string.strip()

        xml_type = xml_type.lower()
        if xml_type not in ["file", "string"]:
            raise XMLTypeException(xml_type_error)

        if xml_type == "string":
            self.xml_parser_from_string()
        else:
            self.xml_parser_from_file()

    def xml_parser_from_string(self, **kwargs) -> ElementTree.Element:
        """
        從字串解析 XML
        Parse XML from string

        :param kwargs: 額外參數 (extra parameters)
        :return: XML 根節點 (XML root element)
        """
        try:
            self.xml_root = ElementTree.fromstring(self.xml_string, **kwargs)
        except ParseError as error:
            raise XMLException(f"{cant_read_xml_error}: {error}")
        return self.xml_root

    def xml_parser_from_file(self, **kwargs) -> ElementTree.Element:
        """
        從檔案解析 XML
        Parse XML from file

        :param kwargs: 額外參數 (extra parameters)
        :return: XML 根節點 (XML root element)
        """
        try:
            self.tree = ElementTree.parse(self.xml_string, **kwargs)
        except (ParseError, OSError) as error:
            raise XMLException(f"{cant_read_xml_error}: {error}")
        self.xml_root = self.tree.getroot()
        self.xml_from_type = "file"
        return self.xml_root

    def write_xml(self, write_xml_filename: str, write_content: str) -> None:
        """
        將 XML 字串寫入檔案
        Write XML string into file

        :param write_xml_filename: 輸出檔案名稱 (Output file name)
        :param write_content: XML 字串內容 (XML string content)
        """
        try:
            content = ElementTree.fromstring(write_content.strip())
            tree = ElementTree.ElementTree(content)
            tree.write(write_xml_filename, encoding="utf-8", xml_declaration=True)
        except ParseError as error:
            raise XMLException(f"{cant_read_xml_error}: {error}")