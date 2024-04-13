from utils.logging import log, log_func, CONFIG

log.configure(**CONFIG)


import re

from dtos import Action, ActionElement, Element, Relation, RelationQuery


EXTRACT_ELEMENT_LIMIT = 25  # maximum number of elements to extract relations from
EVALUATE_RELATION_LIMIT = 25  # maximum number of relations to evaluate
ACT_ELEMENT_LIMIT = 10  # maximum number of actions to choose from


# Prompt to extract relation JSON from text
extract_system_prompt = """
You are tasked to extract all relation triplets from a webpage. The output must be in the format of [entity, attribute, value]. If no relations are found, write `No relations found`.

The following are some examples:

Title: `About Alex | alex.com`
Content:
```
Born
Jaunary 1, 2000
New York City, NY, US
```
Query: [Alex, date of birth, ?]
Reasoning: Let's think step by step. We need to find the date of birth of Alex. The content provides the birthday January 1st, 2000. Since the content provides the date of birth, we should extract the relation [Alex, date of birth, January 1st, 2000]. Additionally, the content provides the birthplace New York City. Since this is related to Alex, we should extract the relation [Alex, place of birth, New York City] as an additional relation.
Output:
Query relations:
- [Alex, date of birth, January 1, 2000]
Additional relations:
- [Alex, place of birth, New York City]

Title: `Alex | LinkedIn`
Content:
```
Education

Bard College
Computer Science

Timbuktu High School
Mathematics
```
Query: [Alex, educated at, ?]
Reasoning: Let's think step by step. We need to find the institution where Alex was educated at. The content provides that Alex studied Computer Science at Bard College. Since this is related to Alex, we should extract the relation [Alex, educated at, Bard College] and [Bard College, academic major, Computer Science]. Additionally, the content provides that Bard College offers Computer Science. Since this is a valid relation, we should extract the relation [Bard College, offers, Computer Science] as an additional relation. The content also provides that Alex studied Mathematics at Timbuktu High School. Since this is related to Alex, we should extract the relation [Alex, educated at, Timbuktu High School].
Output:
Query relations:
- [Alex, educated at, Bard College]
- [Alex, educated at, Timbuktu High School]
Additional relations:
- [Alex, academic major, Computer Science]
- [Bard College, offers, Computer Science]

Title: `Alex - Wikipedia`
Content:
```
Alex works at ACME Inc as a software engineer. Previously, Alex worked at XYZ Corp as a data scientist. Alex has a degree in Computer Science from Bard College.
```
Query: [Alex, ?, ?]
Reasoning: Let's think step by step. We need to find all relevant relations for Alex. The content provides that Alex works at ACME Inc as a software engineer. Since this is related to Alex, we should extract the relation [Alex, works at, ACME Inc] and [Alex, job title, software engineer]. The content also provides that Alex previously worked at XYZ Corp as a data scientist. Since this is related to Alex, we should extract the relation [Alex, worked at, XYZ Corp] and [Alex, job title, data scientist]. The content also provides that Alex has a degree in Computer Science from Bard College. Since this is related to Alex, we should extract the relation [Alex, majored in, Computer Science] and [Alex, graduated from, Bard College].
Output:
Query relations:
- [Alex, works at, ACME Inc]
- [Alex, job title, software engineer]
- [Alex, worked at, XYZ Corp]
- [Alex, job title, data scientist]
- [Alex, majored in, Computer Science]
- [Alex, graduated from, Bard College]

Title: `Fwd: RSVP for Alex's Birthday Party | Gmail`
Content:
```
Hi everyone,

Please RSVP for Alex's birthday party this Friday at 7:00 PM.

Thanks!
```
Query: [Alex, date of birth, ?]
Reasoning: Let's think step by step. We need to find the date of birth of Alex. The content provides that Alex's birthday party is this Friday at 7:00 PM. Since this is not the date of birth, we should write `No relations found`.
Output:
No relations found
"""

# FUTURE: use Auto-CoT
# Read more: https://www.promptingguide.ai/techniques/cot#automatic-chain-of-thought-auto-cot

