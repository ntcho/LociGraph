import re

from lxml.html import HtmlElement
from tinycss2 import parse_stylesheet, serialize

from utils.logging import log


def indent(text: str, bullet: str = "- ", use_bullet: bool = False) -> str:
    """Indent text content with a given bullet.

    Args:
        text (str): Text content to indent
        bullet (str, optional): Bullet to use for indentation. Defaults to "- ".
        use_bullet (bool, optional): Whether to use the bullet for the first line.

    Returns:
        str: Indented text content
    """

    if len(bullet) == 0:
        return text

    bullet_indent = len(bullet) * " "

    lines = text.split("\n")

    result = []

    for i, line in enumerate(lines):
        if i == 0 and use_bullet:
            result.append(bullet + line)
        else:
            result.append(bullet_indent + line)

    return "\n".join(result)


def get_min_indent(text: str) -> str:
    indents = re.findall(r"^[^\S\r\n]+", text, flags=re.MULTILINE)

    if len(indents) > 0:
        return min(indents, key=len)
    else:
        return ""


def get_base_indent(text: str) -> str:
    search = re.search(r"([^\S\r\n]*)\S", text)

    if search is not None:
        return search.group(1)
    else:
        return ""


def get_formatted_text(text: str, bullet: str = "- ") -> str:
    # remove empty line with no indentation
    text = re.sub(r"^\n", "", text, flags=re.MULTILINE)

    sections: list[str] = []

    min_indent = get_min_indent(text)

    if min_indent != "":
        # split text into sections by minimum indentation
        sections = re.split(rf"^{re.escape(min_indent)}$", text, flags=re.MULTILINE)
    else:
        sections = [text]

    # remove empty sections
    sections = [s for s in sections if s.strip() != ""]

    for i, section in enumerate(sections):
        base_indent = get_base_indent(section)

        # remove minimum indentation
        section = re.sub(rf"^{re.escape(base_indent)}", "", section, flags=re.MULTILINE)

        # remove leading empty lines
        section = re.sub(r"^\s+\n", "", section)

        # remove empty lines
        section = re.sub(r"^\s+$\n", "", section, flags=re.MULTILINE)

        # remove trailing empty lines
        section = re.sub(r"\n\s*$", "", section)

        # add bullet for multiple sections
        if len(sections) > 1:
            section = indent(section, bullet=bullet, use_bullet=True)

        sections[i] = section

    return "\n\n".join(sections)


def flatten_element(element: HtmlElement, flattened_content: str | None = None) -> str:
    """Flatten the text content of an HTML element.

    Args:
        element (HtmlElement): HTML element

    Returns:
        str: Flattened text content of the HTML element
    """

    base_indent = get_base_indent(element.text_content())

    if flattened_content is None:
        # get flattened content if not provided
        flattened_content = get_text_content(element)

    # replace element content with indented flattened content
    element.clear()  # type: ignore
    element.text = "\n" + indent(flattened_content, base_indent) + "\n"  # type: ignore

    return flattened_content


def get_text_content(
    element: HtmlElement,
    base_indent: str = "",
    delimiter: str = " | ",
    multiline: bool = True,
) -> str:
    """Get the text content of an HTML element.

    Note:
        This function will add `|` (or given delimiter) between text content of
        nested elements.

    Args:
        element (HtmlElement): HTML element
        delimiter (str, optional): Delimiter between text content of nested elements.
        Defaults to " | ".
        multiline (bool, optional): Whether to keep multiline text content.

    Returns:
        str: Text content of the HTML element
    """

    lines: list[str] = []
    nodes: list = element.xpath("node()")

    for node in nodes:

        # process element nodes
        if type(node) is HtmlElement:
            text = get_text_content(node, multiline=multiline)

            if multiline:
                lines.append(indent(text))
            else:
                lines.append(text)

        # process text nodes
        else:
            text = str(node).strip()
            if text != "":
                text = re.sub(r"\s*\n\s*", "\n", text).strip()

                if multiline:
                    lines.append(indent(text, use_bullet=True))
                else:
                    lines.append(", ".join([t for t in text.split("\n")]))

    if multiline:
        return "\n".join(lines)
    else:
        return "; ".join(lines)

    # create a deep copy of the element to prevent modifying the original element
    element = element.__deepcopy__(None)

    de = re.escape(delimiter.strip())  # escaped delimiter

    # add delimiter between text content of nested elements
    for child in element.iter(None):
        child.tail = delimiter + child.tail if child.tail is not None else delimiter

    content = element.text_content()

    # remove all line breaks
    if not multiline:
        content = re.sub(r"\s*\n+\s*", delimiter, content)

    # remove repeated delimiters
    content = re.sub(rf"(?: ?{de})+", delimiter, content)

    # remove trailing and leading spaces, tabs or delimiters
    content = re.sub(
        rf"(?:^[ \t{de}]*)|(?:[ \t{de}]*$)", "", content, flags=re.MULTILINE
    )

    # remove extra spaces
    content = re.sub(r"[ \t]{2,}", " ", content)

    # replace 3+ line breaks to 2 line breaks
    content = re.sub(r"\n{4,}", "\n\n\n", content)

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
