import pytest

from je_load_density.utils.xml.xml_file.xml_file import XMLParser, reformat_xml_file
from je_load_density.utils.xml.change_xml_structure.change_xml_structure import (
    dict_to_elements_tree,
    elements_tree_to_dict,
)
from je_load_density.utils.exception.exceptions import XMLException, XMLTypeException


class TestReformatXml:

    def test_reformat(self):
        raw = "<root><child>text</child></root>"
        result = reformat_xml_file(raw)
        assert "<root>" in result
        assert "<child>" in result
        assert "text" in result


class TestXMLParser:

    def test_parse_from_string(self):
        xml_str = "<root><item>hello</item></root>"
        parser = XMLParser(xml_str, xml_type="string")
        assert parser.xml_root is not None
        assert parser.xml_root.tag == "root"

    def test_parse_from_string_default(self):
        xml_str = "<data><value>123</value></data>"
        parser = XMLParser(xml_str)
        assert parser.xml_root.tag == "data"

    def test_invalid_xml_type_raises(self):
        with pytest.raises(XMLTypeException):
            XMLParser("<root/>", xml_type="invalid")

    def test_invalid_xml_string_raises(self):
        with pytest.raises(XMLException):
            XMLParser("not xml at all <<<")

    def test_parse_from_file(self, tmp_path):
        xml_file = tmp_path / "test.xml"
        xml_file.write_text("<root><a>1</a></root>", encoding="utf-8")
        parser = XMLParser(str(xml_file), xml_type="file")
        assert parser.xml_root.tag == "root"

    def test_write_xml(self, tmp_path):
        parser = XMLParser("<root/>")
        out_file = str(tmp_path / "out.xml")
        parser.write_xml(out_file, "<root><child>data</child></root>")
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "child" in content


class TestDictToElementsTree:

    def test_simple_dict(self):
        data = {"root": {"child": "value"}}
        result = dict_to_elements_tree(data)
        assert "<root>" in result
        assert "<child>value</child>" in result

    def test_nested_dict(self):
        data = {"root": {"parent": {"child": "text"}}}
        result = dict_to_elements_tree(data)
        assert "<parent>" in result
        assert "<child>text</child>" in result

    def test_list_elements(self):
        data = {"root": {"item": ["a", "b", "c"]}}
        result = dict_to_elements_tree(data)
        assert result.count("<item>") == 3

    def test_invalid_input_raises(self):
        with pytest.raises(ValueError):
            dict_to_elements_tree({"a": 1, "b": 2})

    def test_empty_root(self):
        data = {"root": {}}
        result = dict_to_elements_tree(data)
        assert "<root" in result


class TestElementsTreeToDict:

    def test_simple(self):
        from xml.etree.ElementTree import fromstring
        elem = fromstring("<root><child>hello</child></root>")
        result = elements_tree_to_dict(elem)
        assert result["root"]["child"] == "hello"

    def test_with_attributes(self):
        from xml.etree.ElementTree import fromstring
        elem = fromstring('<root id="1"><child>text</child></root>')
        result = elements_tree_to_dict(elem)
        assert result["root"]["@id"] == "1"
        assert result["root"]["child"] == "text"


class TestRoundTrip:

    def test_dict_to_xml_structure(self):
        data = {
            "xml_data": {
                "Success_Test1": {
                    "Method": "GET",
                    "test_url": "http://example.com",
                    "name": "test",
                    "status_code": "200",
                    "text": "OK",
                    "content": "content",
                    "headers": "headers",
                }
            }
        }
        xml_str = dict_to_elements_tree(data)
        assert "<Method>GET</Method>" in xml_str
        assert "<test_url>http://example.com</test_url>" in xml_str
