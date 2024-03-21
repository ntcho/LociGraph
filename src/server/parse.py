from trafilatura import extract
from base64 import b64decode

from dtos import WebpageData, ParsedWebpageData


def parse(data: WebpageData) -> ParsedWebpageData:
    raw_html = b64decode(data.htmlBase64).decode("utf-8")

    content = extract(raw_html)
    content_markdown = extract(raw_html, include_links=True, url=data.url)
    content_xml = extract(
        raw_html, output_format="xml", include_links=True, url=data.url
    )

    with open("output.md", "w") as file:
        file.write(content_markdown)

    # TODO: extract actions

    return ParsedWebpageData(
        url=data.url,
        title=data.title,
        htmlBase64=data.htmlBase64,
        imageBase64=data.imageBase64,
        language=data.language,
        content=content,
        contentMarkdown=content_markdown,
        contentXML=content_xml,
        actions=[],
    )


def read_file_to_base64(file_path: str) -> str:
    from base64 import b64encode

    with open(file_path, "rb") as file:
        file_content = file.read()
        base64_string = b64encode(file_content).decode("utf-8")

        return base64_string


parse(
    WebpageData(
        url="https://example.com",
        title="Test",
        htmlBase64=read_file_to_base64("test2.html"),
        imageBase64="",
        language="en",
    )
)
