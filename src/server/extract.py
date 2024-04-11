import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


import requests

from litellm import completion

from dtos import Element, Relation, RelationQuery

from utils.prompt import generate_extract_prompt, parse_extract_response
from utils.catalog import DEFAULT_MODEL
from utils.file import write_json
from utils.dev import get_timestamp, read_mock_response


def extract(
    elements: list[Element],
    query: RelationQuery,
    title: str | None,
    model_id: str = DEFAULT_MODEL,
    mock_response: str | None = read_mock_response("data/mock_response_extract.txt"),
) -> list[Relation]:
    """Extract relation triplets from the given elements."""

    results: list[Relation] = []

    results.extend(extract_mrebel(elements))
    results.extend(extract_llm(elements, query, title, model_id, mock_response))

    # FUTURE: use asyncio to run both extraction methods concurrently
    # FUTURE: use HTTP 102 or WebSocket to send updates for long requests

    return results


def extract_mrebel(elements: list[Element]) -> list[Relation]:
    """Extract relation triplets with mREBEL model.

    Args:
        elements (list[HtmlElements]): List of HTML elements to extract relations from.

    Returns:
        list[Relation]: List of extracted relations. Empty list if the extraction failed.
    """

    try:
        # send a POST request to the app_extract endpoint
        response = requests.post(
            "http://localhost:8001/extract/",
            # send all text content of the relevant elements
            data=("\n".join([e.content for e in elements])),
        )

        if response.ok:
            # unpack json response to list of RelationQuery objects
            return [Relation(**r) for r in response.json()]
        else:
            log.error(f"{response.json()} (code {response.status_code})")
            return []

    except Exception as e:
        log.error(f"Failed to extract relations with mREBEL model.")
        log.exception(e)
        return []


def extract_llm(
    elements: list[Element],
    query: RelationQuery,
    title: str | None,
    model_id: str = DEFAULT_MODEL,
    mock_response: str | None = None,
) -> list[Relation]:
    """Extract relation triplets with LLMs.

    Args:
        elements (list[Element]): List of elements to extract relations from.
        query (RelationQuery): The query of relations to extract.
        title (str): The title of the webpage.

    Returns:
        list[Relation]: List of extracted relations triplets or None if the
        extraction failed.
    """

    try:
        response = completion(
            messages=generate_extract_prompt(title, elements, query),
            model=model_id,
            mock_response=mock_response,
        )

        # FUTURE: add observability callbacks
        # See more: https://docs.litellm.ai/docs/observability/callbacks

        # Save the response to a file
        write_json(f"logs/response_extract_{get_timestamp()}.json", response.json())  # type: ignore

        response_content = response["choices"][0]["message"]["content"]  # type: ignore

        log.debug(response_content)
        results = parse_extract_response(response_content)  # type: ignore

        return results

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to extract relations with LLM `{model_id}`.")
        log.exception(e)
        return []
