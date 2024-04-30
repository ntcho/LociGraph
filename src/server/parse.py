from utils.logging import log, log_func


import concurrent.futures
from base64 import b64decode
from pprint import pformat

from lxml.html import HtmlElement, fromstring
from lxml.etree import _ElementTree, ElementTree
from lxml.cssselect import CSSSelector

from utils.html import (
    get_text_content,
    filter_selectors,
    parse_css_to_ast,
    FLAG_ATTRIBUTE_TYPE,
    FLAG_VALUE_NOISE,
    FLAG_ATTRIBUTE_XPATH,
    FLAG_VALUE_SIMPLIFIED,
)
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
    """Parse the elements and actions from the given webpage data and simplify the
    DOM tree.

    Args:
        data (WebpageData): Webpage data to parse

    Returns:
        ParsedWebpageData: Parsed webpage data
    """

    log.info(f"Parsing webpage... (url=`{data.url}`)")

    html_text = b64decode(data.htmlBase64).decode("utf-8")

    log.info(f"Parsing HTML... [{len(html_text)} bytes]")

    # parse the HTML using lxml
    html: HtmlElement = fromstring(html_text, base_url=data.url)
    tree: _ElementTree = ElementTree(html)

    log.debug(f"Parsed HTML")

    # parse the title of the webpage
    title = " ".join(html.xpath("//title/text()"))
    title = title if len(title) > 0 else None

    log.debug(f"Parsed title: `{title}`")

    # parse CSS rules to AST nodes
    global all_rules
    all_rules = parse_css_to_ast(html.xpath("//style"))

    # clean and simplify the DOM tree
    html, tree = flag_noise_elements(html, tree)
    html, tree = flag_action_elements(html, tree)
    html, tree = remove_noise_elements(html, tree)
    html, tree = replace_aria_roles(html, tree)
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


# html element attributes that hide elements
noise_attributes = [
    "contains(@class, 'hidden')",
    "contains(@class, 'invisible')",
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
    log.info("Removing comments")
    count = 0
    for element in html.xpath("//comment()"):
        try:
            element.drop_tree()
            count += 1
        except Exception as e:
            log.trace(f"skipped drop_tree on {element}: {e}")
    log.debug(f"removed {count} comments")

    # flag elements that are not visible with element class as noise
    # e.g. <div style="display: none">...</div>
    log.info("Flagging elements with noise attributes")
    count = 0
    for attr in noise_attributes:
        elements = html.xpath(f"//*[{attr}]")

        for element in elements:
            # flag the element and all its children as noise
            for child in element.iter():
                child.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_NOISE)

        count += len(elements)
        if len(elements) > 0:
            log.trace(f"flagged {len(elements)} elements with attr=`{attr}`")
    log.debug(f"flagged {count} elements with {len(noise_attributes)} attributes")

    # flag elements that are not visible via CSS style as noise
    # e.g. <div class="hidden">...</div> & .hidden { display: none; }
    # multi-threaded flagging noise elements
    log.info("Flagging elements with noise styles")
    with concurrent.futures.ThreadPoolExecutor() as executor:

        def flag_elements_with_selector(html: HtmlElement, select: CSSSelector):
            elements = select(html)

            for element in elements:
                # flag the element and all its children as noise
                for child in element.iter():
                    child.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_NOISE)

            return len(elements), select.css

        # flag elements for each selector in parallel
        futures = [
            executor.submit(flag_elements_with_selector, html, selector)
            for selector in filter_selectors(all_rules, noise_styles)
        ]

        count = 0

        for future in concurrent.futures.as_completed(futures):
            try:
                c, css = future.result()
                count += c
                if c > 0:
                    log.trace(f"flagged {c} elements with selector=`{css}`")
            except Exception as e:
                log.trace(f"skipped selector: {e}")

        log.debug(f"flagged {count} elements with {len(noise_styles)} filters")

    # remove elements that doesn't contain text content
    # e.g. <style>...</style> -> ""
    count = 0
    for tag in noise_tags:
        elements = html.xpath(f"//{tag}")

        for element in elements:
            # flag the element and all its children as noise
            for child in element.iter():
                child.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_NOISE)

        count += len(elements)
        if len(elements) > 0:
            log.trace(f"flagged {len(elements)} <{tag}> tags")
    log.trace(f"flagged {count} elements with {len(noise_tags)} tags")

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

# ARIA roles that are considered as action elements
link_aria_widget_roles = ["link"]
button_aria_widget_roles = ["button"]
input_aria_widget_roles = ["textbox", "searchbox"]


