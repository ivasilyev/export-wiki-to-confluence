
import os
import re
import lxml
import logging
from time import sleep
from requests import Session
from bs4 import BeautifulSoup
from urllib import parse as urlparse
from requests_ntlm import HttpNtlmAuth
from bs4.element import Tag, NavigableString
from connection_handler import ConnectionHandler
from utils import create_tag, is_file_url, process_string, get_tag_attribute
from constants import USER_AGENT, WAIT_SECONDS, TEMPLATE_HYPERLINK, TEMPLATE_SPOILED_IMAGE


class WikiHandler(ConnectionHandler):
    def __init__(self):
        super().__init__()
        self.root_url = ""
        self.table_of_contents_header = ""
        self.attachments = list()

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
        s = s.strip()
        if len(s) > 0:
            s = urlparse.unquote(s)
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

    def add_attachment(self, url: str):
        url = self.import_url(url)
        logging.debug(f"Add attachment: '{url}'")
        self.attachments.append(dict(
            file_content=self.get_page(url),
            file_basename=os.path.basename(url),
        ))

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
        logging.debug(f"Process as '{str(tag.name)}': '{str(tag)}'")
        if str(tag.name) == "div":
            try:
                if tag["id"] == "toc":
                    logging.debug("Table of contents found")
                    tag.replace_with(
                        create_tag(
                            "p",
                            f"<b id=\"toc\">{self.table_of_contents_header}</b>"
                            "<ac:structured-macro ac:name=\"toc\"/>",
                            {"mock-id": "toc"}
                        )
                    )
            except KeyError:
                pass
            return
        if str(tag.name).startswith("h"):
            header_number = re.findall("h([0-9]+)", str(tag.name))
            if len(header_number) == 1:
                header_number = int(header_number[0])
                text = tag.find("span", {"class": "mw-headline"})
                if text is not None:
                    tag.replace_with(create_tag(f"h{header_number}", text.text))
        if str(tag.name) == "a":
            url = self.import_url(get_tag_attribute(tag, "href"))
            if is_file_url(url):
                if get_tag_attribute(tag, "class") == "image" or "Файл:" in url:
                    logging.debug(f"Image URL found: '{url}'")
                    tag.replaceWithChildren()
                else:
                    logging.debug(f"Non-image URL found: '{url}'")
                    self.add_attachment(url)
                    body = TEMPLATE_HYPERLINK.format(
                        basename=os.path.basename(url),
                        link_text=tag.text
                    )
                    tag.replace_with(create_tag("ac:link", body))
        if str(tag.name) == "img":
            url = self.import_url(get_tag_attribute(tag, "src"))
            logging.debug(f"Image source URL found: '{url}'")
            if is_file_url(url):
                self.add_attachment(url)
                basename = os.path.basename(url)
                body = TEMPLATE_SPOILED_IMAGE.format(
                    basename=basename,
                    filename=os.path.splitext(basename)[0]
                )
                tag.replace_with(create_tag("ac:structured-macro", body, {"ac:name": "expand"}))

    def process_page(self, url: str):
        url = self.import_url(url)
        soup = BeautifulSoup(
            self.get_page(url),
            features="lxml"
        ).find("div", {"id": "content"})

        first_heading = soup.find("h1", {"id": "firstHeading"}).text
        contents = soup.find("div", {"class": "mw-parser-output"}).contents
        self.attachments = list()
        for parent in contents:
            self.process_tag(parent)

        content_body = "".join(str(i) for i in contents)
        logging.debug("Processed content body to be uploaded is below")
        logging.debug(content_body)
        return dict(
            page_title=first_heading,
            page_body=content_body,
            page_attachments=list(self.attachments),
        )
