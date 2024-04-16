from parse import parse
from filter import filter

from dtos import RelationQuery, WebpageData
from utils.dev import get_timestamp, read_file_to_base64

from lxml.html import tostring

r = parse(
    WebpageData(
        url="https://example.com",
        htmlBase64=read_file_to_base64("data/linkedin.html"),
        imageBase64="",
        language="en",
    )
)

s = tostring(r.contentHTML, pretty_print=True).decode("utf-8")  # type: ignore

filename = f"output_{get_timestamp()}.html"

with open(filename, "w") as file:
    file.write(s)

e = filter(r, RelationQuery("Anna", "studied at"))

# TODO: add tests
