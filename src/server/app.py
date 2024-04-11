from typing import Optional
import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)

from litestar import Litestar, post, get, exceptions
from dotenv import load_dotenv

from parse import parse
from filter import filter
from extract import extract
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
import utils.error as error


load_dotenv()  # Load environment variables from `.env` file


@post("/process/")
async def process_pipeline(data: Query, model: str = DEFAULT_MODEL) -> Response:
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

    # Step 1: Parse
    # Parse the base64 webpage data into elements and actions
    scrape = ScrapeEvent(parse(data.data))
    webpage = scrape.data

    # Step 2: Filter
    # Filter relevant elements from webpage
    elements, actions = filter(webpage, query)

    # Step 3: Extract
    # Extract relations from filtered elements
    extraction = ExtractionEvent(scrape, query, [])

    if len(elements) > 0:  # skip if no elements filtered
        extraction.results = extract(elements, query, webpage.title, model)

    # Step 4: Evaluate
    # Evaluate the extraction result
    evaluation = EvaluationEvent([], None, extraction)
    completed: bool = False

    if len(extraction.results) > 0:  # skip if no relations are extracted
        completed, relations = evaluate(query, extraction.results, model)
        evaluation.results = relations

    # Step 5: Act
    # Decide next action based on evaluation result

    if not completed:  # skip if extraction is complete
        next_action = act(actions, query, webpage.url, webpage.title, model)
        evaluation.next_action = next_action

    # Step 6: Respond
    # Return the extracted relations and next action to browser
    return evaluation.getresponse()

    # FUTURE: add cloud storage for ExtractionEvent data


models = read_catalog()


@get("/models/")
async def get_models() -> list[str]:
    """Return a list of all available models.

    Returns:
        list[str]: List of available models.
    """

    if models is None:
        raise exceptions.HTTPException(
            status_code=500,
            detail=f"Failed to load model catalog. {error.CHECK_SERVER}",
        )

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
        raise exceptions.HTTPException(
            status_code=500,
            detail=f"Server couldn't load the model catalog. {error.CHECK_SERVER}",
        )

    try:
        return models[model_id]
    except KeyError:
        raise exceptions.HTTPException(
            status_code=404,
            detail=f"Couldn't find model `{model_id}` in the catalog.",
        )


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
        raise exceptions.HTTPException(
            status_code=400,
            detail=f"Couldn't read request body. {error.CHECK_INPUT}",
        )

    from models.mrebel import extract

    return extract(data)


# Separate litestar instance for mREBEL model
app_extract = Litestar(route_handlers=[extract_relation], logging_config=_log.CONFIG)