extract_prompt_template = """
Page title: <title>
Content:
```
<content>
```
Query: <query>
Reasoning: Let's think step by step. """


def generate_extract_prompt(
    title: str | None, elements: list[Element], query: RelationQuery
) -> list[dict[str, str]]:
    """Generate a prompt to extract relation JSON from text.

    Args:
        elements (list[HtmlElement]): The list of HTML elements to extract relations from.
        target (RelationQuery): The query of relations to extract.
    """

    log.info(f"Generating prompt (title='{title}', len(elements)={len(elements)}, query={str(query)})")

    if len(elements) == 0:
        raise RuntimeError("No elements provided.")

    avg_relevancy = sum([e.getrelevancy() for e in elements]) / len(elements)

    content_elements = [
        e.content for e in elements if e.getrelevancy() >= avg_relevancy
    ]  # filter elements with above average relevancy

    content = "\n\n".join(
        content_elements[:EXTRACT_ELEMENT_LIMIT]
    )  # only prompt the top K relevant elements

    # build the prompt content
    prompt = extract_prompt_template
    prompt = (
        prompt.replace("<title>", title)
        if title is not None
        else prompt.replace("Page title: <title>\n", "")
    )
    prompt = prompt.replace("<content>", content)
    prompt = prompt.replace("<query>", str(query))

    message = [
        {
            "role": "user",
            "content": "\n\n".join([extract_system_prompt.strip(), prompt.strip()]),
        }
    ]

    log.debug(f"Generated message:\n```\n{message[0]["content"]}\n```")

    return message


def parse_extract_response(response: str) -> list[Relation]:
    """Parse the response from the extraction prompt.

    Args:
        response (str): The response from the extraction prompt.

    Returns:
        list[Relation]: The list of extracted relations.
    """

    log.info(f"Parsing response (len(response)={len(response)})")
    log.debug(f"Parsing response:\n```\n{response}\n```")

    relations: list[Relation] = []

    if "no relations found" in response.lower():
        log.info("Response contains 'No relations found'")
        return relations

    try:
        for line in response.split("\n"):
            if not line:
                continue

            # Extract the relation from the line
            match = re.match(r"- \[\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+)\s*\]", line)

            if match:
                relations.append(Relation(*match.groups()))
    except Exception as e:
        log.warning("Failed to parse the extraction response.")
        log.exception(e)

    return relations


# Prompt to evaluate relation JSON
evaluate_system_prompt = """
You are tasked to evaluate relation extraction results for the given query. If you believe the extraction results are correct, write `STOP`. If you believe the extraction results are incorrect, write `CONTINUE`.

The following are some examples:

Query: [Alex, date of birth, ?]
Extraction results:
- [Alex, born on, 2000]
- [Alex, birthday, January 1, 2000]
Reasoning: Let's think step by step. We need to find the date of birth of Alex. [Alex, born on, 2000] is incorrect because it only provides the year of birth. [Alex, birthday, January 1st, 2000] is correct because it provides the date of birth as January 1st, 2000. Since at least one extraction result is correct, we should `STOP`.
Answer: STOP
Correct relation:
- [Alex, date of birth, January 1, 2000]

Query: [Alex, educated at, ?]
Extraction results:
- [Alex, studied, Computer Science]
- [Alex, graduated in, 2020]
Reasoning: Let's think step by step. We need to find the institution where Alex was educated at. [Alex, studied, Computer Science] is incorrect because it only provides the academic major. [Alex, graduated in, 2020] is incorrect because it only provides the year of graduation. Since none of the extraction results are correct, we should `CONTINUE`.
Answer: CONTINUE

Query: [Alex, ?, ?]
Extraction results:
- [Alex, works at, ACME Inc]
- [ACME Inc, location, New York]
- [Alex, job title, software engineer]
Reasoning: Let's think step by step. We need to find all relevant relations for Alex. [Alex, works at, ACME Inc] is correct because it provides the company where Alex works. [ACME Inc, location, New York] is incorrect because it provides the location of the company. [Alex, job title, software engineer] is correct because it provides the job title of Alex. Since at least one extraction result is correct, we should `STOP`.
Answer: STOP
Correct relations:
- [Alex, works at, ACME Inc]
- [Alex, job title, software engineer]
"""

