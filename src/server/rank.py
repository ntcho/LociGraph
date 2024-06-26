from utils.logging import log, log_func


from re import sub
from enum import Enum
from pprint import pformat

import wn
from wn.morphy import Morphy
from lxml.html import HtmlElement, tostring
from lxml.etree import _ElementTree

from dtos import ActionElement, Element, ParsedWebpageData, RelationQuery
from parse import get_text_content

from utils.props import read_props_index
from utils.file import read_json


class Relevancy(float, Enum):
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    HIGHEST = 1.0


# regex namespace for lxml XPath
regexpNS = {"re": "http://exslt.org/regular-expressions"}

tag_relevance_level = {
    "aside": Relevancy.LOW,
    "nav": Relevancy.LOW,
    "header": Relevancy.MEDIUM,
    "footer": Relevancy.MEDIUM,
    "article": Relevancy.HIGHEST,
    "section": Relevancy.HIGHEST,
    "main": Relevancy.HIGH,
}


@log_func()
def rank(
    data: ParsedWebpageData, query: RelationQuery
) -> tuple[list[Element], list[ActionElement]]:
    """Rank and return relevant elements based on the given keywords.

    Args:
        data (ParsedWebpageData): The parsed webpage data.
        query (RelationQuery): The relation query to rank elements.

    Returns:
        list[Element], list[ActionElement]: The ranked elements and action elements.
    """

    keywords: list[tuple[str, Relevancy]] = get_top_keywords(query, data.title)

    elements = rank_elements(data, keywords)
    action_elements = rank_action_elements(data, keywords)

    return elements, action_elements


def get_top_keywords(
    query: RelationQuery, title: str | None, k: int = 25
) -> list[tuple[str, Relevancy]]:
    """Get the top K keywords from the given list of keywords.

    Args:
        keywords (list[str]): The list of keywords to get the top K keywords from.
        title (str): The title of the webpage.
        k (int): The number of top keywords to get.

    Returns:
        list[tuple[str, Relevancy]]: The top K keywords with relevance levels, sorted
        by relevance.
    """

    if k <= 0:
        raise ValueError("Invalid value for `k`.")

    results: list[tuple[str, Relevancy]] = []  # [(keyword, relevance), ...]
    
    entity_relevancy = Relevancy.HIGHEST
    
    if title is not None:
        if query.entity.lower() in title.lower():
            # lower relevancy since the webpage is already about the entity
            entity_relevancy = Relevancy.HIGH

    # add name of entity to keywords
    results.append((query.entity, entity_relevancy))

    # add all keywords + extended keywords from the attribute
    if query.attribute is not None:
        results.extend(expand_keywords([query.attribute]))

    # rank top K keywords by relevance level
    results = sorted(results, key=lambda item: item[1], reverse=True)

    # number of keywords with relevance level of Relevancy.HIGHEST
    k = sum(1 for _, r in results if r == Relevancy.HIGHEST)

    # get max(k, 25) keywords
    top_keywords = results[: max(k, 25)]

    return top_keywords


def get_xpath_queries(
    keywords: list[tuple[str, Relevancy]]
) -> list[tuple[str, list[str], Relevancy]]:
    """Get the XPath query for the given relation query.

    Args:
        keywords (list[tuple[str, Relevancy]]): The keywords to rank elements.

    Returns:
        list[tuple[str, list[str], Relevancy]]: List of XPath queries, keyword group, 
        and its relevancy.
    """

    log.info(f"Matching elements with {len(keywords)} keywords...")
    log.debug(f"XPath rank keywords: \n{pformat(keywords)}")

    keywords_by_relevance: list[tuple[list[str], Relevancy]] = [
        ([k for k, r in keywords if r == Relevancy.HIGHEST], Relevancy.HIGHEST),
        ([k for k, r in keywords if r == Relevancy.HIGH], Relevancy.HIGH),
        ([k for k, r in keywords if r == Relevancy.MEDIUM], Relevancy.MEDIUM),
        ([k for k, r in keywords if r == Relevancy.LOW], Relevancy.LOW),
    ]  # [([keyword, ...], relevance), ...]

    results: list[tuple[str, list[str], Relevancy]] = []  # [(query, relevance), ...]

    for keyword_group, relevance in keywords_by_relevance:
        keyword_group = list(set(keyword_group))
        xpath_query = get_keyword_xpath_query(keyword_group)
        if xpath_query is not None:
            results.append((xpath_query, keyword_group, relevance))

    return results


