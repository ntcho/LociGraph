import utils.logging as _log

_log.configure(format=_log.FORMAT)
log = _log.getLogger(__name__)
log.setLevel(_log.LEVEL)


import re
from pprint import pformat
from enum import Enum

import wn
from wn.morphy import Morphy
from lxml.html import HtmlElement, tostring
from lxml.etree import _ElementTree

from dtos import Element, ParsedWebpageData, RelationQuery, WebpageData
from utils.json import read_json


class Relevancy(float, Enum):
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    HIGHEST = 1.0


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

tag_relevance_level = {
    "aside": Relevancy.LOW,
    "nav": Relevancy.LOW,
    "header": Relevancy.MEDIUM,
    "footer": Relevancy.MEDIUM,
    "article": Relevancy.HIGHEST,
    "section": Relevancy.HIGHEST,
    "main": Relevancy.HIGH,
}

# Download and cache the Open English Wordnet (OEWN) 2023
wn.download("oewn:2023")

# Wordnet object with added lemmatizer
# See more: https://wn.readthedocs.io/en/latest/guides/lemmatization.html#querying-with-lemmatization
en = wn.Wordnet("oewn:2023", lemmatizer=Morphy())

index = read_json("utils/props-index.json")  # from `utils/wikidata-props.py`
stopwords = read_json("utils/stopwords.json")


def filter(data: ParsedWebpageData, query: RelationQuery) -> list[Element]:
    """Filter and return relevant elements based on the given keywords.

    Args:
        data (ParsedWebpageData): The parsed webpage data.
        query (RelationQuery): The relation query to filter elements.

    Returns:
        list[HtmlElement]: Relevant HTML elements filtered with the query.
    """

    # prepare XPath query to filter elements
    xpath_queries = get_xpath_queries(query)

    # filter elements with the XPath query
    filtered_elements = get_elements(data, xpath_queries)

    return filtered_elements


def get_xpath_queries(query: RelationQuery) -> list[tuple[str, Relevancy]]:
    """Get the XPath query for the given relation query.

    Args:
        query (RelationQuery): The relation query to get the XPath query for.

    Returns:
        str: The XPath query that filters top K elements related to the given query.
    """

    xpath_keywords: list[tuple[str, Relevancy]] = []  # [(keyword, relevance), ...]

    # add name of entity to keywords
    xpath_keywords.append((query.entity, Relevancy.HIGH))

    # add all keywords + extended keywords from the attribute
    if query.attribute is not None:
        xpath_keywords.extend(expand_keywords([query.attribute]))

    # filter top K keywords by relevance level
    xpath_keywords = sorted(xpath_keywords, key=lambda item: item[1], reverse=True)

    # number of keywords with relevance level of Relevancy.HIGHEST
    k = sum(1 for _, r in xpath_keywords if r == Relevancy.HIGHEST)

    # get max(k, 25) keywords
    top_keywords = xpath_keywords[: max(k, 25)]

    log.info(f"Filtering elements with {len(top_keywords)} keywords...")
    log.debug(f"XPath filter keywords: \n{pformat(top_keywords)}")

    top_keywords_by_relevance: list[tuple[list[str], Relevancy]] = [
        ([k for k, r in top_keywords if r == Relevancy.HIGHEST], Relevancy.HIGHEST),
        ([k for k, r in top_keywords if r == Relevancy.HIGH], Relevancy.HIGH),
        ([k for k, r in top_keywords if r == Relevancy.MEDIUM], Relevancy.MEDIUM),
        ([k for k, r in top_keywords if r == Relevancy.LOW], Relevancy.LOW),
    ]  # [([keyword, ...], relevance), ...]

    results: list[tuple[str, Relevancy]] = []  # [(query, relevance), ...]

    for keywords, relevance in top_keywords_by_relevance:
        xpath_query = get_xpath_query_from_keywords(keywords)
        if xpath_query is not None:
            results.append((xpath_query, relevance))

    return results


