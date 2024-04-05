import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


import requests
from pprint import pformat

from lxml.html import HtmlElement
from litellm import completion

from dtos import Relation, RelationQuery
from utils.prompt import generate_extract_prompt


def extract_mrebel(
    elements: list[HtmlElement], query: RelationQuery
) -> list[Relation] | None:
    """Extract relation triplets with mREBEL model.

    Args:
        elements (list[HtmlElements]): List of HTML elements to extract relations from.
        target (RelationQuery): The query of relations to extract.

    Returns:
        list[Relation]: List of extracted relations triplets or None if the
        extraction failed.
    """
    element_contents: list[str] = [e.text_content() for e in elements]

    response = requests.post(
        "http://localhost:8001/extract/",
        # send all text content of the relevant elements
        data=(
            "\n".join(
                # filter elements with target entity (e.g. paragraph with entity name)
                [e for e in element_contents if query.entity.lower() in e.lower()]
            )
        ),
    )

    if response.status_code == 201:
        # unpack json response to list of RelationQuery objects
        return [Relation(**r) for r in response.json()]
    else:
        log.error(
            f"Failed to extract relations. app_extract returned code {response.status_code}"
        )
        return None


def extract_llm(
    elements: list[HtmlElement], query: RelationQuery
) -> list[Relation] | None:
    """Extract relation triplets with LLMs.

    Args:
        elements (list[HtmlElements]): List of HTML elements to extract relations from.
        target (RelationQuery): The query of relations to extract.

    Returns:
        list[Relation]: List of extracted relations triplets or None if the
        extraction failed.
    """

    try:
        response = completion(
            model="gemini/gemini-1.5-pro",
            messages=generate_extract_prompt(elements, query),
            mock_response="(Alex, studied at, Bard College)\n(Alex, majored, Computer Science)",
        )

        # TODO: add observability callbacks
        # See more: https://docs.litellm.ai/docs/observability/callbacks

        log.info(pformat(response))

        message = response["choices"][0]["message"]

        return []
    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to extract relations. {type(e)}: {e}")
        return None
