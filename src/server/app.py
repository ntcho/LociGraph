import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)

from litestar import Litestar, post, get
from os import getenv
from dotenv import load_dotenv

from parse import parse
from filter import filter
from extract import extract_llm, extract_mrebel
from evaluate import evaluate
from act import act
from dtos import (
    Action,
    ModelDetail,
    Query,
    ExtractionEvent,
    Relation,
    EvaluationEvent,
    Response,
    ScrapeEvent,
)

from utils.catalog import read_catalog, DEFAULT_MODEL
from utils.file import read_txt


load_dotenv()  # Load environment variables from `.env` file

ENV: str | None = getenv("ENV")
DEV: bool = ENV != "production" if ENV is not None else True  # true if not production


@post("/process/")
async def process_pipeline(data: Query, model: str = DEFAULT_MODEL) -> Response | None:
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

    query = data.query  # relation query to extract

    # * Step 1: Parse the webpage data into paragraphs
    scrape_event = ScrapeEvent(parse(data.data))
    webpage_data = scrape_event.data

    # * Step 2: Filter relevant elements
    elements, actions = filter(webpage_data, query)

    # * Step 3: Extract relations from filtered elements
    relations: list[Relation] = []
    evaluated_relations: list[Relation] | None = []
    is_complete: bool = False

    # skip extraction if no relevant elements found
    if len(elements) > 0:

        # Extract relations using the app_extract litestar instance
        relations_mrebel = extract_mrebel(
            elements,
            query,
        )

        # Extract relations using the LLM APIs
        relations_llm = extract_llm(
            elements,
            query,
            webpage_data.title,
            model,
            read_txt("data/mock_response_extract.txt") if DEV else None,
        )

        # FUTURE: use asyncio to run both extraction methods concurrently
        # FUTURE: use HTTP 102 or WebSocket to send updates for long requests

        if relations_mrebel is None and relations_llm is None:
            raise RuntimeError("Failed to extract relations.")

        relations.extend(relations_mrebel if relations_mrebel is not None else [])
        relations.extend(relations_llm if relations_llm is not None else [])

        # * Step 4: Evaluate the extraction results
        is_complete, evaluated_relations = evaluate(
            query,
            relations,
            model,
            read_txt("data/mock_response_evaluate.txt") if DEV else None,
        )

        if evaluated_relations is None:
            raise RuntimeError("Failed to evaluate extraction results.")

    # * Step 5: Decide next action based on evaluation results
    next_action: Action | None = None

    if is_complete is False:
        next_action = act(
            actions,
            query,
            webpage_data.url,
            webpage_data.title,
            model,
            read_txt("data/mock_response_act.txt") if DEV else None,
        )

        if next_action is None:
            raise RuntimeError("Failed to predict next action.")

    # * Step 6: Return the extracted relations and next action to browser
    result = EvaluationEvent(
        data=ExtractionEvent(scrape_event, query, relations),
        results=evaluated_relations,
        next_action=next_action,
    )

    # FUTURE: add cloud storage for ExtractionEvent data

    return Response(evaluated_relations, next_action)


models = read_catalog()


@get("/models/")
async def get_models() -> list[str]:
    """Return a list of all available models.

    Returns:
        list[str]: List of available models.
    """

    if models is None:
        raise RuntimeError("Failed to read model catalog.")

    return list(models.keys())


@get("/model/")
async def get_model_detail(model_id: str) -> ModelDetail:
    """Return the details of the given model.

    Args:
        model_id (str): The ID of the model to get details for.

    Returns:
        ModelDetail: The details of the model.
    """

    if models is None:
        raise RuntimeError("Failed to read model catalog.")

    try:
        return models[model_id]
    except KeyError:
        raise RuntimeError(f"Model `{model_id}` not found.")


# Default litestar instance
app = Litestar(
    route_handlers=[process_pipeline, get_models, get_model_detail],
    logging_config=_log.CONFIG,
)


@post("/extract/")
async def extract_relation(data: str) -> list[Relation]:
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

    if data is None or data == "":
        return []

    from models.mrebel import extract

    return extract(data)


# Separate litestar instance for mREBEL model
app_extract = Litestar(route_handlers=[extract_relation], logging_config=_log.CONFIG)
