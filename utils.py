
import re
import logging
from bs4.element import Tag
from bs4 import BeautifulSoup


def process_string(s: str):
    return re.sub("[\r\n]+", "\n", s.strip())


def load_string(file: str):
    logging.debug(f"Reading '{file}'")
    with open(file=file, mode="r", encoding="utf-8") as f:
        s = f.read()
        f.close()
    return s


def load_dict(file: str):
    from json import loads
    return loads(load_string(file))


def create_tag(tag: str, value: str = "", attrs: dict = None) -> Tag:
    tag = str(tag)
    value = str(value)
    open_tag = f"<{tag}>"
    if attrs is not None and isinstance(attrs, dict):
        open_tag = "<{} {}>".format(
            tag,
            " ".join(f"{k}=\"{v}\"" for k, v in attrs.items())
        )
    return BeautifulSoup(
        open_tag + value + f"</{tag}>", "lxml"
    ).find(f"{tag}")


def get_tag_attribute(tag: Tag, attribute: str) -> str:
    logging.debug(f"Get attribute '{attribute}' from tag {str(tag)}'")
    value = tag.get(attribute)
    logging.debug(f"The attribute is '{value}'")
    if value is None:
        return ""
    if isinstance(value, list):
        return value[0]
    return value


def is_file_url(s: str) -> bool:
    s = s.strip()
    b = len(re.findall(".+(\.[a-z]{3})$", s)) > 0
    if b:
        logging.debug("File URL: '{}'".format(s))
    else:
        logging.debug("Not a file URL: '{}'".format(s))
    return b

