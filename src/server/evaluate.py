import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from pprint import pformat

from litellm import completion

from utils.prompt import generate_evaluate_prompt
from dtos import ExtractionEvent, ActionElement, EvaluationEvent, Relation

# import openai

# inspired by https://github.com/nat/natbot
# TODO: add 3 examples
prompt_template = """
Imagine that you are imitating humans using a web browser for a task, step by step. 
After each task, you can see a part of webpage like humans by a screenshot and know the previous 
actions before the current step decided by yourself through recorded history

You are an agent controlling a browser. You are given:

    (1) an objective that you are trying to achieve
    (2) the URL of your current web page
    (3) a simplified description of the content of the webpage (more on that below)

You can issue these commands:

    CLICK [X] - click element with id X. You can only click on LINK and BUTTON!
    TYPE [X] 'text' - type the specified text into INPUT element with id X.
    TYPESUBMIT [X] 'text' - same as TYPE above, except this command presses ENTER to submit the form
    STOP 'answer' - stop the process and provide the final answer

The format of the browser content is highly simplified; all formatting elements are stripped.
Interactive elements such as LINK, INPUT, BUTTON are represented like this:

    [1] LINK 'link text' (href='https://example.com')
    [2] BUTTON 'button text'
    [3] INPUT 'placeholder or label text' (value='initial value')

Based on your given objective, issue whatever command you believe will get you closest to achieving your goal.

If you find yourself on Google and there are no search results, you should probably issue a command 
like "TYPESUBMIT 7 "search query"" to get to a more useful page.

Then, if you find yourself on a Google search results page, you might issue the command "CLICK 24" to click
on the first link in the search results. (If your previous command was a TYPESUBMIT your next command should
probably be a CLICK.)

==================================================

The current browser status is provided below.

CURRENT PAGE URL: $url
CURRENT PAGE TITLE: $title

CURRENT BROWSER CONTENT:
```
$browser_content
```

PREVIOUS COMMANDS:
```
$previous_command
```

OBJECTIVE: $objective


Follow the following guidance to think step by step before outlining the next action step at the current stage:

1. IDENTIFY CURRENT CONTENT:
First, think about what the current webpage is.

2. ANALYZE PREVIOUS COMMANDS:
Second, combined with the content, analyze each step of the previous action history 
and their intention one by one. Particularly, pay more attention to the last step, 
which may be more related to what you should do now as the next step.

3. DECIDE NEXT COMMAND:
Last, conclude your answer using the format below. Ensure your answer is strictly 
adhering to the format provided below. Please do not leave any explanation in your 
answers of the final standardized format part, and this final part should be clear 
and certain.

To be successful, it is important to follow the following rules: 
1. You should only issue command `CLICK [X]`, `TYPE [X] 'text'` or `TYPESUBMIT [X] 'text'`.
2. You should only issue ONE command at a time.

YOUR COMMAND:
"""


def evaluate(
    extraction_event: ExtractionEvent, results: list[Relation]
) -> EvaluationEvent | None:

    try:
        response = completion(
            model="gemini/gemini-1.5-pro",
            messages=generate_evaluate_prompt(extraction_event, results),
            mock_response="TRUE",
        )

        # TODO: add observability callbacks
        # See more: https://docs.litellm.ai/docs/observability/callbacks

        log.info(pformat(response))

        return None
    except Exception as e:
        # See more: https://docs.litellm.ai/docs/exception_mapping
        log.error(f"Failed to extract relations. {type(e)}: {e}")
        return None
