
import logging
from wiki_handler import WikiHandler
from constants import LOGGING_TEMPLATE
from pdf_file_handler import PdfFileHandler
from confluence_handler import ConfluenceHandler


def run():
    logging.basicConfig(
        level=logging.INFO,
        format=LOGGING_TEMPLATE
    )

    p_handler = PdfFileHandler()
    p_handler.read()
    w_handler = WikiHandler()
    w_handler.connect()
    c_handler = ConfluenceHandler()
    c_handler.connect()

    urls = p_handler.extract_urls()
    for idx, url in enumerate(urls):
        logging.info(f"Process URL {idx + 1} of {len(urls)}")

        html_dict = w_handler.process_page(url)
        c_handler.push_html(**html_dict)


if __name__ == '__main__':
    run()

# python main.py