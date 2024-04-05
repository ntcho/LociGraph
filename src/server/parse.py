import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from base64 import b64decode
from re import sub
from pprint import pformat

from trafilatura import extract
from lxml.html import HtmlElement, fromstring
from lxml.etree import _ElementTree, ElementTree
from cssselect import ExpressionError
from tinycss2 import parse_stylesheet, serialize

from dtos import ActionElement, WebpageData, ParsedWebpageData


def parse(data: WebpageData) -> ParsedWebpageData:
    html = b64decode(data.htmlBase64).decode("utf-8")

    # extract plain text and markdown content
    content, content_markdown = extract_text(html, data.url)

    # extract HTML elements with actions
    root, tree, title, actions = extract_html(html, data.url)

    return ParsedWebpageData(
        data.url,
        data.htmlBase64,
        data.imageBase64,
        data.language,
        title,
        content,
        content_markdown,
        root,
        tree,
        actions,
    )


def extract_text(html: str, url: str) -> tuple[str | None, str | None]:
    """Extract plain text and markdown from HTML using trafilatura.

    Args:
        html (str): HTML of the webpage
        url (str): URL of the webpage

    Returns:
        tuple[str]: Plain text and markdown of the webpage content"""

    content = extract(html)

    if content:
        log.info(f"Extracted content in plain text [{len(content)} chars]")
        log.debug(f"Extracted content: \n```\n{content[:500]}\n```")
    else:
        log.warn(f"Extracted no content")
        return None, None

    content_markdown = extract(html, include_links=True, url=url)

    if content_markdown:
        log.info(f"Extracted content in markdown [{len(content_markdown)} chars]")
        log.debug(f"Extracted content: \n```\n{content_markdown[:500]}\n```")

    return content, content_markdown


# xpath selector for elements with click events
click_event_selector = " or ".join(
    [
        # selector for <[any_tag] onclick|ondblclick|onmousedown|onmouseup="...">
        # will be `@onclick or @ondblclick or ...`
        f"@{s}"
        for s in [
            "onclick",  # https://mdn.io/button_onclick
            "ondblclick",  # https://mdn.io/button_ondblclick
            "onmousedown",  # https://mdn.io/button_onmousedown
            "onmouseup",  # https://mdn.io/button_onmouseup
        ]
    ]
)

# xpath selector for input elements that display as buttons
input_button_selector = " or ".join(
    [
        # selector for <input type="button|reset|submit">
        # will be `@type='button' or @type='reset' or @type='submit'`
        f"@type='{s}'"
        for s in [
            "button",  # https://mdn.io/input_button
            "reset",  # https://mdn.io/input_reset
            "submit",  # https://mdn.io/input_submit
        ]
    ]
)


