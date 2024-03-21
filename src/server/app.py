import logging
from utils.logging import FORMAT

logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


import requests
import importlib
from litestar import Litestar, post

from dtos import ExtractionQuery, ExtractionEvent, Relation, EvaluationEvent

from parse import parse
from filter import filter
from evaluate import evaluate


@post("/process/")
async def processHandler(data: ExtractionQuery) -> list[EvaluationEvent]:

    # Step 1: Parse the webpage data into paragraphs
    parsed_webpage_data = parse(data.event.webpage_data)
    paragraphs = parsed_webpage_data.content.split("\n")
    actions = parsed_webpage_data.actions

    # Step 2: Filter relevant paragraphs
    filtered_paragraphs = filter(paragraphs, [t.attribute for t in data.targets])

    # Step 3: Extract relations from the filtered paragraphs
    relations: list[Relation] = []

    for paragraph in filtered_paragraphs:
        # Extract relations using the app_extract litestar instance
        response = requests.post("http://localhost:8001/extract/", data=paragraph)

        relations.append(
            Relation(**response.json())  # unpack json response to Relation object
        )

    extraction_event = ExtractionEvent(query=data, results=relations)
    # upload(extraction_event)  # TODO: add cloud upload functionality

    # TODO: possibly use HTTP 102 or WebSocket to send progress updates

    # Step 4: Evaluate the extraction results
    evaluation_event = evaluate(extraction_event, actions)

    # TODO: add confidence level & evaluation

    return evaluation_event


# Default litestar instance
app = Litestar([processHandler])


@post("/extract/")
async def extractHandler(data: str) -> list[Relation]:
    """Extract relation triplets from the given paragraph.

    Note:
        This litestar app runs on a separate litestar instance in order to
        enable hot reload on the main litestar app.

    Args:
        data (str): String containing the paragraph to extract relations from.

    Returns:
        list[Relation]: List of extracted relations triplets.
    """

    extract = importlib.import_module("extract")

    if data is None or data == "":
        return []

    return extract.extract(data)


# Separate litestar instance for mREBEL model
app_extract = Litestar([extractHandler])
