from utils.logging import log, log_func


from litellm import completion
from litestar import exceptions

from dtos import Relation, RelationQuery

from utils.prompt import (
    generate_evaluate_prompt,
    parse_evaluate_response,
    litellm_logger,
)
from utils.catalog import DEFAULT_MODEL
from utils.file import write_json
from utils.dev import get_timestamp, read_mock_response
import utils.error as error


@log_func()
def evaluate(
    query: RelationQuery,
    results: list[Relation],
    model_id: str = DEFAULT_MODEL,
    mock_response: str | None = read_mock_response("data/mock_response_evaluate.txt"),
) -> tuple[bool, list[Relation]]:
    """Evaluate the extracted relations and determine if the query is completed.

    Args:
        query (RelationQuery): The query of relations to evaluate.
        results (list[Relation]): The list of relations to evaluate.
        model_id (str): The ID of the LLM model to use for evaluation.
        mock_response (str): The mock response to use for testing.

    Returns:
        bool, list[Relation]: A boolean indicating whether the query is completed and
        a list of evaluated relations.
    """

    try:
        response = completion(
            messages=generate_evaluate_prompt(query, results),
            model=model_id,
            mock_response=mock_response,
            stop="======",
            logger_fn=litellm_logger,
        )

        # Save the response to a file
        write_json(f"logs/{get_timestamp()}_response_evaluate.json", response.json())  # type: ignore

        response_content = response["choices"][0]["message"]["content"]  # type: ignore

        is_complete, relations = parse_evaluate_response(response_content)

        return is_complete, relations

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to evaluate {len(results)} relations with LLM `{model_id}`")
        log.exception(e)

        raise exceptions.HTTPException(
            status_code=500,
            detail=f"Couldn't evaluate current progress. {error.CHECK_LLM}",
        )
