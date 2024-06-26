from utils.logging import log, log_func


import requests
import concurrent.futures
from json import dumps

from litellm import completion

from dtos import Element, Relation, RelationQuery

from utils.prompt import generate_extract_prompt, parse_extract_response, litellm_logger
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
    """Extract relation triplets from the given elements.

    Args:
        elements (list[Element]): List of elements to extract relations from.
        query (RelationQuery): The query of relations to extract.
        title (str): The title of the webpage.
        model_id (str): The ID of the LLM model to use for extraction.
        mock_response (str): The mock response to use for testing.

    Returns:
        list[Relation]: List of extracted relations triplets or empty list if the
        extraction failed.
    """

    results: list[Relation] = []

    # extract relations with mREBEL and LLMs concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:

        futures = [
            executor.submit(
                extract_mrebel,
                elements,
                title,
            ),
            executor.submit(
                extract_llm,
                elements,
                query,
                title,
                model_id,
                mock_response,
            ),
        ]

        for future in concurrent.futures.as_completed(futures):
            results.extend(future.result())

    return results


@log_func()
def extract_mrebel(elements: list[Element], title: str | None) -> list[Relation]:
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

        contents = [
            e.content
            for e in elements
            # only extract relations from elements with content and high relevancy
            if e.content is not None and e.getrelevancy() > 0.5
        ]

        if len(contents) == 0:
            log.warning("No relevant content to extract relations from.")
            return []

        # start the content with the title of the webpage
        text = f"{title}\n" if title is not None else ""

        # all text content of the relevant elements
        text += "\n".join(contents)

        # send a POST request to the app_extract endpoint
        response = requests.post(
            "http://localhost:8001/extract/",
            data=dumps(text),  # serialize content to JSON
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
            stop="======",
            logger_fn=litellm_logger,
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