def get_keyword_xpath_query(keywords: list[str]) -> str | None:
    """Get the XPath query for the given keywords.

    Args:
        keywords (list[str]): The keywords to get the XPath query for.

    Returns:
        str: The XPath query that ranks elements with the given keywords.
    """

    if len(keywords) == 0:
        return None

    # rank elements with keywords
    xpath_query = " | ".join(
        # match whole words with case-insensitive regex with multiple spaces
        # e.g. "studied at" matches text with irregular spaces "Alex   studied  at Bard College"
        [f"//*[re:test(text(), '{sub(r" ", " +", keyword)}', 'i')]" for keyword in keywords]
    )

    return xpath_query


@log_func()
def rank_elements(
    data: ParsedWebpageData, keywords: list[tuple[str, Relevancy]]
) -> list[Element]:
    """Get all visible elements from the parsed webpage data, sorted by relevance.

    Args:
        data (ParsedWebpageData): The parsed webpage data.
        xpath_query (str): The XPath query to rank elements.

    Returns:
        list[Element]: The ranked elements from the webpage data.
    """

    # prepare XPath query to rank elements
    xpath_queries = get_xpath_queries(keywords)

    if data is None or data.contentHTML is None or data.contentTree is None:
        raise ValueError("Invalid webpage data.")

    tree: _ElementTree = data.contentTree
    html: HtmlElement = data.contentHTML

    results: list[Element] = []

    for xpath_query, keyword_group, content_relevancy in xpath_queries:
        log.info(f"Matching elements with XPath query (len={len(xpath_query)}, keywords={keyword_group})")

        try:
            # rank elements with the XPath query
            xpath_elements: list[HtmlElement] = html.xpath(xpath_query, namespaces=regexpNS)
        except Exception as e:
            log.exception(e)
            continue

        # create Element objects from the ranked elements
        ranked_elements: list[Element] = []
        
        # content must be at least the length of the longest keyword
        minimum_length = max(keyword_group, key=len)

        for element in xpath_elements:
            content = get_text_content(element)
            
            while len(content) < len(minimum_length):
                # get parent element if content is too short
                element = element.getparent()
                
                if element is None:
                    break
                
                content = get_text_content(element)

            result = Element(
                xpath=tree.getpath(element),
                html_element=element,
                content=content,
                relevance={
                    "content": float(content_relevancy),
                    "location": float(
                        calculate_location_relevance(tree.getpath(element))
                    ),
                },
            )
            ranked_elements.append(result)

            try:
                element.drop_tree()  # drop element from tree to prevent duplicates
            except Exception as e:
                log.trace(f"skipping drop_tree: {e}")

        log.info(f"Found {len(ranked_elements)} elements")
        log.debug(f"Ranked elements: \n```\n{pformat(ranked_elements)}\n```")

        results.extend(ranked_elements)

    return sorted(results)  # higher relevance comes first


