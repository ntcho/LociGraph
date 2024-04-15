from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional
from math import prod

from uuid_extensions import uuid7str
from lxml.html import HtmlElement
from lxml.etree import _ElementTree


@dataclass
class Element:
    """Class that represents an element on a webpage.

    Attributes:
        xpath (str): The full XPath of the element.
        html_element (HtmlElement): The HTML element.
        content (str): The text content of the element.
        details (dict | None): Additional attributes of the element.
        relevance (dict[str, float] | None): The relevance score of the element.
    """

    xpath: str
    html_element: HtmlElement
    content: str | None
    details: (
        dict[Literal["placeholder", "aria-label", "label", "href", "value"], str] | None
    ) = None
    relevance: dict[str, float] | None = None

    def getdetails(self) -> str:
        """Get the details of the element in a string format `key1='value1', key2='value2', ...`.

        Returns:
            str: The details of the element. Defaults to an empty string if not set."""

        if self.details is None:
            return ""

        return ", ".join(
            [f"{k}='{v}'" for k, v in self.details.items() if v is not None or v != ""]
        )

    def getrelevancy(self) -> float:
        """Get the relevance score of the element.

        Note:
            The relevance score is calculated as the product of all values
            of the element's relevance dict.

        Returns:
            float: The relevance score of the element. Defaults to 0 if not set."""

        return 0 if self.relevance is None else prod(self.relevance.values())

    def __lt__(self, other) -> bool:
        if not isinstance(other, Element):
            return False

        self_relevance = self.getrelevancy()
        other_relevance = other.getrelevancy()

        # higher relevance is better
        if self_relevance != other_relevance:
            return self_relevance > other_relevance

        # shorter xpath is better
        if len(self.xpath) != len(other.xpath):
            return len(self.xpath) < len(other.xpath)

        # lexicographically smaller xpath is better
        # e.g. /html/body/div[1] is better than /html/body/div[2]
        return self.xpath < other.xpath

    def getrepr(self) -> str:
        """Get the representation of the element in a string format `xpath='...',
        relevancy='0.0' relevance={k: v} details={k: v}, content='...'`.
        """

        details = "" if self.details is None else f" details={{{self.getdetails()}}}"
        relevance = (
            ""
            if self.relevance is None
            else f" relevancy={self.getrelevancy()} relevance={{{self.relevance}}}"
        )
        content = "" if self.content is None else f" content='{self.content}'"
        return f"xpath='{self.xpath}'{relevance}{details}{content}"

    def __repr__(self) -> str:
        """Get the representation of the element in a string format `xpath='...',
        relevancy='0.0' relevance={k: v} details={k: v}, content='...'`.
        """

        return f"<dtos.{self.__class__.__name__} {self.getrepr()}>"


type ActionElementType = Literal["LINK", "BUTTON", "INPUT"]


@dataclass
class ActionElement(Element):
    """Class that represents an interactive element on a webpage.

    Note:
        See `extract_html()` in `extract.py` for more details how action elements
        are parsed from HTML.

    Attributes:
        xpath (str): The full XPath of the element.
        html_element (HtmlElement): The HTML element.
        content (str): The text content or input value of the element.
        details (dict | None): Additional attributes of the element (e.g. href, placeholder, etc.).
        relevance (dict[str, float] | None): The relevance score of the element.
        id (int): The unique identifier of the element. Used to reference the element in actions.
        type (Literal["LINK", "BUTTON", "INPUT"]): The type of the element.
    """

    id: int = -1
    type: ActionElementType = "LINK"

    def __str__(self) -> str:
        if self.id < 0:
            raise ValueError("Element ID not set")

        if self.type == "INPUT":
            label = self.getinputlabel()
            label = "" if label is None else f" '{label}'"

            value = self.getinputvalue()
            value = "" if value is None or value == "" else f" (value='{value}')"

            return f"[{self.id}] {self.type}{label}{value}"
        else:
            content = (
                ""
                if self.content is None or self.content == ""
                else f" '{self.content}'"
            )

            if self.details is None:
                return f"[{self.id}] {self.type}{content}"

            return f"[{self.id}] {self.type}{content} ({self.getdetails()})"

    def getinputvalue(self) -> str | None:
        # try to use the value attribute if available, otherwise use the content
        return (
            self.details["value"]
            if self.details is not None and self.details.get("value", None) is not None
            else self.content
        )

    def getinputlabel(self) -> str | None:
        # try to use the label attribute if available, otherwise try to use the aria-label
        placeholder = (
            self.details.get("placeholder", None) if self.details is not None else None
        )

        if placeholder is not None:
            return placeholder

        aria_label = (
            self.details.get("aria-label", None) if self.details is not None else None
        )

        return aria_label

    def getresponseobject(self) -> "ActionElement":
        """Remove unserializable attributes from the action element."""

        copy = self.__class__(
            self.xpath,
            self.html_element,
            self.content,
            self.details,
            self.relevance,
            self.id,
            self.type,
        )

        del copy.html_element
        del copy.relevance

        return copy

    def getrepr(self) -> str:
        """Get the representation of the action element in a string format `id=0,
        type='TYPE' xpath='...', relevancy='0.0' relevance={k: v} details={k: v},
        content='...'`.
        """
        return f"id={self.id}, type={self.type} {super().getrepr()}"

    def __repr__(self) -> str:
        """Get the representation of the action element in a string format `id=0,
        type='TYPE' xpath='...', relevancy='0.0' relevance={k: v} details={k: v},
        content='...'`.
        """

        return f"<dtos.{self.__class__.__name__} {self.getrepr()}>"


