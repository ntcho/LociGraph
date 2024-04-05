from dataclasses import dataclass, field
from typing import Literal, Optional

from uuid_extensions import uuid7str
from lxml.html import HtmlElement


@dataclass
class ActionElement:
    """Class that represents an interactive element on a webpage.

    Note:
        See `extract_html()` in `extract.py` for more details how action elements
        are parsed from HTML.

    Attributes:
        xpath (str): The full XPath of the element.
        type (Literal["LINK", "BUTTON", "INPUT"]): The type of the element.
        content (str): The text content or input value of the element.
        details (dict | None): Additional attributes of the element (e.g. href, placeholder, etc.).
    """

    xpath: str
    type: Literal["LINK", "BUTTON", "INPUT"]
    content: str
    details: dict | None


@dataclass
class Action:
    """Class that represents an action to be taken on a webpage.

    Attributes:
        element (ActionElement): The interactive element to perform the action on.
        type (Literal["CLICK", "TYPE", "TYPESUBMIT", "STOP"]): The type of action.
        value (str | None): The value to input. Used for TYPE, TYPESUBMIT and STOP actions.
    """

    element: ActionElement
    type: Literal["CLICK", "TYPE", "TYPESUBMIT", "STOP"]
    value: str | None  # for TYPE, TYPESUBMIT and STOP


@dataclass
class WebpageData:
    """Class that represents the raw webpage data.

    Attributes:
        url (str): The URL of the webpage.
        htmlBase64 (str): The base64 encoded HTML content of the webpage.
        imageBase64 (str): The base64 encoded screenshot of the webpage.
        language (str): The language of the webpage.
    """

    url: str
    htmlBase64: str
    imageBase64: str
    language: str


@dataclass
class ParsedWebpageData(WebpageData):
    """Class that represents the parsed data from the raw webpage data.

    Attributes:
        title (str | None): The title of the webpage.
        content (str | None): The full text content of the webpage.
        contentMarkdown (str | None): The full text content of the webpage in Markdown format.
        contentHTML (HtmlElement | None): The full text content of the webpage as an HTML element.
        actions (list[ActionElement]): The interactive elements on the webpage.
    """

    title: str | None
    content: str | None
    contentMarkdown: str | None
    contentHTML: HtmlElement | None
    contentTree: _ElementTree | None
    actions: list[ActionElement]


@dataclass
class Relation:
    """Class that represents a relation between entities.

    Note:
        The relation is represented as a triplet (entity, attribute, value).
        For example, the relation "Alex graduated from Bard College" is represented
        as ("Alex", "studied at", "Bard College").

    Attributes:
        entity (str): The entity of the relation.
        attribute (str): The attribute of the entity.
        value (str): The value of the entity attribute.
    """

    entity: str
    attribute: str
    value: str


@dataclass
class RelationQuery(Relation):
    """Class that represents a relation query.

    Note:
        If `attribute` is provided, the objective of the query will be finding
        the value of the given attribute of the entity.
        If `value` is provided, the objective of the query will be verifying whether
        the given entity attribute is equal to the given value.

    Attributes:
        entity (str): The entity of the relation.
        attribute (Optional[str]): The attribute of the entity.
        value (Optional[str]): The value of the entity attribute.
    """

    attribute: Optional[str] = None
    value: Optional[str] = None

    def getobjective(self) -> str:
        if self.entity is None:
            raise AttributeError("Query entity not found")
        elif self.attribute is not None and self.value is not None:
            return f"Verify whether the `{self.entity}` entity has the `{self.attribute}` attribute equal to `{self.value}`."
        elif self.attribute is not None:
            return f"Find the value of the `{self.attribute}` attribute of the `{self.entity}` entity."
        else:
            return f"Find all attribute of the `{self.entity}` entity."


@dataclass
class Event:
    """Base class for all event dataclasses.

    Attributes:
        id (str): UUIDv7 including the timestamp of the event.
    """

    id: str = field(default=uuid7str(), kw_only=True)


@dataclass
class ScrapeEvent(Event):
    """Class that represents a webpage scrape/parse event.

    Attributes:
        id (str): UUIDv7 including the timestamp of the event.
        data (ParsedWebpageData): Parsed webpage data including the full DOM tree.
    """

    data: ParsedWebpageData


@dataclass
class ExtractionEvent(Event):
    """Class that represents relation extraction event.

    Attributes:
        data (ScrapeEvent): The scrape event including the parsed webpage data.
        query (Relation): The query to extract relations for.
        results (list[Relation]): The extracted relations.
    """

    data: ScrapeEvent
    query: RelationQuery
    results: list[Relation]


@dataclass
class EvaluationEvent(Event):
    """Class that represents evaluation event for an extraction task.

    Attributes:
        data (ExtractionEvent): The extraction event including the data and the
        extracted relations.
        confidence_level (str): The confidence level of the extraction results.
        next_action (ActionElement | None): The next action to take based on the
    """

    data: ExtractionEvent
    confidence_level: str
    next_action: ActionElement | None  # stop processing if empty


@dataclass
class Query:
    """Type definition for the extraction query.

    Attributes:
        data (WebpageData): The raw webpage data to extract relations from.
        query (Relation): The relation to extract.
    """

    data: WebpageData
    query: RelationQuery
