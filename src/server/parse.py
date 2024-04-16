from utils.logging import log, log_func


from base64 import b64decode
from re import sub
from pprint import pformat

from trafilatura import extract
from lxml.html import HtmlElement, fromstring
from lxml.etree import _ElementTree, ElementTree
from tinycss2 import parse_stylesheet, serialize

from dtos import ActionElement, ActionElementType, WebpageData, ParsedWebpageData


@log_func()
def parse(data: WebpageData) -> ParsedWebpageData:
    """Parse the webpage data into a structured format.

    Args:
        data (WebpageData): Webpage data to parse
    """

    log.info(f"Parsing webpage data from `{data.url}`...")

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
        tuple[str]: Plain text and markdown of the webpage content
    """

    content = extract(html)

    if content:
        log.info(f"Extracted content in plain text [{len(content)} chars]")
        log.debug(f"Extracted content: \n```\n{content[:100]}...\n```")
    else:
        log.warning(f"Extracted no content from html [{len(html)} bytes]")
        return None, None

    content_markdown = extract(html, include_links=True, url=url)

    if content_markdown:
        log.info(f"Extracted content in markdown [{len(content_markdown)} chars]")
        log.debug(f"Extracted content: \n```\n{content_markdown[:100]}...\n```")

    log.success(f"Extracted {len(content)} chars of plain text from `{url}`")

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
    "br",
    "wbr",
]

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

# html tags for elements that are purely cosmetic and have no semantic meaning
cosmetic_tags = [
    "a",
    "button",
    "abbr",
    "b",
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

# all parsed CSS rules
all_rules = None


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

    # parse CSS rules to AST nodes
    global all_rules
    all_rules = parse_css_to_ast(root.xpath("//style"))

    root, tree = flag_noise_elements(root, tree)

    root, tree = flag_action_elements(root, tree)

    root, tree = remove_noise_elements(root, tree)

    actions = get_action_elements(root, tree)

    root, tree = simplify_html(root, tree)

    return root, tree, title, actions


FLAG_ATTRIBUTE_TYPE = "locigraph-type"
FLAG_VALUE_NOISE = "NOISE"
FLAG_ATTRIBUTE_XPATH = "locigraph-xpath"


@log_func()
def flag_noise_elements(
    root: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Remove non-semantic elements from the HTML.

    Args:
        root (HtmlElement): Root element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    # remove comments
    for element in root.xpath("//comment()"):
        try:
            element.drop_tree()
        except Exception as element:
            log.trace(f"skipped drop_tree: {element}")

    # flag elements that are not visible with element class as noise
    # e.g. <div style="display: none">...</div>
    for attr in noise_attributes:
        elements = root.xpath(f"//*[{attr}]")

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
        selectors.extend(get_selectors_from_rule(property, value))

    for selector in selectors:
        try:
            elements = root.cssselect(selector)

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
        elements = root.xpath(f"//{tag}")

        for element in elements:
            # flag the element and all its children as noise
            for child in element.iter():
                child.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_NOISE)

        if len(elements) > 0:
            log.trace(f"flagged {len(elements)} <{tag}> tags")

    return root, tree


@log_func()
def flag_action_elements(
    root: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Find all interactable elements in the HTML and flag them as actions.

    Args:
        root (HtmlElement): Root element of the HTML
        tree (_ElementTree): Element tree of the HTML
        styles (list[HtmlElement]): List of <style> elements containing CSS

    Returns:
        list[ActionElement]: List of interactable elements
    """

    ### * Extract all interactable elements from the HTML

    links: list[HtmlElement] = []
    buttons: list[HtmlElement] = []
    inputs: list[HtmlElement] = []
    # dropdowns = [] # TODO: add support for <select> tags

    # * extract LINK elements
    # all <a> elements with non-empty text content
    links.extend(root.xpath("//a[string-length(text()) > 0]"))
    # all elements with `cursor: pointer` style with non-empty text content
    for selector in get_selectors_from_rule("cursor", "pointer"):
        try:
            links.extend(
                [e for e in root.cssselect(selector) if len(e.text_content()) > 0]
            )
        except Exception as e:
            # pseudo-elements and pseudo-classes (e.g. ::before) are not supported
            log.trace(f"Skipped selector `{selector}`, {e}")

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

    return root, tree


