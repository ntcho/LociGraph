from dataclasses import dataclass, field

from uuid_extensions import uuid7str


@dataclass
class WebpageData:
    url: str
    title: str
    htmlBase64: str
    imageBase64: str
    language: str


@dataclass
class Action:
    value: str  # description of the action (e.g. button text, link text, etc.)
    type: str  # TODO: change to enum
    target: str  # TODO: add detailed definition (e.g. xpath, css selector, etc.)


@dataclass
class ParsedWebpageData(WebpageData):
    content: str
    contentMarkdown: str
    contentXML: str
    actions: list[Action]


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
    targets: list[ExtractionTarget]


@dataclass
class ExtractionEvent(Event):
    query: ExtractionQuery
    results: list[Relation]


@dataclass
class EvaluationQuery:
    event: ExtractionEvent
    actions: list[Action]


@dataclass
class EvaluationEvent(Event):
    query: ExtractionQuery
    results: list[Relation]
    next_actions: list[Action] = None  # stop processing if empty