@log_func()
def flag_action_elements(
    html: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Flag all interactable elements as actions.

    Args:
        html (HtmlElement): html element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    ### * Extract all interactable elements from the HTML

    links: list[HtmlElement] = []
    buttons: list[HtmlElement] = []
    inputs: list[HtmlElement] = []
    # dropdowns = [] # FUTURE: add support for <select> tags

    log.info("Flagging action elements...")

    # * extract LINK elements
    # all <a> elements with non-empty text content
    links.extend(html.xpath("//a[string-length(text()) > 0]"))
    # all elements with `cursor: pointer` style with non-empty text content
    link_selectors = filter_selectors(all_rules, [("cursor", "pointer")])
    if link_selectors is not None:
        for select_link in link_selectors:
            links.extend(
                [e for e in select_link(html) if len(e.text_content().strip()) > 0]
            )
    # all elements with ARIA role of link
    for role in link_aria_widget_roles:
        links.extend(html.xpath(f"//*[@role='{role}']"))

    log.trace(f"Extracted LINK elements [{len(links)} elements]")

    # * Extract BUTTON elements
    # all <button> element with non-empty text content
    buttons.extend(html.xpath("//button[string-length(text()) > 0]"))
    # all <input> elements with button type attributes
    buttons.extend(html.xpath(f"//input[{input_button_selector}]"))
    # all elements with click event attributes
    buttons.extend(html.xpath(f"//*[{click_event_selector}]"))
    # all elements with ARIA role of button
    for role in button_aria_widget_roles:
        buttons.extend(html.xpath(f"//*[@role='{role}']"))

    log.trace(f"Extracted BUTTON elements [{len(buttons)} elements]")

    # * extract INPUT elements
    # all <input> elements except hidden and button types
    inputs.extend(
        html.xpath(f"//input[not(@type='hidden' or {input_button_selector})]")
    )
    # all <textarea> elements
    inputs.extend(html.xpath("//textarea"))
    # all elements with ARIA role of text input
    for role in input_aria_widget_roles:
        inputs.extend(html.xpath(f"//*[@role='{role}']"))

    log.trace(f"Extracted INPUT elements [{len(inputs)} elements]")

    # * Extract SELECT elements
    # dropdowns.extend(html.xpath("//select")) # FUTURE: add support for <select> tags

    action_elements: dict[ActionElementType, list[HtmlElement]] = {
        "LINK": links,
        "BUTTON": buttons,
        "INPUT": inputs,
    }

    # add original xpath to elements to preserve after cleaning
    for type, elements in action_elements.items():
        for e in elements:
            if e.get(FLAG_ATTRIBUTE_TYPE, None) != FLAG_VALUE_NOISE:
                # flag the element as an action if the element haven't been flagged as noise
                # e.g. <div locigraph-type="LINK" locigraph-xpath="...">
                e.set(FLAG_ATTRIBUTE_TYPE, type)
                e.set(FLAG_ATTRIBUTE_XPATH, tree.getpath(e))

    log.debug(f"Flagged {len(action_elements)} action elements")

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
    log.info("Removing elements flagged as noise")
    count = 0
    for element in html.xpath(f"//*[@{FLAG_ATTRIBUTE_TYPE}='{FLAG_VALUE_NOISE}']"):
        try:
            element.drop_tree()
            count += 1
        except Exception as e:
            log.trace(f"skipped drop_tree on {element}: {e}")
    log.debug(f"removed {count} elements flagged as noise")

    return html, tree


# ARIA landmark roles that should be replaced with HTML tags
# e.g. <div role="banner"> -> <header>
aria_landmark_roles_to_tags = {
    # See https://mdn.io/aria-landmark-role
    "banner": "header",
    "complementary": "aside",
    "contentinfo": "footer",
    "form": "form",
    "main": "main",
    "navigation": "nav",
    "region": "section",
    "search": "form",
}


def replace_aria_roles(
    html: HtmlElement, tree: _ElementTree
) -> tuple[HtmlElement, _ElementTree]:
    """Replace ARIA roles with HTML tags.

    Args:
        html (HtmlElement): html element of the HTML
        tree (_ElementTree): Element tree of the HTML
    """

    # replace ARIA roles with HTML tags
    log.info("Replacing ARIA roles with HTML tags")
    count = 0
    for role, tag in aria_landmark_roles_to_tags.items():
        elements = html.xpath(f"//*[@role='{role}']")

        for element in elements:
            log.trace(f"  replacing {element} to <{tag}>")
            element.tag = tag

        count += len(elements)
        if len(elements) > 0:
            log.trace(
                f"replaced {len(elements)} elements with `role='{role}'` with <{tag}>"
            )
    log.debug(
        f"replaced {count} elements with {len(aria_landmark_roles_to_tags)} roles"
    )

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

    log.info(
        f"Creating ActionElements... [inputs={len(inputs)}, buttons={len(buttons)}, links={len(links)}]"
    )

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
            details["label"] = get_text_content(label, multiline=False)

        actions.append(
            ActionElement(
                xpath=xpath,
                modified_xpath=tree.getpath(element),
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

        content = get_text_content(element, multiline=False)

        if len(content) == 0:
            continue  # skip empty buttons

        actions.append(
            ActionElement(
                xpath=xpath,
                modified_xpath=tree.getpath(element),
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

        content = get_text_content(element, multiline=False)

        if len(content) == 0:
            continue  # skip empty links

        href: str | None = element.get("href", default=None)

        details = {}

        # add href to details if it's not an in-page link
        if href is not None and href != "" and href.startswith("#") is False:
            details["href"] = href

        actions.append(
            ActionElement(
                xpath=xpath,
                modified_xpath=tree.getpath(element),
                html_element=element,
                type="LINK",
                content=content,
                details=(details if len(details) > 0 else None),
            )
        )

    log.trace(f"Created ActionElements: \n```\n{pformat(actions)}\n```")
    log.debug(f"Created {len(actions)} ActionElements")

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
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "i",
    "kbd",
    "mark",
    "meter",
    "output",
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

    # drop tags for `aria-hidden="true"` elements
    log.info("Dropping tags for `aria-hidden='true'` elements")
    drop_tag(html.xpath("//*[@aria-hidden='true']"))

    # remove attributes from all elements
    log.info("Removing attributes from all elements")
    for e in html.iter():  # type: ignore
        e.attrib.clear()

    # replace elements with no text content with a single space
    # e.g. <div></div> -> " "
    log.info("Replacing elements with no text content with a single space")
    drop_tag_from_xpath(html, "//*[not(normalize-space())]")

    # remove tags that are purely cosmetic
    # e.g. <div>hello <span>world</span></div> -> <div>hello world</div>
    log.info("Removing cosmetic tags")
    for tag in cosmetic_tags:
        drop_tag_from_xpath(html, f"//{tag}")

    # replace table contents with markdown-style tables
    # e.g. <tr><td>1</td><td>2</td></tr> -> 1 | 2
    log.info("Replacing table contents with markdown-style tables")
    count = 0
    for table in html.xpath("//table"):

        if len(table.xpath(".//table")) > 0:
            continue  # skip nested tables

        # table content by line
        captions: list[str] = []
        contents: list[str] = []

        # read table content from <tr> tags
        for row in table.xpath(".//tr"):
            text = " | ".join(
                [get_text_content(c, multiline=False) for c in row.iterchildren()]
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
        text = "[table]\n" + "\n".join(captions + contents)

        simplify_element_text(table, text)
        count += 1
    log.debug(f"replaced {count} tables with markdown-style tables")

    # remove tags from elements that contain only one child element
    log.info("Removing tags from elements with 1 children")
    drop_tag_from_xpath(html, "//*[count(*) = 1 and not(normalize-space(text()))]")

    # replace list contents with markdown-style lists
    # e.g. <ul><li>1</li> ... </ul> -> <ul> - 1 ...</ul>
    log.info("Replacing list contents with markdown-style lists")

    for ul in html.xpath("//ul") + html.xpath("//menu"):
        text = "\n".join(
            [
                # bullet points are already added from `get_text_content`
                get_text_content(li)
                for li in ul.iterchildren()
            ]
        )

        simplify_element_text(ul, text)

    for ol in html.xpath("//ol"):
        text = "\n".join(
            [
                # replace first bullet point with index
                get_text_content(li).replace("-", f"{i}.", 1)
                for i, li in enumerate(ul.iterchildren())
            ]
        )

        simplify_element_text(ol, text)

    return html, tree


def drop_tag_from_xpath(root: HtmlElement, xpath: str):
    """Drop the tag from the elements found by the given xpath until no more elements
    are found.

    Args:
        root (HtmlElement): Root element to search for elements
        xpath (str): XPath selector to find elements to drop the tag from
    """
    prev_elements_count = None  # reset the number of elements removed

    while True:
        elements = root.xpath(xpath)

        # repeat until the number of elements found didn't change from previous iteration
        if prev_elements_count == len(elements):
            break

        drop_tag(elements)

        # update the number of elements found
        prev_elements_count = len(elements)


def drop_tag(elements: list[HtmlElement], delimiter: str = " ") -> int:
    """Drop the tag from the given elements and append a space to the tail.

    Args:
        elements (list[HtmlElement]): List of HTML elements to remove the tag from

    Returns:
        int: Number of elements skipped during the operation
    """

    skipped: int = 0

    for element in elements:
        try:
            element.tail = (
                delimiter + element.tail if element.tail is not None else delimiter  # type: ignore
            )
            element.drop_tag()
        except Exception as e:
            log.trace(f"skipped drop_tag on {element}: {e}")
            skipped += 1

    if len(elements) > 0:
        log.debug(f"dropped tags for {len(elements) - skipped} elements")

    return skipped


def simplify_element_text(e: HtmlElement, text: str):
    """Simplify the text content of the given HTML element.

    Args:
        e (HtmlElement): HTML element to simplify the text content of
        text (str): Text content to set to the HTML element
    """

    # clear the element's text content and set the new text content
    e.clear()  # type: ignore
    e.text = text  # type: ignore

    # set the simplified flag to the element
    e.set(FLAG_ATTRIBUTE_TYPE, FLAG_VALUE_SIMPLIFIED)


def debug_html(e, f):
    from lxml.html import tostring
    from utils.file import write_txt

    write_txt(f, tostring(e, pretty_print=True).decode("utf-8"))  # type: ignore