def get_xpath_query_from_keywords(keywords: list[str]) -> str | None:
    """Get the XPath query for the given keywords.

    Args:
        keywords (list[str]): The keywords to get the XPath query for.

    Returns:
        str: The XPath query that filters elements with the given keywords.
    """

    if len(keywords) == 0:
        return None

    # filter elements with keywords that are not hidden
    xpath_query = " | ".join(
        [
            f"//body//*[re:test(text(), '\\b{keyword}\\b', 'i') \
and not(contains(@style, 'display: none')) \
and not(contains(@class, 'hidden')) \
and not(contains(@class, 'none')) \
and not(contains(@style, 'visibility: hidden')) \
and not(contains(@style, 'visibility: hidden'))]"
            for keyword in keywords
        ]
    )

    return xpath_query


def get_elements(
    data: ParsedWebpageData, xpath_queries: list[tuple[str, Relevancy]]
) -> list[Element]:
    """Get all visible elements from the parsed webpage data.

    Args:
        data (ParsedWebpageData): The parsed webpage data.
        xpath_query (str): The XPath query to filter elements.

    Returns:
        list[Element]: The filtered elements from the webpage data.
    """

    if data is None or data.contentHTML is None or data.contentTree is None:
        raise ValueError("Invalid webpage data.")

    tree: _ElementTree = data.contentTree
    html: HtmlElement = data.contentHTML

    results: list[Element] = []

    for xpath_query, relevancy in xpath_queries:
        log.debug(f"Filtering elements with XPath query [{len(xpath_query)}]")

        # filter elements with the XPath query
        xpath_eval: list[HtmlElement] = html.xpath(xpath_query, namespaces=regexpNS)

        # remove elements with blacklisted tags
        xpath_eval = [e for e in xpath_eval if e.tag not in tag_blacklist]

        # create Element objects from the filtered elements
        filtered_elements = list(
            map(
                lambda element: Element(
                    xpath=tree.getpath(element),
                    html_element=element,
                    content=re.sub(r"\s+", " ", element.text_content()).strip(),
                    relevance={
                        "content": float(relevancy),
                        "location": float(
                            get_relevance_from_xpath(tree.getpath(element))
                        ),
                    },
                ),
                xpath_eval,
            )
        )

        log.info(f"Found {len(filtered_elements)} elements")
        log.debug(f"Filtered elements: \n```\n{pformat(filtered_elements)}\n```")

        results.extend(filtered_elements)

    return sorted(results, reverse=True)


def get_relevance_from_xpath(xpath: str) -> Relevancy:
    """Get the relevance level of the element with the given XPath.

    Args:
        xpath (str): The XPath of the element to get the relevance level for.

    Returns:
        Relevancy: The relevance level of the element.
    """

    for tag, relevance in tag_relevance_level.items():
        if tag in xpath:
            return relevance

    # element not in a main content relevance level
    return Relevancy.MEDIUM


def expand_keywords(keywords: list[str]) -> list[tuple[str, Relevancy]]:
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
        list[tuple[str, Relevancy]]: The expanded keywords with relevancy levels.
    """

    all_keywords = []
    results: list[tuple[str, Relevancy]] = []  # [(keyword, relevance), ...]

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
                    results.append((form, Relevancy.HIGH))

            log.info(f"  synset: added {synset.lemmas()}")

            # add all words from related synsets of current synset
            for related_synset in synset.get_related():
                for word in related_synset.words():
                    for form in word.forms():
                        results.append((form, Relevancy.LOW))

                log.info(f"    related: added {related_synset.lemmas()}")

        # add all WikiData property aliases
        try:
            for k in index[keyword]:
                results.append((k, Relevancy.HIGHEST))

            log.info(f"  alias: added {index[keyword]}")
        except KeyError:
            pass  # no aliases found

    # remove stopwords from expanded keywords
    results = [(k, r) for k, r in results if k not in stopwords]

    log.debug(f"expanded keywords: \n{pformat(results, sort_dicts=False)}")

    return results
