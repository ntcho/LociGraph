import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


from pprint import pformat

import wn
from wn.morphy import Morphy
from lxml.html import HtmlElement, tostring

from dtos import RelationQuery, WebpageData

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


def filter(html: HtmlElement, query: RelationQuery) -> list[HtmlElement]:
    """Filter and return relevant elements based on the given keywords.

    Args:
        html (HtmlElement): The HTML element to filter.
        keywords (list[str]): The keywords to filter with.

    Returns:
        list[HtmlElement]: The filtered elements.
    """

    xpath_keywords: dict[str, float] = {}  # { keyword: confidence }

    # add name of entity to keywords
    xpath_keywords[query.entity] = 1.0

    # add all keywords + extended keywords from the attribute
    if query.attribute is not None:
        expanded_keywords = expand_keywords([query.attribute])

        # add words of the keyword phrase without stopwords
        # e.g. "attended school at" -> ["attended", "school"] ("at" is a stopword)
        for keyword in expanded_keywords:
            for word in keyword.split(" "):
                if word not in stopwords:
                    # add keyword with confidence level
                    xpath_keywords[word] = expanded_keywords[keyword]

    # filter top K keywords by confidence level
    xpath_keywords = dict(
        sorted(xpath_keywords.items(), key=lambda item: item[1], reverse=True)
    )

    # number of keywords with confidence level of 1.0
    k = sum(1 for v in xpath_keywords.values() if v == 1.0)

    # get max(k, 25) keywords
    top_keywords = list(xpath_keywords.keys())[: max(k, 25)]

    log.info(f"Filtering elements with {len(top_keywords)} keywords...")
    log.debug(f"XPath filter keywords: \n{pformat(top_keywords)}")

    # filter elements with keywords that are not hidden
    xpath_query = " | ".join(
        [
            f"//body//*[re:test(text(), '\\b{keyword}\\b', 'i') \
and not(contains(@style, 'display: none')) \
and not(contains(@class, 'hidden')) \
and not(contains(@class, 'none')) \
and not(contains(@style, 'visibility: hidden')) \
and not(contains(@style, 'visibility: hidden'))]"
            for keyword in top_keywords
        ]
    )

    # log.debug(f"XPath query: \n```\n{xpath_query}\n```")
    filtered_elements = html.xpath(f"{xpath_query}", namespaces=regexpNS)

    # remove elements with blacklisted tags
    filtered_elements = [e for e in filtered_elements if e.tag not in tag_blacklist]

    log.info(f"Found {len(filtered_elements)} elements")
    log.debug(
        f"Filtered elements: \n```\n{pformat([e.tag for e in filtered_elements])}\n```"
    )

    return filtered_elements  # TODO: add confidence level for each element


def expand_keywords(keywords: list[str]) -> dict[str, float]:
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
        dict[str, float]: The expanded keywords with confidence levels.
    """

    all_keywords = []
    expanded_keywords: dict[str, float] = {}  # { keyword: confidence }

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

        log.info(f"expanding `{keyword}`")

        # add all Wordnet synsets
        for synset in en.synsets(keyword):

            # iterate through all words linked in the synset (similar to synonyms)
            # e.g. "study" -> ["major", "minor"]
            for word in synset.words():

                # add all forms of the word
                # e.g. "studied" -> ["study"]
                for form in word.forms():
                    expanded_keywords[form] = 0.9

            log.info(f"  synset: added {synset.lemmas()}")

            # add all words from related synsets of current synset
            for related_synset in synset.get_related():
                for word in related_synset.words():
                    for form in word.forms():
                        expanded_keywords[form] = 0.1

                log.info(f"    related: added {related_synset.lemmas()}")

        # add all WikiData property aliases
        try:
            for k in index[keyword]:
                expanded_keywords[k] = 1.0
            log.info(f"  alias: added {index[keyword]}")
        except KeyError:
            pass  # no aliases found

    # remove stopwords from expanded keywords
    for stopword in stopwords:
        try:
            del expanded_keywords[stopword]
        except KeyError:
            pass

    log.debug(f"expanded keywords: \n{pformat(expanded_keywords, sort_dicts=False)}")

    return expanded_keywords


# TODO: remove on production
from utils.dev import read_file_to_base64

r = parse(
    WebpageData(
        url="https://example.com",
        htmlBase64=read_file_to_base64("data/linkedin.html"),
        imageBase64="",
        language="en",
    )
)

e = filter(r.contentHTML, RelationQuery("Anna", "studied at"))