@log_func()
def rank_action_elements(
    data: ParsedWebpageData, keywords: list[tuple[str, Relevancy]]
) -> list[ActionElement]:
    """Rank relevant action elements, sorted by relevance.

    Args:
        data (ParsedWebpageData): The parsed webpage data.
        xpath_query (str): The XPath query to rank elements.

    Returns:
        list[Element]: The ranked action elements, sorted by relevance.
    """

    if data is None or data.actions is None:
        raise ValueError("Invalid webpage data.")

    result: list[ActionElement] = []

    for action in data.actions:

        # check whether action is a search input
        if action.type == "INPUT" and "search" in action.getdetails().lower():
            # search input is always relevant
            action.relevance = {"content": Relevancy.HIGHEST}
            log.debug(f"Found search input: {repr(action)}")

        else:
            if action.modified_xpath is None:
                log.error(f"Invalid action element: {repr(action)}")
                continue
            
            # XPath of the action element in the modified tree
            # this is different from `action.xpath` which is the original XPath
            xpath = action.modified_xpath
            
            # check whether action contains any of the keywords
            for keyword, content_relevance in keywords:
                if action.content is not None and keyword in action.content.lower():
                    action.relevance = {
                        "content": content_relevance,
                        "location": calculate_location_relevance(xpath),
                    }
                    log.debug(f"Found action with keyword: {repr(action)}")
                    break

            if action.relevance is None:
                action.relevance = {
                    "content": Relevancy.LOW,
                    "location": calculate_location_relevance(xpath),
                }

        result.append(action)

    result = sorted(result)  # higher relevance comes first

    # add id to actions (1 for most relevant, 2 for second most relevant, etc.)
    for i, action in enumerate(result):
        action.id = i + 1

    return result


def calculate_location_relevance(xpath: str) -> float:
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


STOPWORD_PATH = "utils/stopwords.json"

en: wn.Wordnet | None = None
index: dict[str, list[str]] | None = None
stopwords: list[str] | None = None


def init_expansion():
    """Initialize Wordnet, Wikidata, stopword variables for `expand_keywords()`."""

    global en
    if en is None:
        # Download and cache the Open English Wordnet (OEWN) 2023
        wn.download("oewn:2023")

        # Wordnet object with added lemmatizer
        # See more: https://wn.readthedocs.io/en/latest/guides/lemmatization.html#querying-with-lemmatization
        en = wn.Wordnet("oewn:2023", lemmatizer=Morphy())

    global index
    if index is None:
        index = read_props_index()

    global stopwords
    if stopwords is None:
        stopwords = read_json(STOPWORD_PATH)


@log_func()
def expand_keywords(keywords: list[str]) -> list[tuple[str, Relevancy]]:
    """Find synonyms, related words, and aliases of the given keywords from
    Wikidata and Wordnet.

    Note:
        Wikidata aliases are generally more accurate, but Wordnet is added to
        capture all possible synonyms and related words.

    Args:
        keywords (list[str]): The keywords to expand.

    Returns:
        list[tuple[str, Relevancy]]: The expanded keywords with relevancy levels.
    """

    init_expansion()  # initialize Wordnet, Wikidata, stopword variables

    if en is None or index is None or stopwords is None:
        raise RuntimeError("Failed to initialize expansion variables.")

    all_keywords = []
    result_keywords: list[str] = []  # set to check for duplicates
    results: list[tuple[str, Relevancy]] = []  # [(keyword, relevance), ...]

    for keyword in keywords:

        # add all Wikidata property aliases
        try:
            log.info(f"found alias {pformat(index[keyword])}")
            
            for k in index[keyword]:
                for word in k.split():
                    if word not in stopwords:
                        results.append((word, Relevancy.HIGHEST))
                        log.debug(f"  alias: added '{word}'")

        except KeyError:
            pass  # no aliases found

        # add keyword itself to search for synonyms
        all_keywords.append(keyword)

        # add all parts of the keyword without stopwords
        # e.g. "studied at" -> ["studied at", "studied"] ("at" is a stopword)
        for word in keyword.split():
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
                    if form not in result_keywords:
                        result_keywords.append(form)
                        results.append((form, Relevancy.HIGH))

            log.debug(f"  synset: added {synset.lemmas()}")

            # add all words from related synsets of current synset
            for related_synset in synset.get_related():
                for word in related_synset.words():
                    for form in word.forms():
                        if form not in result_keywords:
                            result_keywords.append(form)
                            results.append((form, Relevancy.LOW))

                log.trace(f"    related: added {related_synset.lemmas()}")

    # remove stopwords from expanded keywords
    results = [(k, r) for k, r in results if k not in stopwords]

    # log.debug(f"expanded keywords: \n{pformat(results, sort_dicts=False)}")

    return results
