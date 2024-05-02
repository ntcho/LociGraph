from extract import extract_llm
from parse import parse
from rank import filter

from dtos import RelationQuery, WebpageData
from utils.dev import get_timestamp, read_file_to_base64

from lxml.html import tostring

from utils.prompt import generate_extract_prompt

data = parse(
    WebpageData(
        url="https://mail.google.com/mail/eCvnvz83ITgehi2O-dQKC",
        htmlBase64=read_file_to_base64("data/1-gmail.html"),
        imageBase64="",
        language="en",
    )
)

s = tostring(data.contentHTML, pretty_print=True).decode("utf-8")  # type: ignore

filename = f"output_{get_timestamp()}.html"

with open(filename, "w") as file:
    file.write(s)

query = RelationQuery("Contineum Therapeutics", "IPO size")

e = filter(data, query)

r = extract_llm(e, query, data.title)

p = generate_extract_prompt(data.title, e, query)
