from collections import defaultdict
from xml.etree import ElementTree
from typing import Union, Dict, Any


def elements_tree_to_dict(elements_tree: ElementTree.Element) -> Dict[str, Any]:
    """
    將 XML ElementTree 轉換為字典
    Convert XML ElementTree to dictionary

    :param elements_tree: XML ElementTree 元素 (XML ElementTree element)
    :return: 對應的字典結構 (Dictionary representation)
    """
    elements_dict: Dict[str, Any] = {elements_tree.tag: {} if elements_tree.attrib else None}
    children = list(elements_tree)

    # 遞迴處理子節點 (Recursively process children)
    if children:
        default_dict = defaultdict(list)
        for dc in map(elements_tree_to_dict, children):
            for key, value in dc.items():
                default_dict[key].append(value)
        elements_dict[elements_tree.tag] = {
            key: value[0] if len(value) == 1 else value
            for key, value in default_dict.items()
        }

    # 加入屬性 (Add attributes)
    if elements_tree.attrib:
        elements_dict[elements_tree.tag].update(
            {f"@{key}": value for key, value in elements_tree.attrib.items()}
        )

    # 加入文字內容 (Add text content)
    if elements_tree.text:
        text = elements_tree.text.strip()
        if children or elements_tree.attrib:
            if text:
                elements_dict[elements_tree.tag]["#text"] = text
        else:
            elements_dict[elements_tree.tag] = text

    return elements_dict


def dict_to_elements_tree(json_dict: Dict[str, Any]) -> str:
    """
    將字典轉換為 XML 字串
    Convert dictionary to XML string

    :param json_dict: JSON 格式字典 (Dictionary in JSON-like format)
    :return: XML 字串 (XML string)
    """

    def _to_elements_tree(json_dict: Any, root: ElementTree.Element) -> None:
        if isinstance(json_dict, str):
            root.text = json_dict
        elif isinstance(json_dict, dict):
            for key, value in json_dict.items():
                if key.startswith("#"):  # 處理文字節點
                    if key != "#text" or not isinstance(value, str):
                        raise TypeError(f"Invalid text node: {key} -> {value}")
                    root.text = value
                elif key.startswith("@"):  # 處理屬性
                    if not isinstance(value, str):
                        raise TypeError(f"Invalid attribute value: {key} -> {value}")
                    root.set(key[1:], value)
                elif isinstance(value, list):  # 處理子節點清單
                    for element in value:
                        _to_elements_tree(element, ElementTree.SubElement(root, key))
                else:  # 處理單一子節點
                    _to_elements_tree(value, ElementTree.SubElement(root, key))
        else:
            raise TypeError(f"Invalid type in dict_to_elements_tree: {type(json_dict)}")

    if not isinstance(json_dict, dict) or len(json_dict) != 1:
        raise ValueError("Input must be a dictionary with a single root element")

    tag, body = next(iter(json_dict.items()))
    node = ElementTree.Element(tag)
    _to_elements_tree(body, node)
    return ElementTree.tostring(node, encoding="utf-8").decode("utf-8")