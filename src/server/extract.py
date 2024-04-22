from utils.logging import log, log_func


import requests
from json import dumps

from litellm import completion

from dtos import Element, Relation, RelationQuery

from utils.prompt import generate_extract_prompt, parse_extract_response
from utils.catalog import DEFAULT_MODEL
from utils.file import write_json
from utils.dev import get_timestamp, read_mock_response


@log_func()
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

    return results


@log_func()
def extract_mrebel(elements: list[Element]) -> list[Relation]:
    """Extract relation triplets with mREBEL model.

    Args:
        elements (list[HtmlElements]): List of HTML elements to extract relations from.

    Returns:
        list[Relation]: List of extracted relations. Empty list if the extraction failed.
    """

    try:
        log.info(
            f"Extracting relations with mREBEL model (len(elements)={len(elements)})"
        )

        # all text content of the relevant elements
        content = "\n".join([e.content for e in elements if e.content is not None])

        # send a POST request to the app_extract endpoint
        response = requests.post(
            "http://localhost:8001/extract/",
            data=dumps(content),  # serialize content to JSON
        )

        if response.ok:
            log.success(
                f"Extracted {len(response.json())} relations with mREBEL model."
            )
            # unpack json response to list of RelationQuery objects
            return [Relation(**r) for r in response.json()]
        else:
            log.warning(
                f"Failed to extract relations with mREBEL model (code={response.status_code}, response={response.json()})"
            )
            return []

    except Exception as e:
        log.error(f"Failed to extract relations with mREBEL model.")
        log.exception(e)
        return []


@log_func()
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

        # Save the response to a file
        write_json(f"logs/{get_timestamp()}_response_extract.json", response.json())  # type: ignore

        response_content = response["choices"][0]["message"]["content"]  # type: ignore

        results = parse_extract_response(response_content)  # type: ignore

        return results

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to extract relations with LLM `{model_id}`.")
        log.exception(e)

        return []
