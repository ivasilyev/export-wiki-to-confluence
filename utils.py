
import os
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
        open_tag + value + f"</{tag}>", "html.parser"  # Keeps elements like '<![CDATA[...]]>'
    ).find(f"{tag}")


def remove_tag_children(tag: Tag):
    if hasattr(tag, "children"):
        children = list(tag.children)
        if len(children) > 0:
            for child in children:
                try:
                    child.decompose()
                except AttributeError:
                    child.replace_with("")


def get_tag_attribute(tag: Tag, attribute: str) -> str:
    logging.debug(f"Get attribute '{attribute}' from tag {str(tag)}'")
    value = tag.get(attribute)
    if value is None:
        value = ""
    if isinstance(value, list):
        value = value[0]
    if len(value) > 0:
        logging.debug(f"The attribute value is '{value}'")
    return value


def is_file_url(s: str) -> bool:
    from constants import FILE_EXTENSIONS
    s = s.strip().lower()
    return any(s.endswith(f".{i}") for i in FILE_EXTENSIONS)


def is_valid_size(x):
    from constants import CONFLUENCE_ATTACHMENT_SIZE_LIMIT
    z = int(x)
    o = z < CONFLUENCE_ATTACHMENT_SIZE_LIMIT
    if o:
        logging.debug(f"The object size does not exceed Confluence limits: {z}")
    else:
        logging.warning(f"The object size exceeds Confluence limits: {z}")
    return o


def filename_only(s: str):
    return os.path.splitext(os.path.basename(s))[0]


def is_attachment(s: str):
    from constants import WIKI_ATTACHMENT_PAGE_PREFIXES
    bn = s.split("/")[-1]
    o = any(bn.startswith(f"{i}:") for i in WIKI_ATTACHMENT_PAGE_PREFIXES)
    if o:
        logging.debug(f"Attachment found: '{s}'")
    return o


def is_image(s: str):
    from mimetypes import guess_type
    if isinstance(s, str):
        g = guess_type(s)[0]
        if isinstance(g, str):
            return g.split("/")[0] == "image"
    return False
