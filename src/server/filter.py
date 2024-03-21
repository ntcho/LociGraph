import logging
from utils.logging import FORMAT

logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


import wn
from wn.morphy import Morphy
from utils.json import read_json

# Download and cache the Open English Wordnet (OEWN) 2023
wn.download("oewn:2023")

# Wordnet object with added lemmatizer
# See more: https://wn.readthedocs.io/en/latest/guides/lemmatization.html#querying-with-lemmatization
en = wn.Wordnet("oewn:2023", lemmatizer=Morphy())

index = read_json("utils/props-index.json")  # from `utils/wikidata-props.py`
stopwords = read_json("utils/stopwords.json")


def filter(paragraphs: list[str], keywords: list[str]) -> list[str]:
    """Filter and return relevant paragraphs based on the given keywords.

    Args:
        paragraphs (list[str]): The paragraphs to filter.
        keywords (list[str]): The keywords to filter with.

    Returns:
        list[str]: The filtered paragraphs.
    """

    filtered_paragraphs = []

    # expand keywords to include synonyms, related words, and aliases
    # could also use `wn.similarity` to filter based on semantic similarity
    # See more: https://wn.readthedocs.io/en/latest/api/wn.similarity.html
    expanded_keywords = expand_keywords(keywords)

    for paragraph in paragraphs:
        for keyword in expanded_keywords:
            if keyword in paragraph:
                filtered_paragraphs.append(paragraph)
                break

    return filtered_paragraphs


def expand_keywords(keywords: list[str]) -> set[str]:
    """Find synonyms, related words, and aliases of the given keywords from
    WikiData and Wordnet.

    Note:
        WikiData aliases are generally more accurate, but Wordnet is added to
        capture all possible synonyms and related words.

    Args:
        keywords (list[str]): The keywords to expand.

    Returns:
        set[str]: The expanded keywords.
    """

    all_keywords = []
    expanded_keywords = set()

    # add all parts of the keyword without stopwords
    # e.g. "studied at" -> ["studied at", "studied"] ("at" is a stopword)
    for keyword in keywords:

        # add keyword itself
        all_keywords.append(keyword)

        # add parts of the keyword
        for word in keyword.split(" "):
            if word not in stopwords:
                all_keywords.append(word)

    # iterate through all keywords and parts of keywords
    for keyword in all_keywords:

        logger.info(f"expanding `{keyword}`")

        # add all WikiData property aliases
        try:
            expanded_keywords.update(index[keyword])
            logger.info(f"  alias: added {index[keyword]}")
        except KeyError:
            pass  # no aliases found

        # iterate through all Wordnet synsets
        for synset in en.synsets(keyword):

            # iterate through all words linked in the synset (similar to synonyms)
            # e.g. "study" -> ["major", "minor"]
            for word in synset.words():

                # add all forms of the word
                # e.g. "studied" -> ["study"]
                for form in word.forms():
                    expanded_keywords.add(form)

            logger.info(f"  synset: added {synset.lemmas()}")

            # add all words from related synsets of current synset
            for related_synset in synset.get_related():
                for word in related_synset.words():
                    for form in word.forms():
                        expanded_keywords.add(form)

                logger.info(f"    related: added {related_synset.lemmas()}")

    logger.debug(f"expanded keywords: {expanded_keywords}")

    return expanded_keywords