def extract_html(
    html: str, url: str
) -> tuple[HtmlElement, _ElementTree, str | None, list[ActionElement]]:
    """Extract actions from the HTML using lxml.

    Args:
        html (str): HTML of the webpage

    Returns:
        tuple[HtmlElement, _ElementTree, str | None, list[ActionElement]]:
        Root element of the HTML, element tree, HTML title and actions
    """

    log.info(f"Parsing HTML... [{len(html)} bytes]")

    # parse the HTML using lxml
    root: HtmlElement = fromstring(html, base_url=url)
    tree: _ElementTree = ElementTree(root)

    log.info(f"Parsed HTML [{tree.__sizeof__()} bytes]")

    title = root.xpath("//title/text()")
    title = title[0] if len(title) > 0 else None

    log.info(f"Parsed title: `{title}`")

    """
    Extract elements with actions from the HTML
    """

    links: list[HtmlElement] = []
    buttons: list[HtmlElement] = []
    inputs: list[HtmlElement] = []
    # dropdowns = [] # TODO: add support for <select> tags

    # all <style> elements containing CSS
    styles = root.xpath("//style")

    # * extract LINK elements
    # all <a> elements with non-empty text content
    links.extend(root.xpath("//a[string-length(text()) > 0]"))
    # all elements with `cursor: pointer` style with non-empty text content
    for selector in get_selectors_from_rule("cursor", "pointer", styles):
        try:
            links.extend(
                [e for e in root.cssselect(selector) if len(e.text_content()) > 0]
            )
        except ExpressionError as e:
            # pseudo-elements and pseudo-classes (e.g. ::before) are not supported
            log.info(f"Skipped selector `{selector}`, {e}")

    log.info(f"Extracted LINK elements [{len(links)} elements]")

    # * extract INPUT elements
    # all <input> elements except hidden and button types
    inputs.extend(
        root.xpath(f"//input[not(@type='hidden' or {input_button_selector})]")
    )
    # all <textarea> elements
    inputs.extend(
        root.xpath("//textarea")
    )  # TODO: use `.get("placeholder")` for context

    log.info(f"Extracted INPUT elements [{len(inputs)} elements]")

    # * Extract BUTTON elements
    # all <button> element with non-empty text content
    buttons.extend(root.xpath("//button[string-length(text()) > 0]"))
    # all elements with click event attributes
    buttons.extend(root.xpath(f"//*[{click_event_selector}]"))
    # all <input> elements with button type attributes
    buttons.extend(root.xpath(f"//input[{input_button_selector}]"))

    log.info(f"Extracted BUTTON elements [{len(buttons)} elements]")

    # * Extract SELECT elements
    # dropdowns.extend(root.xpath("//select")) # TODO: add support for <select> tags

    """
    Create ActionTarget objects from the extracted elements
    """

    actions: list[ActionElement] = []

    for element in links:
        content = element.text_content().replace("\n", " ").strip()
        content = sub(r"\s+", " ", content)  # remove extra spaces

        if len(content) == 0:
            continue  # skip empty links

        href: str | None = element.get("href", default=None)

        details = {}

        if href is not None:
            details["href"] = href

        actions.append(
            ActionElement(
                xpath=tree.getpath(element),
                html_element=element,
                type="LINK",
                content=content,
                details=(details if len(details) > 0 else None),
            )
        )

    for element in buttons:
        content = element.text_content().replace("\n", " ").strip()
        content = sub(r"\s+", " ", content)  # remove extra spaces

        if len(content) == 0:
            continue  # skip empty buttons

        actions.append(
            ActionElement(
                xpath=tree.getpath(element),
                html_element=element,
                type="BUTTON",
                content=content,
                details=None,
            )
        )

    for element in inputs:
        placeholder: str | None = element.get("placeholder", default=None)
        aria_label: str | None = element.get("aria-label", default=None)
        label: HtmlElement | None = element.label

        details = {}

        if placeholder is not None:
            details["placeholder"] = placeholder
        if aria_label is not None:
            details["aria-label"] = aria_label
        if label is not None:
            details["label"] = label.text_content()

        actions.append(
            ActionElement(
                xpath=tree.getpath(element),
                html_element=element,
                type="INPUT",
                content=element.get("value", default=None),
                details=(details if len(details) > 0 else None),
            )
        )

    log.info(f"Created ActionTargets [{len(actions)} actions]")
    log.debug(
        f"Created ActionTargets: \n```\n{pformat(actions[:3])}\n{pformat(actions[-3:])}\n```"
    )

    return root, tree, title, actions


def get_selectors_from_rule(
    property: str, value: str, styleHtmlElements: list[HtmlElement]
) -> list[str]:
    """Get all CSS selectors that contain a CSS rule `{ property: value; }`
    from given `<style>` elements.

    Args:
        property (str): CSS property name
        value (str): CSS property value
        styleHtmlElements (list[HtmlElement]): List of <style> elements

    Returns:
        list[str]: List of CSS selectors that contain the given CSS rule"""

    # extract CSS code in the <style> tag
    all_css = [e.text_content() for e in styleHtmlElements]

    # parse all rules in the CSS code into tinycss2 AST nodes
    # read more: https://doc.courtbouillon.org/tinycss2/stable/api_reference.html#ast-nodes
    all_rules = [
        rules
        for css in all_css
        for rules in parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
    ]

    # selector for rules that contain `property: value;`
    selectors = []

    for rule in all_rules:
        if rule.type == "qualified-rule" or rule.type == "at-rule":
            property_exists = False
            value_exists = False

            for token in rule.content:
                # look for the property and value in ident tokens
                # read more: https://doc.courtbouillon.org/tinycss2/stable/api_reference.html#tinycss2.ast.IdentToken
                if token.type == "ident":
                    if token.value == property:
                        property_exists = True
                        if value_exists:
                            break
                    elif token.value == value:
                        value_exists = True
                        if property_exists:
                            break

            if property_exists and value_exists:
                selectors.append(serialize(rule.prelude))

    return selectors
