
import logging
import atlassian
from connection_handler import ConnectionHandler


class ConfluenceHandler(ConnectionHandler):
    def __init__(self):
        super().__init__()
        self.space_key = ""
        self.parent_page_id = ""

    def connect(self):
        self.client = atlassian.Confluence(
            url=self._secret_dict["confluence_root_url"],
            username=self._secret_dict["confluence_username"],
            password=self._secret_dict["confluence_password"]
        )
        self.space_key = [
            i for i in self.client.get_all_spaces()["results"]
            if i["name"] == self._secret_dict["confluence_space_name"]
        ][0]["key"]
        self.parent_page_id = self.client.get_page_id(
            self.space_key,
            self._secret_dict["confluence_parent_page_name"]
        )
        logging.debug("Confluence client connected")
        super().connect()

    def push_html(self, page_title: str, page_body: str):
        if not self.is_connected:
            logging.warning("Confluence client is not connected")
            return
        if self.client.page_exists(self.space_key, page_title, type=None):
            logging.debug("Update the page with the name '{}' into the space with the key '{}'".format(
                page_title, self.space_key
            ))
            o = self.client.update_page(
                page_id=self.client.get_page_id(self.space_key, page_title),
                title=page_title,
                body=page_body,
                parent_id=self.parent_page_id,
                type="page",
                representation="storage",
                minor_edit=False,
                full_width=False
            )
        else:
            logging.debug("Create the page with the name '{}' into the space with the key '{}'".format(
                page_title, self.space_key
            ))
            o = self.client.create_page(
                space=self.space_key,
                title=page_title,
                body=page_body,
                parent_id=self.parent_page_id,
                type="page",
                representation="storage",
                editor="v2",
                full_width=False
            )

    def push_blob(self, file_content: bytes, file_basename: str, page_title: str):
        logging.debug(f"Upload attachment '{file_basename}' into created page '{page_title}'")
        o = self.client.attach_content(
            content=bytes(file_content),
            name=file_basename,
            page_id=self.client.get_page_id(self.space_key, page_title),
            title=page_title,
            space=self.space_key
        )

    def push_page(self, page_title: str, page_body: str, page_attachments: list):
        logging.debug(f"Upload page {page_title} with {len(page_attachments)} attachments")
        self.push_html(page_title, page_body)
        for attachment_dict in page_attachments:
            self.push_blob(page_title=page_title, **attachment_dict)

