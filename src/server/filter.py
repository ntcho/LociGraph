import logging
from utils.logging import FORMAT

logging.basicConfig(format=FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # TODO: Change to INFO on production


from pprint import pformat

import wn
from wn.morphy import Morphy
from lxml.html import HtmlElement, tostring

from dtos import Relation, WebpageData

# regex namespace for lxml XPath
regexpNS = {"re": "http://exslt.org/regular-expressions"}

tag_blacklist = set(
    [
        "html",
        "head",
        "title",
        "meta",
        "iframe",
        "body",
        "script",
        "style",
        "path",
        "svg",
        "br",
    ]
)

from parse import parse
from utils.json import read_json

# Download and cache the Open English Wordnet (OEWN) 2023
wn.download("oewn:2023")

# Wordnet object with added lemmatizer
# See more: https://wn.readthedocs.io/en/latest/guides/lemmatization.html#querying-with-lemmatization
en = wn.Wordnet("oewn:2023", lemmatizer=Morphy())

index = read_json("utils/props-index.json")  # from `utils/wikidata-props.py`
stopwords = read_json("utils/stopwords.json")


def filter(html: HtmlElement, target: Relation) -> list[HtmlElement]:
    """Filter and return relevant elements based on the given keywords.

    Args:
        html (HtmlElement): The HTML element to filter.
        keywords (list[str]): The keywords to filter with.

    Returns:
        list[HtmlElement]: The filtered elements.
    """

    xpath_keywords = []

    # add name of entity to keywords
    xpath_keywords.append(target.entity)

    if target.attribute is not None:
        # add all keywords + extended keywords from the attribute
        xpath_keywords.extend(
            # only use keywords that are not phrases
            [k for k in expand_keywords(list(target.attribute)) if " " not in k]
        )

    logger.info(f"Filtering elements with {len(xpath_keywords)} keywords...")
    logger.debug(f"XPath keywords: \n{pformat(xpath_keywords)}")

    xpath_query = " | ".join(
        [
            f"//body//*[re:test(text(), '\\b{keyword}\\b', 'i') \
and not(contains(@style, 'display: none')) \
and not(contains(@class, 'hidden')) \
and not(contains(@class, 'none')) \
and not(contains(@style, 'visibility: hidden')) \
and not(contains(@style, 'visibility: hidden')) \
and not(contains(@aria-hidden, 'true'))]"
            for keyword in xpath_keywords
        ]
    )

    # logger.debug(f"XPath query: \n```\n{xpath_query}\n```")
    filtered_elements = html.xpath(f"{xpath_query}", namespaces=regexpNS)

    # remove elements with blacklisted tags
    filtered_elements = [e for e in filtered_elements if e.tag not in tag_blacklist]

    logger.info(f"Found {len(filtered_elements)} elements")
    logger.debug(
        f"Filtered elements: \n```\n{pformat([e.tag for e in filtered_elements])}\n```"
    )

    return filtered_elements  # TODO: add confidence level for each element


def expand_keywords(keywords: list[str]) -> list[str]:
    """Find synonyms, related words, and aliases of the given keywords from
    WikiData and Wordnet.

    Note:
        WikiData aliases are generally more accurate, but Wordnet is added to
        capture all possible synonyms and related words.

    Future:
        Could also use `wn.similarity` to filter based on semantic similarity.
        See more: https://wn.readthedocs.io/en/latest/api/wn.similarity.html

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

    # remove stopwords from expanded keywords
    expanded_keywords = [k for k in expanded_keywords if k not in stopwords]
    logger.debug(f"expanded keywords: \n{pformat(expanded_keywords)}")

    return expanded_keywords  # TODO: add confidence level for each keyword


# TODO: remove on production
# from utils.dev import read_file_to_base64

# r = parse(
#     WebpageData(
#         url="https://example.com",
#         htmlBase64=read_file_to_base64("data/wiki.html"),
#         imageBase64="",
#         language="en",
#     )
# )

# e = filter(r.contentHTML, ["graduated from"])
