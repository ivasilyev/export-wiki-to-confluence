# export-wiki-to-confluence
Repo containing tools to scrap Wiki pages and upload them to Confluence

# Action sequence

0. Create & fill `secret.json`;
1. Read given PDF file and parse URLs from it;
2. Login into Wiki using NTLM authentication protocol;
3. Fetch a URL and parse the required part of the corresponding web page;
3. Modify this page in-place;
4. Login into Confluence;
5. Upload the modified page to Confluence.
