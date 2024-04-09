import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from pprint import pformat

from litellm import completion

from dtos import Action, ActionElement, RelationQuery
from utils.dev import get_timestamp
from utils.json import write_json
from utils.prompt import generate_act_prompt, parse_act_response


def act(
    actions: list[ActionElement], query: RelationQuery, url: str, title: str | None
) -> Action | None:

    try:
        response = completion(
            model="gemini/gemini-1.5-pro",
            messages=generate_act_prompt(url, title, actions, query),
            mock_response="TRUE",
        )

        # TODO: add observability callbacks
        # See more: https://docs.litellm.ai/docs/observability/callbacks

        log.debug(pformat(response))

        # Save the response to a file
        write_json(f"response_{get_timestamp()}.json", response)

        action = parse_act_response(response["choices"][0]["message"]["content"], actions)  # type: ignore

        return action

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to predict actions. {type(e)}: {e}")
        return None