type ActionType = Literal["CLICK", "TYPE", "TYPESUBMIT"]


@dataclass
class Action:
    """Class that represents an action to be taken on a webpage.

    Attributes:
        element (ActionElement): The interactive element to perform the action on.
        type (Literal["CLICK", "TYPE", "TYPESUBMIT"]): The type of action.
        value (str | None): The value to input. Used for TYPE, TYPESUBMIT and STOP actions.
    """

    element: ActionElement
    type: ActionType
    value: str | None  # for TYPE and TYPESUBMIT

    def getresponseobject(self):
        """Remove unserializable attributes from the action element."""
        return self.__class__(self.element.getresponseobject(), self.type, self.value)

    def __repr__(self) -> str:
        """Get the representation of the action in a string format `type='...', value='...',
        element=...`.
        """

        value = "" if self.value is None else f" value='{self.value}'"
        return f"<dtos.{self.__class__.__name__} type={self.type}{value} element={self.element.__repr__()}>"


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
    imageBase64: str  # FUTURE: use screenshot image with multimodal models
    language: str

    def __repr__(self) -> str:
        """Get the representation of the webpage data in a string format `url='...',
        language='...', len(htmlBase64)=0, len(imageBase64)=0`."""
        return f"<dtos.{self.__class__.__name__} {self.getrepr()}>"

    def getrepr(self) -> str:
        """Get the representation of the webpage data in a string format `url='...',
        language='...', len(htmlBase64)=0, len(imageBase64)=0`.
        """

        return f"url='{self.url}' language='{self.language}' len(htmlBase64)={len(self.htmlBase64)} len(imageBase64)={len(self.imageBase64)}"


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

    def getrepr(self) -> str:
        content = "" if self.content is None else f" len(content)={len(self.content)}"
        return f"title='{self.title}' actions=[{self.actions}]{content} {super().getrepr()}"

    def __repr__(self) -> str:
        """Get the representation of the parsed webpage data in a string format
        `title='...', actions=[...], len(content)=0, url='...', language='...',
        len(htmlBase64)=0, len(imageBase64)=0`.
        """

        return f"<dtos.{self.__class__.__name__} {self.getrepr()}>"


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

    def __str__(self) -> str:
        return f"[{self.entity}, {self.attribute}, {self.value}]"

    def __repr__(self) -> str:
        """Get the representation of the relation in a string format `[entity, attribute, value]`."""

        return f"<dtos.{self.__class__.__name__} {self.__str__()}>"


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

    def __str__(self) -> str:
        attribute = self.attribute if self.attribute is not None else "?"
        value = self.value if self.value is not None else "?"

        return f"[{self.entity}, {attribute}, {value}]"

    def getobjective(self) -> str:
        if self.entity is None:
            raise AttributeError("Query entity not found")
        elif self.attribute is not None and self.value is not None:
            return f"Verify whether entity `{self.entity}` has attribute `{self.attribute}` with the value `{self.value}`."
        elif self.attribute is not None:
            return f"Find the value of attribute `{self.attribute}` of entity `{self.entity}`."
        else:
            return f"Find all attribute of entity `{self.entity}`."

    def __repr__(self) -> str:
        """Get the representation of the relation query in a string format `[entity, attribute, value]`."""
        return f"<dtos.{self.__class__.__name__} {self.__str__()}>"


@dataclass
class Event:
    """Base class for all event dataclasses.

    Attributes:
        id (str): UUIDv7 including the timestamp of the event.
    """

    id: str = field(default=uuid7str(), kw_only=True)

    def __repr__(self) -> str:
        """Get the representation of the event in a string format `id='...'`."""

        return f"<dtos.{self.__class__.__name__} id='{self.id}'>"


