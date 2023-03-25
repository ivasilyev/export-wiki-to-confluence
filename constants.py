
import os

FILE_EXTENSIONS = ("sql", "docx", "pptx")
WAIT_SECONDS = 3
LOGGING_TEMPLATE = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SECRET_JSON_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "secret.json")
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
CONFLUENCE_ATTACHMENT_SIZE_LIMIT = 30 << 20  # 30 MB

# <ac:link>...</ac:link>
# https://confluence.atlassian.com/conf710/confluence-storage-format-1031840114.html#ConfluenceStorageFormat-Links
TEMPLATE_HYPERLINK = """
<ri:attachment ri:filename="{basename}" />
<ac:plain-text-link-body>
    <![CDATA[{link_text}]]>
</ac:plain-text-link-body>
"""

# <ac:structured-macro ac:name="expand">...</ac:structured-macro>
# https://confluence.atlassian.com/conf59/expand-macro-792499106.html
# https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html
TEMPLATE_SPOILED_IMAGE = """
<ac:parameter ac:name="title">{filename}</ac:parameter>
<ac:rich-text-body>
    <ac:image 
        ac:alt="{filename}" 
        ac:height="100%"
        ac:thumbnail="false" 
        ac:title="{filename}"
        ac:width="100%"
    >
        <ri:attachment ri:filename="{basename}" />
    </ac:image>
</ac:rich-text-body>
"""

WIKI_ATTACHMENT_PAGE_PREFIXES = ("Медиа", "Файл")
