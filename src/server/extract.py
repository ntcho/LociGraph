from transformers import pipeline
from dataclasses import dataclass

from dtos import Relation

triplet_extractor = pipeline(
    "translation_xx_to_yy",
    model="Babelscape/mrebel-large",
    tokenizer="Babelscape/mrebel-large",
)
# We need to use the tokenizer manually since we need special tokens.


@dataclass
class Triplet:
    head: str
    head_type: str
    type: str
    tail: str
    tail_type: str


# Function to parse the generated text and extract the triplets
def extract_triplets_typed(text) -> list[Triplet]:
    triplets = []
    relation = ""
    text = text.strip()
    current = "x"
    subject, relation, object_, object_type, subject_type = "", "", "", "", ""

    for token in (
        text.replace("<s>", "")
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


def extract(text: str):
    extracted_text = triplet_extractor.tokenizer.batch_decode(
        [
            triplet_extractor(
                text,
                decoder_start_token_id=250058,
                src_lang="en_XX",
                tgt_lang="<triplet>",
                return_tensors=True,
                return_text=False,
            )[0]["translation_token_ids"]
        ]
    )  # change en_XX for the language of the source.
    extracted_triplets = extract_triplets_typed(extracted_text[0])

    #! DEBUG
    print(extracted_triplets)

    return [
        Relation(
            entity=t.head,
            attribute=t.type,
            value=t.tail,
        )  # convert Triplet into Relation
        for t in extracted_triplets
    ]
