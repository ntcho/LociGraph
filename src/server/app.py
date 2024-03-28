import logging
from utils.logging import CONFIG, FORMAT

logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

from litestar import Litestar, post

from parse import parse
from filter import filter
from extract import extract_llm, extract_mrebel
from evaluate import evaluate
from dtos import (
    ExtractionQuery,
    ExtractionEvent,
    Relation,
    EvaluationEvent,
)


@post("/process/")
async def processHandler(data: ExtractionQuery) -> EvaluationEvent | None:
    """Process the given extraction query.

    Note:
        Use `LITESTAR_APP=app:app litestar run --port 8000 --pdb --reload`
        to start the server.

    Args:
        data (ExtractionQuery): The extraction query to process.

    Returns:
        list[EvaluationEvent] | None: The evaluation events or None if the
        process failed.
    """

    # * Step 1: Parse the webpage data into paragraphs
    webpage = parse(data.event.webpage_data)

    if webpage is None or webpage.content is None:
        raise Exception("Invalid webpage data.")

    # * Step 2: Filter relevant elements
    relevant_elements = filter(webpage.contentHTML, data.target)

    # * Step 3: Extract relations from filtered elements
    relations: list[Relation] = []

    # TODO: possibly use HTTP 102 or WebSocket to send updates for long requests
    # Extract relations using the app_extract litestar instance
    relations_mrebel = extract_mrebel(relevant_elements, data.target)
    # Extract relations using the LLM APIs
    relations_llm = extract_llm(relevant_elements, data.target)

    if relations_mrebel is None and relations_llm is None:
        raise Exception("Failed to extract relations.")

    relations.extend(relations_mrebel if relations_mrebel is not None else [])
    relations.extend(relations_llm if relations_llm is not None else [])

    extraction_event = ExtractionEvent(query=data, results=relations)
    # upload(extraction_event)  # TODO: add cloud upload functionality

    # * Step 4: Evaluate the extraction results
    evaluation_event = evaluate(extraction_event, relations)

    # TODO: add confidence level & evaluation

    return evaluation_event


# Default litestar instance
app = Litestar(route_handlers=[processHandler], logging_config=CONFIG)


@post("/extract/")
async def extractHandler(data: str) -> list[Relation]:
    """Extract relation triplets from the given paragraph.

    Note:
        This litestar app runs on a separate litestar instance in order to
        enable hot reload on the main litestar app.
        Use `LITESTAR_APP=app:app_extract litestar run --port 8001 --pdb` to
        start the server.

    Args:
        data (str): String containing the paragraph to extract relations from.

    Returns:
        list[Relation]: List of extracted relations triplets.
    """

    print(f"Extracting triplets from text: \n```\n{data}\n```")

    from extract_mrebel import extract

    if data is None or data == "":
        return []

    return extract(data)


# Separate litestar instance for mREBEL model
app_extract = Litestar(route_handlers=[extractHandler], logging_config=CONFIG)
