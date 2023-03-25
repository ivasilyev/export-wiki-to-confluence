
import os
import re
import lxml
import logging
from time import sleep
from requests import Session
from bs4 import BeautifulSoup
from mimetypes import guess_type
from urllib import parse as urlparse
from requests_ntlm import HttpNtlmAuth
from bs4.element import Tag, NavigableString
from connection_handler import ConnectionHandler
from constants import (
    TEMPLATE_HYPERLINK,
    TEMPLATE_SPOILED_IMAGE,
    USER_AGENT,
    WAIT_SECONDS,
)
from utils import (
    create_tag,
    filename_only,
    get_tag_attribute,
    is_attachment,
    is_file_url,
    is_image,
    is_valid_size,
    process_string,
    remove_tag_children
)


class WikiHandler(ConnectionHandler):
    def __init__(self):
        super().__init__()
        self.root_url = ""
        self.table_of_contents_header = ""
        self.attachments = list()

    def connect(self):
        self.is_connected = False
        while not self.is_connected:
            try:
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
            except KeyError:  # Auth failure
                pass

    def import_url(self, s: str):
        s = s.strip()
        if len(s) > 0:
            s = urlparse.unquote(s)
            if not s.startswith("http"):
                s = urlparse.urljoin(self.root_url, s)
        return s

    def is_valid_file_url(self, s: str):
        o = (
            s.startswith(self.root_url)
            and (
                guess_type(s)[0] is not None
                or is_file_url(s)
            )
        )
        if o:
            logging.debug(f"File URL found: '{s}'")
        return o

    def get_page(self, url: str, empty_content_retries: int = 5):
        url = self.import_url(url)
        for retry in range(1, empty_content_retries + 1):
            logging.debug("Fetch the URL '{}' for attempt {} of {}".format(
                url, retry, empty_content_retries
            ))
            try:
                head = self.client.head(url, allow_redirects=True)
                code = head.status_code
                if code != 200:
                    logging.warning(f"Got response with status {code} for '{url}'")
                    if code >= 500:
                        logging.info(f"Wait {WAIT_SECONDS} seconds due to server error")
                        sleep(WAIT_SECONDS)
                        self.connect()
                    continue
                logging.debug(f"Check size for '{url}'")
                if not is_valid_size(head.headers.get("content-length", -1)):
                    logging.warning(f"Skip the URL due to excess file size: '{url}'")
                    return b""
                response = self.client.get(
                    url,
                    headers={
                        "User-Agent": USER_AGENT
                    }
                )
                content = response.content
                if len(content) > 0:
                    return content
            except Exception as e:
                logging.exception(f"Got exception: '{e}'")
                sleep(WAIT_SECONDS)
                self.connect()
        logging.critical("Exceeded empty content retries count for the URL: '{}'".format(url))
        return b""

    def get_soup(self, *args, **kwargs):
        return BeautifulSoup(
            self.get_page(*args, **kwargs),
            features="lxml"
        )

    def add_attachment(self, url: str):
        url = self.import_url(url)
        logging.debug(f"Add attachment: '{url}'")
        content = self.get_page(url)
        if len(content) > 0:
            self.attachments.append(dict(
                file_content=content,
                file_basename=os.path.basename(url),
            ))
            return True
        logging.debug(f"The attachment was not added: '{url}'")
        return False

    def extract_flash(self, s: str):
        video = re.findall("so\.addVariable\(\"file\",\"([^\"]+)\"\)", s)
        if len(video) > 0:
            video = video[0]
            logging.debug(f"Found Adobe Flash video: '{video}'")
            return create_tag("a", filename_only(video), {"href": video})
        return create_tag("p", "")

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
        if not hasattr(tag, "name") or tag.name is None or tag.name.startswith("ac:"):
            logging.debug(f"Not to be processed: '{str(tag)}'")
            return
        logging.debug(f"Process as '{str(tag.name)}': '{str(tag)}'")
        if len(get_tag_attribute(tag, "style")) > 0:
            logging.debug(f"Clear style")
            del tag["style"]
        if str(tag.name) == "div":
            try:
                # Reflect Table of Contents by Confluence macro
                if get_tag_attribute(tag, "id") == "toc":
                    logging.debug("Table of contents found")
                    tag.replace_with(
                        create_tag(
                            "p",
                            f"<b id=\"toc\">{self.table_of_contents_header}</b>"
                            "<ac:structured-macro ac:name=\"toc\" />",
                        )
                    )
                _class = get_tag_attribute(tag, "class")
                if _class in ("wikiFlvPlayer", "magnify"):
                    remove_tag_children(tag)
                    logging.debug(f"Remove tag with class '{_class}'")
                    tag.decompose()
                if _class in ("thumbinner", "thumb"):
                    logging.debug(f"Replace tag with forbidden class '{_class}'")
                    tag.replace_with_children()
                if _class == "thumbcaption":
                    remove_tag_children(tag)
                    tag.replace_with(create_tag("p", tag.text))
            except KeyError:
                pass
        if str(tag.name) == "script" and get_tag_attribute(tag, "type") == "text/javascript":
            if "wikiFlvPlayer" in get_tag_attribute(tag, "src"):
                remove_tag_children(tag)
                tag.decompose()
                return
        if "/extensions/wikiFlvPlayer/player.swf" in str(tag):
            t = self.extract_flash(tag)
            remove_tag_children(tag)
            tag.replace_with(t)
            tag = t
        if str(tag.name).startswith("h"):
            header_number = re.findall("h([0-9]+)", str(tag.name))
            if len(header_number) == 1:
                header_number = int(header_number[0])
                text = tag.find("span", {"class": "mw-headline"})
                if text is not None:
                    tag.replace_with(create_tag(f"h{header_number}", text.text))
        if str(tag.name) == "a":
            url = get_tag_attribute(tag, "href")
            if url.startswith("#"):  # Internal URL
                return
            url = self.import_url(url)
            if self.is_valid_file_url(url):
                if is_attachment(url):
                    soup = self.get_soup(url)
                    if len(soup) > 0:
                        a = soup.find("a", {"class": "internal"})
                        url_2 = self.import_url(get_tag_attribute(a, "href"))
                        if url_2 is not None:
                            url = url_2
                    else:
                        logging.debug(f"Unable to parse URL as web page: '{url}'")
                if self.add_attachment(url):
                    if is_image(url):
                        logging.debug(f"Image URL found: '{url}'")
                        basename = os.path.basename(url)
                        body = TEMPLATE_SPOILED_IMAGE.format(
                            basename=basename,
                            filename=filename_only(url),
                        )
                        tag.replace_with(create_tag("ac:structured-macro", body, {"ac:name": "expand"}))
                    else:
                        logging.debug(f"Non-image URL found: '{url}'")
                        text = tag.text
                        basename = os.path.basename(url)
                        if is_attachment(text):
                            text = " {} ".format(basename)
                        body = TEMPLATE_HYPERLINK.format(
                            basename=basename,
                            link_text=text
                        )
                        tag.replace_with(create_tag("ac:link", body))
                else:
                    tag.replace_with(create_tag("p", " [Not available] "))
                remove_tag_children(tag)
        if str(tag.name) in ("img", "script"):
            remove_tag_children(tag)
            tag.decompose()

    def process_page(self, url: str):
        url = self.import_url(url)
        soup = self.get_soup(url).find("div", {"id": "content"})

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
