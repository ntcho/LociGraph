import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from dataclasses import dataclass
from pprint import pformat

from transformers import pipeline

from dtos import Relation

triplet_extractor = pipeline(
    "translation_xx_to_yy",
    model="Babelscape/mrebel-large",
    tokenizer="Babelscape/mrebel-large",
)
log.info("Initialized triplet extractor pipeline")


@dataclass
class Triplet:
    """Triplet dataclass to store the extracted triplets. Adds compatibility
    between mREBEL outputs and Relation dataclass."""

    head: str
    head_type: str
    type: str
    tail: str
    tail_type: str


def extract(text: str) -> list[Relation]:
    """Extract triplets from the given text.

    Args:
        text (str): The text to extract triplets from.

    Returns:
        list[Relation]: The extracted relations from the text.

    Raises:
        Exception: If the triplet extractor or tokenizer is not initialized.
    """
    if triplet_extractor is None or triplet_extractor.tokenizer is None:
        raise Exception("Triplet extractor not initialized")

    log.info(f"Extracting triplets from text: \n```\n{text}\n```")

    # Translate text into string with triplet tokens
    extracted_text = triplet_extractor.tokenizer.batch_decode(
        [
            triplet_extractor(
                text,
                decoder_start_token_id=250058,  # `tp_XX` token
                src_lang="en_XX",  # change en_XX for the language of the source
                tgt_lang="<triplet>",
                return_tensors=True,
                return_text=False,
            )[0]["translation_token_ids"]
        ]
    )

    log.debug(
        f"Extracted text with triplet tokens: \n```\n{pformat(extracted_text)}\n```"
    )

    # Extract triplets from the translated text
    triplets = extract_triplets(extracted_text[0])

    log.info(f"Extracted {len(triplets)} triplets from text")
    log.debug(f"Extracted triplets: \n```\n{pformat(triplets)}\n```")

    return [
        Relation(
            entity=t.head,
            attribute=t.type,
            value=t.tail,
        )  # convert Triplet into Relation
        for t in triplets
    ]


def extract_triplets(extracted_text: str) -> list[Triplet]:
    """Extract triplets from string with triplet tokens.

    Note:
        TODO: add `extracted_text` format and example

    Args:
        text (str): The translated text with triplet tokens.

    Returns:
        list[Triplet]: The extracted triplets from the text."""

    triplets = []
    relation = ""
    extracted_text = extracted_text.strip()
    current = "x"
    subject, relation, object_, object_type, subject_type = "", "", "", "", ""

    for token in (
        # Remove special tokens
        extracted_text.replace("<s>", "")
        .replace("<pad>", "")
        .replace("</s>", "")
        .replace("tp_XX", "")
        .replace("__en__", "")
        .split()
    ):
        if token == "<triplet>" or token == "<relation>":
            current = "t"
            if relation != "":
                triplets.append(
                    Triplet(
                        head=subject.strip(),
                        head_type=subject_type,
                        type=relation.strip(),
                        tail=object_.strip(),
                        tail_type=object_type,
                    )
                )
                relation = ""
            subject = ""
        elif token.startswith("<") and token.endswith(">"):
            if current == "t" or current == "o":
                current = "s"
                if relation != "":
                    triplets.append(
                        Triplet(
                            head=subject.strip(),
                            head_type=subject_type,
                            type=relation.strip(),
                            tail=object_.strip(),
                            tail_type=object_type,
                        )
                    )
                object_ = ""
                subject_type = token[1:-1]
            else:
                current = "o"
                object_type = token[1:-1]
                relation = ""
        else:
            if current == "t":
                subject += " " + token
            elif current == "s":
                object_ += " " + token
            elif current == "o":
                relation += " " + token

    if (
        subject != ""
        and relation != ""
        and object_ != ""
        and object_type != ""
        and subject_type != ""
    ):
        triplets.append(
            Triplet(
                head=subject.strip(),
                head_type=subject_type,
                type=relation.strip(),
                tail=object_.strip(),
                tail_type=object_type,
            )
        )

    return triplets
