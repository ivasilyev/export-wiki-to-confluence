
import os
import re
import logging
from bs4 import BeautifulSoup
from urllib import parse as urlparse


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


def create_tag(tag: str, value: str, attrs: dict = None):
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
