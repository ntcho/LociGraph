from utils.logging import log, log_func

import re
import concurrent.futures

from lxml.html import HtmlElement
from lxml.cssselect import CSSSelector
from tinycss2 import parse_stylesheet, serialize


FLAG_ATTRIBUTE_TYPE = "locigraph-type"
FLAG_VALUE_NOISE = "NOISE"
FLAG_VALUE_SIMPLIFIED = "SIMPLIFIED"

FLAG_ATTRIBUTE_XPATH = "locigraph-xpath"


# pre-defined indentation tabs
TAB: dict[int, str] = {
    0: "",
    1: " ",
    2: "  ",
    3: "   ",
    4: "    ",
}


# pre-defined indentation tabs with bullet points
TAB_BULLET: dict[int, str] = {
    0: "",
    1: "-",
    2: "- ",
    3: " - ",
    4: "  - ",
}


def indent(text: str, tab_size: int = 2, bullet: str | None = None) -> str:
    """Indent text content with a given bullet.

    Args:
        text (str): Text content to indent
        tab_size (int, optional): Indentation size. Defaults to 2.
        bullet (str, optional): Bullet point style. Defaults to None.

    Returns:
        str: Indented text content
    """

    if tab_size < 0:
        raise ValueError("`tab_size` should be a positive integer or zero.")

    try:
        tab = TAB[tab_size]
    except KeyError:
        tab = " " * tab_size

    result = re.sub(r"(^.)", rf"{tab}\1", text, flags=re.MULTILINE)

    if bullet is None or len(bullet) == 0:
        # add a tab to the start of all lines
        return result

    try:
        tab_bullet = TAB_BULLET[tab_size]
    except KeyError:
        tab_bullet = " " * (tab_size - 2) + "- "

    if bullet != "-":
        tab_bullet = tab_bullet.replace("-", bullet)

    # replace the first tab with a bullet point
    return re.sub(rf"^{re.escape(tab)}", tab_bullet, result)


def get_text_content(
    element: HtmlElement, multiline: bool = True, bullet: str | None = "-"
) -> str:
    """Get the text content of an HTML element.

    Args:
        element (HtmlElement): HTML element to extract text content
        multiline (bool, optional): Return text content as multiline. Defaults to True.
        bullet (str, optional): Bullet point style. Defaults to "-".

    Returns:
        str: Text content of the HTML element
    """

    # check if the element is already simplified from `parse.py`
    if element.get(FLAG_ATTRIBUTE_TYPE, "") == FLAG_VALUE_SIMPLIFIED:
        return element.text

    lines: list[str] = []
    nodes: list = element.xpath("node()")

    # remove empty nodes
    for i, node in enumerate(nodes):
        if str(node).strip() == "":
            del nodes[i]

    for i, node in enumerate(nodes):

        # process element nodes
        if type(node) is HtmlElement:

            # recursively get text content of child nodes
            text = get_text_content(node, multiline, bullet)

            if multiline:
                if i == 0:
                    # skip indentation if this is the first and only element node
                    # this keeps the first element node indentation consistent
                    lines.append(text)
                else:
                    lines.append(indent(text))
            else:
                lines.append(text)

        # process text nodes
        else:
            text = str(node).strip()
            if text != "":
                text = re.sub(r"\s*\n\s*", "\n", text).strip()

                if multiline:
                    if len(nodes) == 1:
                        # skip indentation if this is the only text node
                        lines.append(text)
                    else:
                        lines.append(indent(text, bullet=bullet))
                else:
                    lines.append(", ".join([t for t in text.split("\n")]))

    result = None

    if multiline:
        result = "\n".join(lines)

        # add bullet points if first line is missing indentation
        if (
            bullet is not None
            and len(lines) > 1
            and result.startswith(bullet) is False
            and result.startswith(" ") is False
        ):
            result = indent(result, bullet=bullet)
    else:
        result = "; ".join([l.strip() for l in lines if l.strip() != ""])

    return result


@log_func(time=True)
def parse_css_to_ast(styleHtmlElements: list[HtmlElement]) -> list:
    """Parse the CSS code in the <style> elements into tinycss2 AST nodes.

    Args:
        styleHtmlElements (list[HtmlElement]): List of <style> elements

    Returns:
        list: List of tinycss2 AST nodes"""

    all_rules = []  # list[tinycss2.ast.Object]

    # multi-threaded parsing of CSS code
    with concurrent.futures.ThreadPoolExecutor() as executor:

        def parse_css(styleElement: HtmlElement):
            css = styleElement.text_content()

            # parse all rules in the CSS code into tinycss2 AST nodes
            # read more: https://doc.courtbouillon.org/tinycss2/stable/api_reference.html#ast-nodes
            rules = parse_stylesheet(css, skip_comments=True, skip_whitespace=True)

            # filter out only qualified rules and at-rules
            rules = [r for r in rules if r.type in ["qualified-rule", "at-rule"]]

            all_rules.extend(rules)
            return len(rules)

        futures = [executor.submit(parse_css, e) for e in styleHtmlElements]
        log.info(f"Parsing {len(futures)} <style> elements into AST nodes")

        for future in concurrent.futures.as_completed(futures):
            try:
                count = future.result()
                if count > 0:
                    log.trace(f"parsed {count} CSS rules")
            except Exception as e:
                log.error(f"Failed to parse CSS code: {e}")

    return all_rules


@log_func(time=True)
def filter_selectors(
    all_rules: list | None, filters: list[tuple[str, str]]
) -> list[CSSSelector]:
    """Get all CSS selectors that contain a CSS rule `{ property: value; }`
    from given `<style>` elements.

    Args:
        property (str): CSS property name
        value (str): CSS property value
        styleHtmlElements (list[HtmlElement]): List of <style> elements

    Returns:
        list[CSSSelector] | None: List of CSS selectors that contain the CSS rule
        `{ property: value; }`
    """

    if all_rules is None:
        log.warning("No CSS rules found. Skipping selector extraction.")
        return []

    # selector for rules that contain `property: value;`
    selectors: list[CSSSelector] = []

    for filter in filters:

        prev = len(selectors)

        for rule in all_rules:
            # index of the property token
            pi = find_token(rule.content, filter[0])
            if pi < 0:
                continue

            # index of the value token
            vi = find_token(rule.content, filter[1], pi + 1)
            if vi < 0:
                continue

            try:
                # serialize the CSS selector rule
                selector = serialize(rule.prelude)

                # try to parse the CSS selector
                selectors.append(CSSSelector(selector, translator="html"))
            except Exception as e:
                # log.trace(f"skipping rule: {e}")
                pass

        log.trace(f"found {len(selectors) - prev} selectors for {filter}")

    return selectors


def find_token(tokens: list, token_value: str, start: int = 0) -> int:
    """Find the index of the ident token that matches the given token value.

    Note:
        Read more about tinycss2 AST tokens:
        https://doc.courtbouillon.org/tinycss2/stable/api_reference.html#tinycss2.ast.IdentToken

    Args:
        tokens (list): List of tinycss2 AST tokens
        token_value (str): Token value to search for
        start (int, optional): Start index to search from. Defaults to 0.
    """

    if start < 0 or tokens is None:
        return -1

    i = start
    while i < len(tokens):
        # check if the token is an ident and matches the token value
        if tokens[i].type == "ident":
            if tokens[i].lower_value == token_value:
                return i
            return -1
        i += 1

    return -1
