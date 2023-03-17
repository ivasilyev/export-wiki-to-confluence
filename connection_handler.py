
import logging
from utils import load_dict
from constants import SECRET_JSON_PATH


class ConnectionHandler:
    def __init__(self):
        self._secret_dict = dict()
        self.update_secret()
        self.client = None
        self.is_connected = False

    def update_secret(self, file: str = SECRET_JSON_PATH):
        try:
            self._secret_dict.update(load_dict(file))
        except Exception:
            logging.critical(f"The secret file is invalid : '{file}'")
            raise

    def connect(self):
        # self.client.connect() etc
        self.is_connected = True

