from utils.logging import log, log_func


from base64 import b64decode
from re import sub, escape, MULTILINE
from pprint import pformat

from lxml.html import HtmlElement, fromstring
from lxml.etree import _ElementTree, ElementTree
from tinycss2 import parse_stylesheet, serialize

from dtos import (
    ActionElement,
    ActionElementType,
    ElementDetail,
    WebpageData,
    ParsedWebpageData,
)


# all parsed CSS rules
all_rules = None


@log_func()
def parse(data: WebpageData) -> ParsedWebpageData:
    """Parse the elements and actions from the given webpage data.

    Args:
        data (WebpageData): Webpage data to parse

    Returns:
        ParsedWebpageData: Parsed webpage data
    """

    log.info(f"Parsing webpage data from `{data.url}`...")

    html_text = b64decode(data.htmlBase64).decode("utf-8")

    log.info(f"Parsing HTML... [{len(html_text)} bytes]")

    # parse the HTML using lxml
    html: HtmlElement = fromstring(html_text, base_url=data.url)
    tree: _ElementTree = ElementTree(html)

    log.info(f"Parsed HTML [{tree.__sizeof__()} bytes]")

    title = " ".join(html.xpath("//title/text()"))
    title = title if len(title) > 0 else None

    log.info(f"Parsed title: `{title}`")

    # parse CSS rules to AST nodes
    global all_rules
    all_rules = parse_css_to_ast(html.xpath("//style"))

    html, tree = flag_noise_elements(html, tree)
    html, tree = flag_action_elements(html, tree)
    html, tree = remove_noise_elements(html, tree)
    actions = get_action_elements(html, tree)
    html, tree = simplify_html(html, tree)

    return ParsedWebpageData(
        data.url,
        data.htmlBase64,
        data.imageBase64,
        data.language,
        title,
        html,
        tree,
        actions,
    )


FLAG_ATTRIBUTE_TYPE = "locigraph-type"
FLAG_VALUE_NOISE = "NOISE"
FLAG_ATTRIBUTE_XPATH = "locigraph-xpath"


# html element attributes that hide elements
noise_attributes = [
    "contains(@class, 'hidden')",
    "contains(@class, 'invisible')",
    "contains(@class, 'none')",
    "contains(@style, 'display: none')",
    "contains(@style, 'visibility: hidden')",
]

# CSS styles that hide elements
noise_styles: list[tuple[str, str]] = [
    # Adapted from https://www.sitepoint.com/hide-elements-in-css
    ("display", "none"),
    ("visibility", "hidden"),
    ("opacity", "0"),
    ("opacity", "0%"),
    ("transform", "scale(0)"),
    ("height", "0"),
    ("width", "0"),
]

# html tags for elements that don't contain text content
noise_tags = [
    "head",
    "title",
    "code",
    "script",
    "noscript",
    "style",
    "link",
    "meta",
    "iframe",
    "base",
    "svg",
    "path",
    "wbr",
]


@log_func()
def flag_noise_elements(
    html: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Flag elements that are not visible or contain no text content as noise.

    Args:
        html (HtmlElement): html element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    # remove comments
    for element in html.xpath("//comment()"):
        try:
            element.drop_tree()
        except Exception as element:
            log.trace(f"skipped drop_tree: {element}")

    # flag elements that are not visible with element class as noise
    # e.g. <div style="display: none">...</div>
    for attr in noise_attributes:
        elements = html.xpath(f"//*[{attr}]")

        for element in elements:
            # flag the element and all its children as noise
            for child in element.iter():
                child.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_NOISE)

        if len(elements) > 0:
            log.trace(f"flagged {len(elements)} elements with attr=`{attr}`")

    # flag elements that are not visible via CSS style as noise
    # e.g. <div class="hidden">...</div> & .hidden { display: none; }
    selectors = []

    for property, value in noise_styles:
        selectors.extend(filter_selectors(property, value))

    for selector in selectors:
        try:
            elements = html.cssselect(selector)

            for element in elements:
                # flag the element and all its children as noise
                for child in element.iter():
                    child.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_NOISE)

            if len(elements) > 0:
                log.trace(
                    f"flagged {len(elements)} elements with selector=`{selector}`"
                )

        except Exception as element:
            # pseudo-elements and pseudo-classes (e.g. ::before) are not supported
            log.trace(f"skipped selector `{selector}`, {element}")

    # remove elements that doesn't contain text content
    # e.g. <style>...</style> -> ""
    for tag in noise_tags:
        elements = html.xpath(f"//{tag}")

        for element in elements:
            # flag the element and all its children as noise
            for child in element.iter():
                child.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_NOISE)

        if len(elements) > 0:
            log.trace(f"flagged {len(elements)} <{tag}> tags")

    return html, tree


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