@dataclass
class ScrapeEvent(Event):
    """Class that represents a webpage scrape/parse event.

    Attributes:
        id (str): UUIDv7 including the timestamp of the event.
        data (ParsedWebpageData): Parsed webpage data including the full DOM tree.
    """

    data: ParsedWebpageData

    def __repr__(self) -> str:
        """Get the representation of the scrape event in a string format `id='...', data=...`."""

        return f"<dtos.{self.__class__.__name__} id='{self.id}' data={self.data.__repr__()}>"


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

    def __repr__(self) -> str:
        """Get the representation of the extraction event in a string format `id='...',
        query=..., results=[...], data=...`.
        """

        return f"<dtos.{self.__class__.__name__} id='{self.id}' query={self.query.__repr__()} results={self.results} data={self.data.__repr__()}>"


@dataclass
class EvaluationEvent(Event):
    """Class that represents evaluation event for an extraction task.

    Attributes:
        data (ExtractionEvent): The extraction event including the data and the
        extracted relations.
        confidence_level (str | None): The confidence level of the extraction results.
        next_action (ActionElement | None): The next action to take based on the
    """

    results: list[Relation]
    next_action: Action | None  # None if extraction is complete
    data: Optional[ExtractionEvent] = None
    confidence_level: Optional[str] = None  # FUTURE: use top-K prompting strategy

    def getresponse(self) -> "Response":
        return Response(self.results, self.next_action, self.confidence_level)

    def __repr__(self) -> str:
        """Get the representation of the evaluation event in a string format `id='...',
        next_action=..., confidence_level='...', results=[...], data=...`.
        """

        next_action = (
            ""
            if self.next_action is None
            else f" next_action={self.next_action.__repr__()}"
        )
        confidence_level = (
            ""
            if self.confidence_level is None
            else f" confidence_level={self.confidence_level}"
        )
        return f"<dtos.{self.__class__.__name__} id='{self.id}'{next_action}{confidence_level} results={self.results} data={self.data.__repr__()}>"


@dataclass
class Query:
    """Type definition for the extraction query.

    Attributes:
        data (WebpageData): The raw webpage data to extract relations from.
        query (Relation): The relation to extract.
    """

    data: WebpageData
    query: RelationQuery

    def __repr__(self) -> str:
        """Get the representation of the query in a string format `data=..., query=...`."""

        return f"<dtos.{self.__class__.__name__} data={self.data.__repr__()} query={self.query.__repr__()}>"


@dataclass
class Response:
    """Type definition for the extraction response.

    Attributes:
        results (list[Relation]): The extracted relations.
        next_action (Action | None): The next action to take based on the extraction results.
        confidence_level (str | None): The confidence level of the extraction results.
    """

    results: list[Relation]
    next_action: Action | None
    confidence_level: Optional[str] = None

    def __init__(
        self,
        results: list[Relation],
        next_action: Action | None,
        confidence_level: Optional[str] = None,
    ):
        """Initialize the response object.

        Note:
            The `HtmlElement` of `next_action` will be removed for serialization.

        Args:
            results (list[Relation]): The extracted relations.
            next_action (Action | None): The next action to take based on the extraction results.
            confidence_level (str | None): The confidence level of the extraction results.
        """

        self.results = results
        self.next_action = (
            next_action.getresponseobject() if next_action is not None else None
        )
        self.confidence_level = confidence_level

    def __repr__(self) -> str:
        """Get the representation of the response in a string format `results=[...],
        next_action=..., confidence_level='...'`.
        """

        next_action = (
            ""
            if self.next_action is None
            else f" next_action={self.next_action.__repr__()}"
        )
        confidence_level = (
            ""
            if self.confidence_level is None
            else f" confidence_level={self.confidence_level}"
        )
        return f"<dtos.{self.__class__.__name__} results={self.results}{next_action}{confidence_level}>"


@dataclass
class ModelDetail:
    """Class that represents the details of a model supported via LiteLLM."""

    litellm_provider: str
    mode: Optional[str]
    source: Optional[str]
    max_tokens: Optional[float]
    max_input_tokens: Optional[float]
    max_output_tokens: Optional[float]
    input_cost_per_token: Optional[float]
    output_cost_per_token: Optional[float]
    input_cost_per_pixel: Optional[float]
    output_cost_per_pixel: Optional[float]
    input_cost_per_second: Optional[float]
    output_cost_per_second: Optional[float]
    max_images_per_prompt: Optional[float]
    max_videos_per_prompt: Optional[float]
    max_video_length: Optional[float]
    output_vector_size: Optional[float]
    output_cost_per_image: Optional[float]
    input_cost_per_request: Optional[float]
    supports_function_calling: Optional[bool]
    supports_parallel_function_calling: Optional[bool]