@log_func()
def remove_noise_elements(
    root: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Remove elements that are flagged as noise from the HTML.

    Args:
        root (HtmlElement): Root element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    # remove elements that are flagged as noise
    for element in root.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='{FLAG_VALUE_NOISE}']"):
        try:
            element.drop_tree()
        except Exception as element:
            log.trace(f"skipped drop_tree: {element}")

    return root, tree


@log_func()
def get_action_elements(root: HtmlElement, tree: _ElementTree) -> list[ActionElement]:
    """Create ActionElement objects from the extracted elements

    Args:
        links (list[HtmlElement]): List of <a> elements
        buttons (list[HtmlElement]): List of <button> elements
        inputs (list[HtmlElement]): List of <input> elements

    Returns:
        list[ActionElement]: List of ActionElement objects
    """

    inputs = root.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='INPUT']")
    buttons = root.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='BUTTON']")
    links = root.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='LINK']")

    actions: list[ActionElement] = []

    # 1st priority: INPUT actions
    for element in inputs:
        xpath = element.get(FLAG_ATTRIBUTE_XPATH, None)  # retrieve original xpath

        if xpath is None:
            log.warning(f"Skipping action element without xpath: {element}")
            continue

        placeholder: str | None = element.get("placeholder", default=None)
        aria_label: str | None = element.get("aria-label", default=None)
        value: str | None = element.get("value", default=None)
        label: HtmlElement | None = element.label

        details = {}

        if placeholder is not None and placeholder != "":
            details["placeholder"] = placeholder
        if aria_label is not None and aria_label != "":
            details["aria-label"] = aria_label
        if value is not None and value != "":
            details["value"] = value
        if label is not None and label.text_content() != "":
            details["label"] = label.text_content()

        actions.append(
            ActionElement(
                xpath=xpath,
                html_element=element.text_content(),
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

        content = get_text_from_element(element)

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

        content = get_text_from_element(element)

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


def simplify_html(
    root: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Simplify the HTML by removing unnecessary tags and attributes.

    Args:
        root (HtmlElement): Root element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    # replace elements with no text content with a single space
    while True:
        elements = root.xpath("//*[not(normalize-space())]")

        # repeat until no more elements are found
        if len(elements) == 0 or drop_tag_elements(elements) is False:
            break

    # remove tags from elements that contain only one child element
    while True:
        elements = root.xpath("//*[count(*) = 1]")

        # repeat until no more elements are found
        if len(elements) == 0 or drop_tag_elements(elements) is False:
            break

    # remove tags that are purely cosmetic
    # e.g. <div>hello <span>world</span></div> -> <div>hello world</div>
    for tag in cosmetic_tags:
        drop_tag_elements(root.xpath(f"//{tag}"))

    # remove attributes from all elements
    for e in root.iter():  # type: ignore
        e.attrib.clear()

    return root, tree


def get_text_from_element(element: HtmlElement) -> str:
    """Get the text content of an HTML element.

    Note:
        This function will add `|` between text content of nested elements.

    Args:
        element (HtmlElement): HTML element

    Returns:
        str: Text content of the HTML element
    """

    # create a deep copy of the element to prevent modifying the original element
    element = element.__deepcopy__(None)

    # add `|` between text content of nested elements
    for child in element.iter(None):
        child.tail = " | " + child.tail if child.tail is not None else " | "

    content = sub(r"\s+", " ", element.text_content())  # remove extra spaces
    content = sub(r"(?: \|)+", " |", content).strip()  # remove repeated `|` characters
    content = sub(r"\|$", "", content)  # remove trailing `|`
    content = sub(r"^\|", "", content)  # remove leading `|`

    return content.strip()


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


def get_selectors_from_rule(property: str, value: str) -> list[str]:
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
            property_exists = False
            value_exists = False

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


def drop_tag_elements(elements) -> bool:
    """Drop the tag from the given elements and append a space to the tail.

    Args:
        elements (list[HtmlElement]): List of HTML elements to remove the tag from

    Returns:
        bool: True if the tag was dropped successfully, False otherwise
    """

    for element in elements:
        try:
            element.tail = " " + element.tail if element.tail is not None else " "
            element.drop_tag()
        except Exception as e:
            log.trace(f"skipped drop_tag on element {element}: {e}")
            return False

    if len(elements) > 0:
        log.trace(f"drop_tag {len(elements)} elements")

    return True
