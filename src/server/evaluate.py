import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from pprint import pformat

from litellm import completion

from dtos import Relation, RelationQuery
from utils.prompt import generate_evaluate_prompt, parse_evaluate_response
from utils.dev import get_timestamp
from utils.json import write_json


def evaluate(
    query: RelationQuery, results: list[Relation]
) -> tuple[bool, list[Relation] | None]:

    try:
        response = completion(
            model="gemini/gemini-1.5-pro",
            messages=generate_evaluate_prompt(query, results),
            mock_response="TRUE",
        )

        # TODO: add observability callbacks
        # See more: https://docs.litellm.ai/docs/observability/callbacks

        log.debug(pformat(response))

        # Save the response to a file
        write_json(f"response_{get_timestamp()}.json", response)

        is_complete, relations = parse_evaluate_response(
            response["choices"][0]["message"]["content"]  # type: ignore
        )

        return is_complete, relations

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to extract relations. {type(e)}: {e}")
        return False, None
