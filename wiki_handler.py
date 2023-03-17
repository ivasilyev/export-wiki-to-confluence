
import re
import lxml
import logging
from time import sleep
from requests import Session
from bs4 import BeautifulSoup
from urllib import parse as urlparse
from requests_ntlm import HttpNtlmAuth
from bs4.element import Tag, NavigableString
from utils import create_tag, process_string
from constants import USER_AGENT, WAIT_SECONDS
from connection_handler import ConnectionHandler


class WikiHandler(ConnectionHandler):
    def __init__(self):
        super().__init__()
        self.root_url = ""
        self.table_of_contents_header = ""

    def connect(self):
        del self.client
        self.client = Session()
        self.client.auth = HttpNtlmAuth(
            self._secret_dict["wiki_ntlm_username"],
            self._secret_dict["wiki_ntlm_password"],
        )
        self.root_url = self._secret_dict["wiki_root_url"]
        self.table_of_contents_header = self._secret_dict["confluence_table_of_contents_header"]
        logging.debug("Wiki client connected")
        super().connect()

    def import_url(self, s: str):
        s = urlparse.unquote(s.strip())
        if not s.startswith("http"):
            s = urlparse.urljoin(self.root_url, s)
        return s

    def get_page(self, url: str, empty_content_retries: int = 5):
        url = self.import_url(url)
        for retry in range(1, empty_content_retries + 1):
            logging.debug("Fetch the URL '{}' for attempt {} of {}".format(
                url, retry, empty_content_retries
            ))
            response = self.client.get(
                url,
                headers={
                    "User-Agent": USER_AGENT
                }
            )
            if response.status_code != 200:
                logging.warning(f"Got response with status {response.status_code} for '{url}'")
                sleep(WAIT_SECONDS)
                self.connect()
                continue
            content = response.content
            if len(content) > 0:
                return content
        logging.critical("Exceeded empty content retries count for the URL: '{}'".format(url))
        raise ValueError()

    def process_tag(self, tag: Tag) -> None:
        if isinstance(tag, NavigableString):
            text = process_string(tag.text)
            if len(text) == 0:
                # Stub
                tag.replace_with("")
        if hasattr(tag, "children"):
            children = list(tag.children)
            if len(children) > 0:
                for child in children:
                    self.process_tag(child)
        if not hasattr(tag, "name") or tag.name is None:
            return
        t = str(tag.name)
        if t == "div":
            # Table of contents
            try:
                if tag["id"] == "toc":
                    tag.replace_with(
                        create_tag(
                            "p",
                            f"<b id=\"toc\">{self.table_of_contents_header}</b>\n<ac:structured-macro ac:name=\"toc\"/>",
                            {"mock-id": "toc"}
                        )
                    )
            except KeyError:
                pass
            return
        if t.startswith("h"):
            text = tag.text
            header_number = re.findall("h([0-9]+)", t)
            if len(header_number) == 1:
                header_number = int(header_number[0])
                bold_tag = tag.find("b")
                if bold_tag is not None:
                    text = bold_tag.text
                text = text.replace("[править | edit source]", "")
                tag.replace_with(create_tag(f"h{header_number}", text))
        if t == "a":
            url = urlparse.unquote(tag["href"])
            if len(re.findall(".+(\.[a-z]{3})$", url)) > 0:
                tag["href"] = self.import_url(url)
        if t == "img":
            tag["src"] = self.import_url(tag["src"])

    def process_page(self, url: str):
        soup = BeautifulSoup(
            self.get_page(url),
            features="lxml"
        ).find("div", {"id": "content"})

        first_heading = soup.find("h1", {"id": "firstHeading"}).text
        contents = soup.find("div", {"class": "mw-parser-output"}).contents
        for parent in contents:
            self.process_tag(parent)

        content_body = "".join(str(i) for i in contents)
        return dict(
            title=first_heading,
            body=content_body
        )
