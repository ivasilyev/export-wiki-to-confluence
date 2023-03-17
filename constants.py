
import os

WAIT_SECONDS = 3
LOGGING_TEMPLATE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SECRET_JSON_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "secret.json")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
