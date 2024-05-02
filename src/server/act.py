from utils.logging import log, log_func


from litestar import exceptions
from litellm import completion

from dtos import Action, ActionElement, RelationQuery

from utils.prompt import generate_act_prompt, parse_act_response, litellm_logger
from utils.catalog import DEFAULT_MODEL
from utils.file import write_json
from utils.dev import get_timestamp, read_mock_response
import utils.error as error


@log_func()
def act(
    actions: list[ActionElement],
    query: RelationQuery,
    previous_actions: list[str],
    url: str,
    title: str | None,
    model_id: str = DEFAULT_MODEL,
    mock_response: str | None = read_mock_response("data/mock_response_act.txt"),
) -> Action:
    """Predict the next action to take based on the given actions and query.

    Args:
        actions (list[ActionElement]): List of actions to predict from.
        query (RelationQuery): The query of relations to act on.
        previous_actions (list[str]): List of previous actions.
        url (str): The URL of the webpage.
        title (str): The title of the webpage.
        model_id (str): The ID of the LLM model to use for action prediction.
        mock_response (str): The mock response to use for testing.

    Returns:
        Action: The predicted action to take.
    """

    try:
        response = completion(
            messages=generate_act_prompt(url, title, actions, query, previous_actions),
            model=model_id,
            mock_response=mock_response,
            stop="======",
            logger_fn=litellm_logger,
        )

        # Save the response to a file
        write_json(f"logs/{get_timestamp()}_response_act.json", response.json())  # type: ignore

        response_content = response["choices"][0]["message"]["content"]  # type: ignore

        action = parse_act_response(response_content, actions)

        return action

    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to predict actions. {type(e)}: {e}")
        log.exception(e)

        raise exceptions.HTTPException(
            status_code=500,
            detail=f"Couldn't predict next action. {error.CHECK_LLM}",
        )
