import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from litellm import completion

from dtos import Relation, RelationQuery

from utils.prompt import generate_evaluate_prompt, parse_evaluate_response
from utils.catalog import DEFAULT_MODEL
from utils.file import write_json
from utils.dev import get_timestamp


def evaluate(
    query: RelationQuery,
    results: list[Relation],
    model_id: str = DEFAULT_MODEL,
    mock_response: str | None = None,
) -> tuple[bool, list[Relation] | None]:
    """Evaluate the extracted relations and determine if the extraction is complete.

    Args:
        query (RelationQuery): The query of relations to extract.
        results (list[Relation]): The extracted relations to evaluate.
        model_id (str, optional): The model ID to use for evaluation. Defaults to "gemini/gemini-pro".
        mock_response (str | None, optional): The mock response to use for evaluation. Defaults to None.
    """

    try:
        response = completion(
            messages=generate_evaluate_prompt(query, results),
            model=model_id,
            mock_response=mock_response,
        )

        # FUTURE: add observability callbacks
        # See more: https://docs.litellm.ai/docs/observability/callbacks

        # Save the response to a file
        write_json(f"logs/response_evaluate_{get_timestamp()}.json", response.json())  # type: ignore

        response_content = response["choices"][0]["message"]["content"]  # type: ignore

        log.debug(response_content)
        is_complete, relations = parse_evaluate_response(response_content)

        return is_complete, relations

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to extract relations. {type(e)}: {e}")
        return False, None
