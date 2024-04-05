import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


import re

from lxml.html import HtmlElement

from dtos import ExtractionEvent, Relation, RelationQuery


# Prompt to extract relation JSON from text
extract_system_prompt = """
You are tasked to extract all relation triplets from the input. The relation format must be in the format of [entity, attribute, value]. If no relations are found in the content, write `[]`.

The following are some examples of the input and output format:

Content: `Alex was born in New York on Jaunary 1st, 2000.`
Query: [Alex, date of birth, ?]
Output:
Query relations:
- [Alex, date of birth, January 1st, 2000]
Additional relations:
- [Alex, place of birth, New York]

Content: `Alex studied Computer Science at Bard College.`
Query: [Alex, educated at, ?]
Output:
Query relations:
- [Alex, educated at, Bard College]
Additional relations:
- [Alex, academic major, Computer Science]
- [Bard College, offers, Computer Science]

Content: `Alex works at ACME Inc as a software engineer.`
Query: [Alex, ?, ?]
Query relations:
- [Alex, works at, ACME Inc]
- [Alex, job title, software engineer]
"""

extract_prompt_template = """
Content: `<content>`
Query: <query>
Output:
"""


def generate_extract_prompt(
    elements: list[HtmlElement], query: RelationQuery
) -> list[dict[str, str]]:
    """Generate a prompt to extract relation JSON from text.

    Args:
        elements (list[HtmlElement]): The list of HTML elements to extract relations from.
        target (RelationQuery): The query of relations to extract.
    """

    element_contents: list[str] = [e.text_content() for e in elements]
    content = "\n".join(element_contents)
    content = re.sub(r"\n+", "\n", content)

    prompt = extract_prompt_template
    prompt = prompt.replace("<content>", content)
    prompt = prompt.replace("<query>", str(query))

    return [
        {"role": "system", "content": extract_system_prompt},
        {"role": "user", "content": prompt},
    ]


# Prompt to evaluate relation JSON
evaluate_prompt_template = """

"""


def generate_evaluate_prompt(
    event: ExtractionEvent, results: list[Relation]
) -> list[dict[str, str]]:

    prompt = evaluate_prompt_template.replace("$url", event.data.data.url)

    if event.data.data.content:
        prompt = prompt.replace("$browser_content", event.data.data.content)
    else:
        # Remove the content placeholder if it is not available
        prompt = prompt.replace(
            "CURRENT BROWSER CONTENT:\n```\n$browser_content\n```\n", ""
        )

    try:
        prompt = prompt.replace("$objective", event.query.getobjective())
    except AttributeError:
        raise RuntimeError("Query objective not found")

    return [{"role": "user", "content": "Lorem ipsum"}]


# Prompt to predict next action
predict_prompt_template = """
Imagine that you are imitating humans using a web browser to achieve an objective, step by step.

You can take these actions:

    CLICK [X] - click element with id X. You can only click on LINK and BUTTON!
    TYPE [X] 'text' - type the specified text into INPUT element with id X.
    TYPESUBMIT [X] 'text' - same as TYPE above, except this command presses ENTER to submit the form
    STOP 'answer' - stop the process and provide the final answer

LINK, INPUT, BUTTON elements are represented like this:

    [1] LINK 'link text' (href='https://example.com')
    [2] BUTTON 'button text'
    [3] INPUT 'placeholder or label text' (value='initial value')

Based on your given objective, issue whatever command you believe will get you closest to achieving your goal.

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


def generate_predict_prompt(extraction_result: ExtractionEvent) -> list[dict[str, str]]:

    # TODO: See https://arxiv.org/pdf/2306.13063.pdf#page=28.20 for evaluation prompt details

    prompt = predict_prompt_template.replace("$url", extraction_result.data.data.url)

    if extraction_result.data.data.title:
        prompt = prompt.replace("$title", extraction_result.data.data.title)
    else:
        # Remove the title placeholder if it is not available
        prompt = prompt.replace("CURRENT PAGE TITLE: $title\n", "")

    if extraction_result.data.data.content:
        prompt = prompt.replace("$browser_content", extraction_result.data.data.content)
    else:
        # Remove the content placeholder if it is not available
        prompt = prompt.replace(
            "CURRENT BROWSER CONTENT:\n```\n$browser_content\n```\n", ""
        )

    try:
        prompt = prompt.replace("$objective", extraction_result.query.getobjective())
    except AttributeError:
        raise RuntimeError("Query objective not found")

    return [{"role": "user", "content": "Lorem ipsum"}]