evaluate_prompt_template = """
Query: <query>
Extraction results:
<relations>
Reasoning: Let's think step by step. """


def generate_evaluate_prompt(
    query: RelationQuery, results: list[Relation]
) -> list[dict[str, str]]:
    """Generate a prompt to evaluate relation extraction results.

    Args:
        query (RelationQuery): The query of relations to evaluate.
        results (list[Relation]): The list of extracted relations to evaluate.
    """

    log.info(f"Generating prompt (query={str(query)}, len(results)={len(results)})")
    
    relations = "\n".join(
        [f"- {str(r)}" for r in results[:EVALUATE_RELATION_LIMIT]]
    )  # limit the number of relations to evaluate

    prompt = evaluate_prompt_template
    prompt = prompt.replace("<query>", str(query))
    prompt = prompt.replace("<relations>", relations)

    message = [
        {
            "role": "user",
            "content": "\n\n".join([evaluate_system_prompt.strip(), prompt.strip()]),
        }
    ]

    log.debug(f"Generated message:\n```\n{message[0]["content"]}\n```")

    return message


def parse_evaluate_response(response: str) -> tuple[bool, list[Relation]]:
    """Parse the response from the evaluation prompt.

    Args:
        response (str): The response from the evaluation prompt.

    Returns:
        tuple[bool, list[Relation]]: A tuple containing a boolean indicating if the extraction results are correct and the list of extracted relations.
    """

    log.info(f"Parsing response (len(response)={len(response)})")
    log.debug(f"Parsing response:\n```\n{response}\n```")

    answer_stop = "answer: stop" in response.lower()
    answer_continue = "answer: continue" in response.lower()

    # check if the response contains either `STOP` or `CONTINUE`
    if answer_stop is not answer_continue:
        log.error("The response didn't contain either `STOP` or `CONTINUE`.")
        raise RuntimeError("The response must contain either `STOP` or `CONTINUE`.")

    relations = []

    try:
        for line in response.split("\n"):
            if not line:
                continue

            # Extract the relation from the line
            match = re.match(r"- \[\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+)\s*\]", line)

            if match:
                relations.append(Relation(*match.groups()))
    except Exception as e:
        log.warning("Failed to parse the evaluation response.")
        log.exception(e)
    
    return answer_stop, relations


# TODO: add more few-shot examples for action prediction

# Prompt to predict next action
# Inspired by https://github.com/nat/natbot
act_system_prompt = """
You are tasked to predict the next action to achieve the given objective. Imagine you are imitating humans using a web browser to achieve an objective, step by step.

You can take these actions:

    CLICK [X] - click element with id X. You can only click on LINK and BUTTON!
    TYPE [X] 'text' - type the specified text into INPUT element with id X.
    TYPESUBMIT [X] 'text' - same as TYPE above, except this command presses ENTER to submit the form

LINK, INPUT, BUTTON elements are represented like this:

    [1] LINK 'link text' (href='https://example.com')
    [2] BUTTON 'button text'
    [3] INPUT 'placeholder or label text' (value='initial value')

Based on your given objective, issue whatever command you believe will get you closest to achieving your goal.

The following are some examples:

Page URL: https://gmail.com
Page title: `Inbox - Gmail`
Actions:
- [1] BUTTON 'Compose'
- [2] INPUT 'Search mail'
- [3] LINK 'Inbox' (href='/inbox')
- [4] LINK 'Sent' (href='/sent')
Objective: Find the value of attribute `date of birth` of entity `Alex`.
Reasoning: Let's think step by step. We need to find the date of birth of Alex. Since the current page is Gmail inbox, we should start by searching for the date of birth of Alex. We can search with the query `date of birth Alex` by typing it in the search mail input. Therefore, I will issue the command `TYPE [2] 'date of birth Alex'`.
Command: TYPE [2] 'date of birth Alex'

Page URL: https://wikipedia.org/en/Alex
Page title: `Alex - Wikipedia`
Actions:
- [1] LINK 'Bard College - Alex' (href='https://bard.edu/people/alex')
- [2] LINK 'Alex | LinkedIn' (href='https://linkedin.com/in/alex')
- [3] LINK 'ACME Inc - Alex' (href='https://acme.com/people/alex')
Objective: Find the value of attribute `graduated in` of entity `Alex`.
Reasoning: Let's think step by step. We need to find the year Alex graduated. Since the current page is Alex's Wikipedia page, we should click on the LinkedIn link to find the educational background of Alex. Therefore, I will issue the command `CLICK [2]`.
Command: CLICK [2]
"""

