from dtos import ExtractionEvent, Action, EvaluationEvent

# import openai


def evaluate() -> EvaluationEvent:

    # prompt = f"Extraction Event: {extraction_event}\nActions: {actions}\n\n"
    # response = openai.Completion.create(
    #     engine="gpt-3.5-turbo",
    #     prompt=prompt,
    #     max_tokens=100,
    #     temperature=0.7,
    #     n=1,
    #     stop=None,
    # )
    # evaluation = response.choices[0].text.strip()
    # next_actions = [
    #     "Action 1",
    #     "Action 2",
    #     "Action 3",
    # ]  # Replace with your logic to generate next actions

    return EvaluationEvent(evaluation=evaluation, next_actions=next_actions)
