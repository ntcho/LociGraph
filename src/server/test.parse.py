from rank import filter

from dtos import RelationQuery, WebpageData
from utils.dev import get_timestamp, read_file_to_base64
from utils.html import get_text_content
from utils.file import read_txt

from lxml.etree import _ElementTree

from lxml.html import tostring, fromstring, HtmlElement

e = fromstring("<div>hello <p>asdfasdf</p> this this</div>")

# e = r.contentHTML
c = e.text_content()
t = get_text_content(e)


root = e.getroottree()  # type: ignore


def xpath(e: _ElementTree, element: HtmlElement):
    return e.getpath(element)


x = e.xpath("text()")