act_prompt_template = """
Page URL: <url>
Page title: <title>
Actions:
<actions>
Objective: <objective>
Reasoning: Let's think step by step. """  # TODO: add previous actions and reasoning

# FUTURE: Use top-K prompting strategy to generate multiple answers and evaluate the best one
# See more: https://arxiv.org/pdf/2306.13063.pdf#page=28.20


def generate_act_prompt(
    url: str, title: str | None, actions: list[ActionElement], query: RelationQuery
) -> list[dict[str, str]]:
    """Generate a prompt to predict the next action to achieve the given objective.

    Args:
        extraction_result (ExtractionEvent): The extraction result to generate the prompt from.
    """

    log.info(f"Generating prompt (url='{url}', title='{title}', len(actions)={len(actions)}, query={str(query)})")

    if len(actions) == 0:
        raise RuntimeError("No action elements provided.")

    avg_relevancy = sum([e.getrelevancy() for e in actions]) / len(actions)

    action_elements = [
        e for e in actions if e.getrelevancy() >= avg_relevancy
    ]  # filter action elements with above average relevancy

    action_list = "\n".join(
        [f"- {str(a)}" for a in action_elements[:ACT_ELEMENT_LIMIT]]
    )  # only prompt the top K relevant actions

    prompt = act_prompt_template
    prompt = prompt.replace("<url>", url)
    prompt = (
        prompt.replace("<title>", title)
        if title is not None
        else prompt.replace("Page title: <title>\n", "")
    )
    prompt = prompt.replace(
        "<actions>",
        action_list,
    )
    prompt = prompt.replace("<objective>", query.getobjective())

    message = [
        {
            "role": "user",
            "content": "\n\n".join([act_system_prompt.strip(), prompt.strip()]),
        }
    ]

    log.debug(f"Generated message:\n```\n{message[0]["content"]}\n```")

    return message


def parse_act_response(response: str, actions: list[ActionElement]) -> Action:
    """Parse the response from the action prediction prompt.

    Args:
        response (str): The response from the action prediction prompt.
        actions (list[ActionElement]): The list of available actions to predict from.

    Returns:
        Action: The next action predicted by the LLM.
    """

    log.info(f"Parsing response (len(response)={len(response)})")
    log.debug(f"Parsing response:\n```\n{response}\n```")

    match = re.fullmatch(r"(CLICK|TYPE|TYPESUBMIT) \[(\d+)\](?: '(.+)')?", response)

    if not match:
        log.error("The response didn't match the expected format.")
        raise RuntimeError(
            "The response must be in the format 'CLICK [X]', 'TYPE [X] text', or 'TYPESUBMIT [X] text'."
        )

    try:
        action_type, id, text = match.groups()
        
        # Find the action element with the given id found in the response
        action_element = list(filter(lambda e: e.id == int(id), actions))
    except Exception as e:
        log.error("Failed to parse the action response.")
        log.exception(e)
        raise RuntimeError("Failed to parse the action response.")

    if len(action_element) == 0:
        raise RuntimeError(f"Action element with id {id} not found.")

    if len(action_element) > 1:
        raise RuntimeError(f"Multiple action elements with id {id} found.")
    
    return Action(type=action_type, element=action_element[0], value=text)  # type: ignore
