import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from litellm import completion

from dtos import Action, ActionElement, RelationQuery

from utils.prompt import generate_act_prompt, parse_act_response
from utils.catalog import DEFAULT_MODEL
from utils.file import write_json
from utils.dev import get_timestamp


def act(
    actions: list[ActionElement],
    query: RelationQuery,
    url: str,
    title: str | None,
    model_id: str = DEFAULT_MODEL,
    mock_response: str | None = None,
) -> Action | None:
    """Predict the next action to take based on the given actions and query.

    Args:
        actions (list[ActionElement]): The list of available actions.
        query (RelationQuery): The query of relations to extract.
        url (str): The URL of the webpage.
        title (str | None): The title of the webpage.
        model_id (str, optional): The model ID to use for prediction. Defaults to "gemini/gemini-pro".
        mock_response (str | None, optional): The mock response to use for prediction. Defaults to None.
    """

    try:
        response = completion(
            messages=generate_act_prompt(url, title, actions, query),
            model=model_id,
            mock_response=mock_response,
        )

        # FUTURE: add observability callbacks
        # See more: https://docs.litellm.ai/docs/observability/callbacks

        # Save the response to a file
        write_json(f"logs/response_act_{get_timestamp()}.json", response.json())  # type: ignore

        response_content = response["choices"][0]["message"]["content"]  # type: ignore

        log.debug(response_content)
        action = parse_act_response(response_content, actions)

        return action

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to predict actions. {type(e)}: {e}")
        return None
