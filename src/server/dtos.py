from dataclasses import dataclass, field
from enum import Enum

from uuid_extensions import uuid7str

from lxml.html import HtmlElement


@dataclass
class WebpageData:
    url: str
    htmlBase64: str
    imageBase64: str
    language: str


@dataclass
class ActionType(Enum):
    CLICK: str = "CLICK"
    TYPE: str = "TYPE"
    TYPESUBMIT: str = "TYPESUBMIT"
    STOP: str = "STOP"


@dataclass
class ActionTarget:
    xpath: str
    type: str  # "LINK" | "BUTTON" | "INPUT"
    content: str  # text content or value of the element
    details: dict | None  # additional details (e.g. href, placeholder, etc.)


@dataclass
class Action:
    target: ActionTarget
    type: ActionType
    value: str | None  # for TYPE, TYPESUBMIT and STOP


@dataclass
class ParsedWebpageData(WebpageData):
    title: str | None
    content: str | None
    contentMarkdown: str | None
    contentHTML: HtmlElement
    actions: list[ActionTarget]


@dataclass
class Relation:
    entity: str
    attribute: str
    value: str


@dataclass
class ExtractionTarget(Relation):
    entity: str
    attribute: str | None


@dataclass
class Event:
    id: str = field(default=uuid7str(), kw_only=True)


@dataclass
class ScrapeEvent(Event):
    webpage_data: WebpageData


@dataclass
class ExtractionQuery:
    event: ScrapeEvent
    target: ExtractionTarget


@dataclass
class ExtractionEvent(Event):
    query: ExtractionQuery
    results: list[Relation]


@dataclass
class EvaluationQuery:
    event: ExtractionEvent
    actions: list[ActionTarget]


@dataclass
class EvaluationEvent(Event):
    query: ExtractionQuery
    results: list[Relation]
    next_actions: list[ActionTarget] | None  # stop processing if empty
