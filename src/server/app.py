from utils.logging import log, log_func


from litestar import Litestar, post, get, exceptions
from dotenv import load_dotenv

from parse import parse
from rank import rank
from extract import extract
from evaluate import evaluate
from act import act

from dtos import (
    ModelDetail,
    RequestBody,
    ExtractionEvent,
    EvaluationEvent,
    ResponseBody,
    ScrapeEvent,
)

from utils.catalog import read_catalog, DEFAULT_MODEL
import utils.error as error


load_dotenv()  # Load environment variables from `.env` file


@post("/process/", sync_to_thread=True)
@log_func()
def process_pipeline(data: RequestBody, model: str = DEFAULT_MODEL) -> ResponseBody:
    """Process the given extraction query.

    Note:
        Use `LITESTAR_APP=app:app litestar run --port 8000 --pdb --reload`
        to start the server.

    Args:
        data (RequestBody): The extraction query to process.
        model (str, optional): The model to use for extraction. Defaults to DEFAULT_MODEL.

    Returns:
        ResponseBody: The response containing the extracted relations and next action.
    """

    query = data.query  # relation query to extract

    # Step 1: Webpage Parsing
    # Parse the base64 webpage data into elements and actions
    scrape = ScrapeEvent(parse(data.data))
    webpage = scrape.data

    # Step 2: Element Ranking
    # Rank and filter relevant elements from webpage
    elements, actions = rank(webpage, query)

    # Step 3: Relation Extraction
    # Extract relations from ranked elements
    extraction = ExtractionEvent(scrape, query, [])

    if len(elements) > 0:  # skip if no elements ranked
        extraction.results = extract(elements, query, webpage.title, model)

    # Step 4: Evaluate
    # Evaluate the extraction result
    evaluation = EvaluationEvent([], None, extraction)
    completed: bool = False

    if len(extraction.results) > 0:  # skip if no relations are extracted
        completed, relations = evaluate(query, extraction.results, model)
        evaluation.results = relations

    # Step 5: Action Prediction
    # Decide next action based on evaluation result

    if not completed:  # skip if extraction is complete
        evaluation.next_action = act(
            actions, query, data.previous_actions, webpage.url, webpage.title, model
        )

    # Step 6: Respond
    # Return the extracted relations and next action to browser
    return evaluation.getresponse()


models = None


@get("/models/", sync_to_thread=False)
@log_func()
def get_models() -> list[str]:
    """Return a list of all available models."""

    global models

    if models is None:
        try:
            models = read_catalog()
        except Exception as e:
            log.exception(e)

    if models is None:
        raise exceptions.HTTPException(
            status_code=500,
            detail=f"Failed to load model catalog. {error.CHECK_SERVER}",
        )

    return list(models.keys())


@get("/model/", sync_to_thread=False)
@log_func()
def get_model_detail(model_id: str) -> ModelDetail:
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
app = Litestar(route_handlers=[process_pipeline, get_models, get_model_detail])