@log_func()
def flag_action_elements(
    html: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Flag all interactable elements as actions.

    Args:
        html (HtmlElement): html element of the HTML
        tree (_ElementTree): Element tree of the HTML

    Returns:
        list[ActionElement]: List of interactable elements
    """

    ### * Extract all interactable elements from the HTML

    links: list[HtmlElement] = []
    buttons: list[HtmlElement] = []
    inputs: list[HtmlElement] = []
    # dropdowns = [] # FUTURE: add support for <select> tags

    # * extract LINK elements
    # all <a> elements with non-empty text content
    links.extend(html.xpath("//a[string-length(text()) > 0]"))
    # all elements with `cursor: pointer` style with non-empty text content
    for selector in filter_selectors("cursor", "pointer"):
        try:
            links.extend(
                [
                    e
                    for e in html.cssselect(selector)
                    if len(e.text_content().strip()) > 0
                ]
            )
        except Exception as e:
            # pseudo-elements and pseudo-classes (e.g. ::before) are not supported
            log.trace(f"Skipped selector `{selector}`, {e}")

    log.info(f"Extracted LINK elements [{len(links)} elements]")

    # * extract INPUT elements
    # all <input> elements except hidden and button types
    inputs.extend(
        html.xpath(f"//input[not(@type='hidden' or {input_button_selector})]")
    )
    # all <textarea> elements
    inputs.extend(html.xpath("//textarea"))

    log.info(f"Extracted INPUT elements [{len(inputs)} elements]")

    # * Extract BUTTON elements
    # all <button> element with non-empty text content
    buttons.extend(html.xpath("//button[string-length(text()) > 0]"))
    # all elements with click event attributes
    buttons.extend(html.xpath(f"//*[{click_event_selector}]"))
    # all <input> elements with button type attributes
    buttons.extend(html.xpath(f"//input[{input_button_selector}]"))

    log.info(f"Extracted BUTTON elements [{len(buttons)} elements]")

    # * Extract SELECT elements
    # dropdowns.extend(html.xpath("//select")) # FUTURE: add support for <select> tags

    action_elements: dict[ActionElementType, list[HtmlElement]] = {
        "INPUT": inputs,
        "BUTTON": buttons,
        "LINK": links,
    }

    # add original xpath to elements to preserve after cleaning
    for type, elements in action_elements.items():
        for e in elements:
            if e.get(FLAG_ATTRIBUTE_TYPE, None) != FLAG_VALUE_NOISE:
                # flag the element as an action if the element haven't been flagged as noise
                # e.g. <div locigraph-type="LINK" locigraph-xpath="...">
                e.set(FLAG_ATTRIBUTE_TYPE, type)
                e.set(FLAG_ATTRIBUTE_XPATH, tree.getpath(e))

    return html, tree


@log_func()
def remove_noise_elements(
    html: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Remove elements that are flagged as noise from the HTML.

    Args:
        html (HtmlElement): html element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    # remove elements that are flagged as noise
    for element in html.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='{FLAG_VALUE_NOISE}']"):
        try:
            element.drop_tree()
        except Exception as element:
            log.trace(f"skipped drop_tree: {element}")

    return html, tree


@log_func()
def get_action_elements(html: HtmlElement, tree: _ElementTree) -> list[ActionElement]:
    """Create ActionElement objects from the extracted elements

    Args:
        links (list[HtmlElement]): List of <a> elements
        buttons (list[HtmlElement]): List of <button> elements
        inputs (list[HtmlElement]): List of <input> elements

    Returns:
        list[ActionElement]: List of ActionElement objects
    """

    inputs = html.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='INPUT']")
    buttons = html.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='BUTTON']")
    links = html.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='LINK']")

    actions: list[ActionElement] = []

    # 1st priority: INPUT actions
    for element in inputs:
        xpath = element.get(FLAG_ATTRIBUTE_XPATH, None)  # retrieve original xpath

        if xpath is None:
            log.warning(f"Skipping action element without xpath: {element}")
            continue

        name: str = element.get("name", default="")
        type: str = element.get("type", default="")
        placeholder: str = element.get("placeholder", default="")
        aria_label: str = element.get("aria-label", default="")
        value: str = element.get("value", default="")
        label: HtmlElement | None = element.label

        details: dict[ElementDetail, str] = {}

        if name != "":
            details["name"] = name
        if type != "":
            details["type"] = type
        if placeholder != "":
            details["placeholder"] = placeholder
        if aria_label != "":
            details["aria-label"] = aria_label
        if value != "":
            details["value"] = value
        if label is not None and label.text_content().strip() != "":
            details["label"] = label.text_content().strip()

        actions.append(
            ActionElement(
                xpath=xpath,
                html_element=element,
                type="INPUT",
                content=element.get("value", default=None),
                details=(details if len(details) > 0 else None),
            )
        )

    # 2nd priority: BUTTON actions
    for element in buttons:
        xpath = element.get(FLAG_ATTRIBUTE_XPATH, None)  # retrieve original xpath

        if xpath is None:
            log.warning(f"Skipping action element without xpath: {element}")
            continue

        content = get_text_content(element)

        if len(content) == 0:
            continue  # skip empty buttons

        actions.append(
            ActionElement(
                xpath=xpath,
                html_element=element,
                type="BUTTON",
                content=content,
                details=None,
            )
        )

    # 3rd priority: LINK actions
    for element in links:
        xpath = element.get(FLAG_ATTRIBUTE_XPATH, None)  # retrieve original xpath

        if xpath is None:
            log.warning(f"Skipping action element without xpath: {element}")
            continue

        content = get_text_content(element)

        if len(content) == 0:
            continue  # skip empty links

        href: str | None = element.get("href", default=None)

        details = {}

        if href is not None and href != "" and href != "#":
            details["href"] = href

        actions.append(
            ActionElement(
                xpath=xpath,
                html_element=element,
                type="LINK",
                content=content,
                details=(details if len(details) > 0 else None),
            )
        )

    log.info(f"Created {len(actions)} ActionElements")
    log.debug(f"Created ActionElements: \n```\n{pformat(actions)}\n```")

    return actions


# html tags for elements that are purely cosmetic and have no semantic meaning
cosmetic_tags = [
    "a",
    "button",
    "abbr",
    "b",
    "br",
    "bdi",
    "bdo",
    "cite",
    "code",
    "data",
    "dfn",
    "em",
    "i",
    "kbd",
    "mark",
    "meter",
    "output",
    "p",
    "progress",
    "q",
    "ruby",
    "rp",
    "rt",
    "s",
    "samp",
    "small",
    "span",
    "strong",
    "sub",
    "sup",
    "time",
    "u",
    "var",
    "del",
    "ins",
]


def simplify_html(
    html: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Simplify the HTML by removing unnecessary tags and attributes.

    Args:
        html (HtmlElement): html element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    # replace elements with no text content with a single space
    while True:
        elements = html.xpath("//*[not(normalize-space())]")

        # repeat until no more elements are removed
        if len(elements) == 0 or drop_tag(elements) is False:
            break

    # remove tags from elements that contain only one child element
    while True:
        elements = html.xpath("//*[count(*) = 1]")

        # repeat until no more elements are removed
        if len(elements) == 0 or drop_tag(elements) is False:
            break

    # remove tags that are purely cosmetic
    # e.g. <div>hello <span>world</span></div> -> <div>hello world</div>
    for tag in cosmetic_tags:
        drop_tag(html.xpath(f"//{tag}"))

    # replace table contents with markdown-style tables
    # e.g. <tr><td>1</td><td>2</td></tr> -> 1 | 2
    for table in html.xpath("//table"):

        # table content by line
        captions: list[str] = []
        contents: list[str] = []

        # read table content from <tr> tags
        for row in table.xpath(".//tr"):
            text = " | ".join(
                [get_text_content(c, delimiter="; ") for c in row.iterchildren()]
            )

            if len(text) > 0 and row.getparent() is not None:
                parent_tag = row.getparent().tag
                if parent_tag == "thead":
                    text = text + "\n" + "-" * len(text)  # add separator after header
                elif parent_tag == "tfoot":
                    text = "-" * len(text) + "\n" + text  # add separator before footer

            contents.append(text)

        # read table caption from <caption> tag
        for caption in table.xpath(".//caption"):
            text = caption.text_content().strip()

            if len(text) > 0:
                captions.append(f"[{text}]")

        # flatten the table into markdown-style text
        text = "\n\n```table\n" + "\n".join(captions + contents) + "\n```\n\n"
        table.clear()
        table.text = text

    # remove attributes from all elements
    for e in html.iter():  # type: ignore
        e.attrib.clear()

    return html, tree


def get_text_content(element: HtmlElement, delimiter: str = " | ") -> str:
    """Get the text content of an HTML element.

    Note:
        This function will add `|` (or given delimiter) between text content of
        nested elements.

    Args:
        element (HtmlElement): HTML element
        delimiter (str, optional): Delimiter between text content of nested elements.
        Defaults to " | ".

    Returns:
        str: Text content of the HTML element
    """

    # create a deep copy of the element to prevent modifying the original element
    element = element.__deepcopy__(None)

    de = escape(delimiter.strip())  # escaped delimiter

    # add delimiter between text content of nested elements
    for child in element.iter(None):
        child.tail = delimiter + child.tail if child.tail is not None else delimiter

    content = element.text_content()

    # remove repeated delimiters
    content = sub(rf"(?: ?{de})+", delimiter, content)

    # remove trailing and leading spaces, tabs or delimiters
    content = sub(rf"(?:^[ \t{de}]*)|(?:[ \t{de}]*$)", "", content, flags=MULTILINE)

    # remove extra spaces
    content = sub(r"[ \t]{2,}", " ", content)

    # replace 3+ blank lines to 2 blank lines
    content = sub(r"\n{4,}", "\n\n\n", content)

    content = content.strip()

    return content


def parse_css_to_ast(styleHtmlElements: list[HtmlElement]) -> list:
    """Parse the CSS code in the <style> elements into tinycss2 AST nodes.

    Args:
        styleHtmlElements (list[HtmlElement]): List of <style> elements

    Returns:
        list: List of tinycss2 AST nodes"""

    # extract CSS code in the <style> tag
    all_css = [e.text_content() for e in styleHtmlElements]

    # parse all rules in the CSS code into tinycss2 AST nodes
    # read more: https://doc.courtbouillon.org/tinycss2/stable/api_reference.html#ast-nodes
    all_rules = [
        rules
        for css in all_css
        for rules in parse_stylesheet(css, skip_comments=True, skip_whitespace=True)
    ]

    return all_rules


def filter_selectors(property: str, value: str) -> list[str]:
    """Get all CSS selectors that contain a CSS rule `{ property: value; }`
    from given `<style>` elements.

    Args:
        property (str): CSS property name
        value (str): CSS property value
        styleHtmlElements (list[HtmlElement]): List of <style> elements

    Returns:
        list[str]: List of CSS selectors that contain the given CSS rule"""

    global all_rules

    if all_rules is None:
        log.warning("No CSS rules found. Skipping selector extraction.")
        return []

    # selector for rules that contain `property: value;`
    selectors = []

    for rule in all_rules:
        if rule.type == "qualified-rule" or rule.type == "at-rule":

            def get_next_ident_token(tokens, i):
                while i < len(tokens):
                    if tokens[i].type == "ident":
                        return tokens[i]
                    i += 1
                return None

            for i, token in enumerate(rule.content):
                # look for the property and value in ident tokens
                # read more: https://doc.courtbouillon.org/tinycss2/stable/api_reference.html#tinycss2.ast.IdentToken
                if token.type == "ident":
                    if token.lower_value == property:

                        # check if the next token is the value
                        next_token = get_next_ident_token(rule.content, i + 1)
                        if next_token is not None:
                            if next_token.lower_value == value:
                                selectors.append(serialize(rule.prelude))

                                log.trace(
                                    f"Found `{property}: {value}` at rule `{serialize(rule.prelude)}`"
                                )
                            break

    return selectors


def drop_tag(elements: list[HtmlElement]) -> bool:
    """Drop the tag from the given elements and append a space to the tail.

    Args:
        elements (list[HtmlElement]): List of HTML elements to remove the tag from

    Returns:
        bool: True if the tag was dropped successfully, False otherwise
    """

    for element in elements:
        try:
            element.tail = " " + element.tail if element.tail is not None else " "  # type: ignore
            element.drop_tag()
        except Exception as e:
            log.trace(f"skipped drop_tag on element {element}: {e}")
            return False

    if len(elements) > 0:
        log.trace(f"drop_tag {len(elements)} elements")

    return True
