
import os
import logging
from pypdf import PdfReader
from urllib.parse import unquote
from utils import load_dict
from constants import SECRET_JSON_PATH


class PdfFileHandler:
    def __init__(self):
        self.file = ""
        self._secret_dict = dict()
        self.update_secret()
        self._is_valid = False

    @property
    def is_valid(self):
        is_valid = os.path.exists(self.file)
        if not is_valid:
            logging.warning(f"Invalid PDF file: '{self.file}'")
        return is_valid

    def update_secret(self, file: str = SECRET_JSON_PATH):
        try:
            self._secret_dict.update(load_dict(file))
        except Exception:
            logging.critical(f"The secret file is invalid : '{file}'")
            raise

    def read(self):
        self.file = self._secret_dict["pdf_file_full_path"]

    def extract_urls(self):
        if not self.is_valid:
            return
        reader = PdfReader(self.file)

        out = set()

        def get_url(x):
            if x is None:
                return
            if "/URI" in x.keys():
                s = unquote(x["/URI"])
                if "/Категория:" not in s:
                    out.add(s)
            if "/A" in x.keys():
                get_url(x["/A"])
            if "/Annots" in x.keys():
                for i in x["/Annots"]:
                    get_url(i.get_object())

        for page in reader.pages:
            get_url(page.get_object())

        logging.info(f"{len(out)} URLs were extracted")
        return out

