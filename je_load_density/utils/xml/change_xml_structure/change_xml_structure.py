from collections import defaultdict
from typing import Any, Dict
from xml.etree import ElementTree as _ElementTreeBuilder  # nosec B405 - construction only, no parsing  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml


def _collapse_singleton_lists(grouped: Dict[str, list]) -> Dict[str, Any]:
    return {key: value[0] if len(value) == 1 else value for key, value in grouped.items()}


def _children_to_dict(children: list) -> Dict[str, Any]:
    grouped: Dict[str, list] = defaultdict(list)
    for child_dict in map(elements_tree_to_dict, children):
        for key, value in child_dict.items():
            grouped[key].append(value)
    return _collapse_singleton_lists(grouped)


def _attach_text(elements_dict: Dict[str, Any], tag: str, text: str, has_children_or_attrs: bool) -> None:
    if not text:
        return
    if has_children_or_attrs:
        elements_dict[tag]["#text"] = text
    else:
        elements_dict[tag] = text


def elements_tree_to_dict(elements_tree: _ElementTreeBuilder.Element) -> Dict[str, Any]:
    """
    將 XML ElementTree 轉換為字典
    Convert XML ElementTree to dictionary

    :param elements_tree: XML ElementTree 元素 (XML ElementTree element)
    :return: 對應的字典結構 (Dictionary representation)
    """
    tag = elements_tree.tag
    has_attrs = bool(elements_tree.attrib)
    elements_dict: Dict[str, Any] = {tag: {} if has_attrs else None}
    children = list(elements_tree)

    if children:
        elements_dict[tag] = _children_to_dict(children)

    if has_attrs:
        elements_dict[tag].update({f"@{key}": value for key, value in elements_tree.attrib.items()})

    if elements_tree.text:
        _attach_text(elements_dict, tag, elements_tree.text.strip(), bool(children) or has_attrs)

    return elements_dict


def _set_text_node(root: _ElementTreeBuilder.Element, key: str, value: Any) -> None:
    if key != "#text" or not isinstance(value, str):
        raise TypeError(f"Invalid text node: {key} -> {value}")
    root.text = value


def _set_attribute(root: _ElementTreeBuilder.Element, key: str, value: Any) -> None:
    if not isinstance(value, str):
        raise TypeError(f"Invalid attribute value: {key} -> {value}")
    root.set(key[1:], value)


def _build_element(value: Any, root: _ElementTreeBuilder.Element) -> None:
    if isinstance(value, str):
        root.text = value
    elif isinstance(value, dict):
        _build_from_dict(value, root)
    else:
        raise TypeError(f"Invalid type in dict_to_elements_tree: {type(value)}")


def _build_from_dict(mapping: Dict[str, Any], root: _ElementTreeBuilder.Element) -> None:
    for key, value in mapping.items():
        if key.startswith("#"):
            _set_text_node(root, key, value)
        elif key.startswith("@"):
            _set_attribute(root, key, value)
        elif isinstance(value, list):
            for element in value:
                _build_element(element, _ElementTreeBuilder.SubElement(root, key))
        else:
            _build_element(value, _ElementTreeBuilder.SubElement(root, key))


def dict_to_elements_tree(json_dict: Dict[str, Any]) -> str:
    """
    將字典轉換為 XML 字串
    Convert dictionary to XML string

    :param json_dict: JSON 格式字典 (Dictionary in JSON-like format)
    :return: XML 字串 (XML string)
    """
    if not isinstance(json_dict, dict) or len(json_dict) != 1:
        raise ValueError("Input must be a dictionary with a single root element")

    tag, body = next(iter(json_dict.items()))
    node = _ElementTreeBuilder.Element(tag)
    _build_element(body, node)
    return _ElementTreeBuilder.tostring(node, encoding="utf-8").decode("utf-8")
