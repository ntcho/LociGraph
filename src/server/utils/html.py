from utils.logging import log

import re

from lxml.html import HtmlElement
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


def filter_selectors(all_rules: list | None, property: str, value: str) -> list[str]:
    """Get all CSS selectors that contain a CSS rule `{ property: value; }`
    from given `<style>` elements.

    Args:
        property (str): CSS property name
        value (str): CSS property value
        styleHtmlElements (list[HtmlElement]): List of <style> elements

    Returns:
        list[str]: List of CSS selectors that contain the given CSS rule"""

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

            try:
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
            except Exception as e:
                log.trace(f"skipped parsing CSS rule `{rule}`: {e}")
                # log.exception(e)

    return selectors
