import logging

from utils.logging import FORMAT

logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


import requests
from lxml.html import HtmlElement

from dtos import Relation, RelationQuery


def extract_mrebel(
    elements: list[HtmlElement], target: RelationQuery
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
                [e for e in element_contents if target.entity.lower() in e.lower()]
            )
        ),
    )

    if response.status_code == 201:
        # unpack json response to list of RelationQuery objects
        return [Relation(**r) for r in response.json()]
    else:
        logging.error(
            f"Failed to extract relations. app_extract returned code {response.status_code}"
        )
        return None


def extract_llm(
    elements: list[HtmlElement], target: RelationQuery
) -> list[Relation] | None:
    """Extract relation triplets with LLMs.

    Args:
        elements (list[HtmlElements]): List of HTML elements to extract relations from.
        target (RelationQuery): The query of relations to extract.

    Returns:
        list[Relation]: List of extracted relations triplets or None if the
        extraction failed.
    """
    element_contents: list[str] = [e.text_content() for e in elements]

    return None  # TODO: add prompt for LLM extraction

    # response = requests.post(
    #     "http://localhost:8002/extract/",
    #     # send all text content of the relevant elements
    #     data=(
    #         "\n".join(
    #             # filter elements with target entity (e.g. paragraph with entity name)
    #             [e for e in element_contents if target.entity.lower() in e.lower()]
    #         )
    #     ),
    # )

    # if response.status_code == 200:
    #     # unpack json response to list of RelationQuery objects
    #     return [RelationQuery(**r) for r in response.json()]
    # else:
    #     logging.error(
    #         f"Failed to extract relations. API returned code {response.status_code}"
    #     )
    #     return None
