from utils.logging import log, log_func

import requests

from utils.file import read_json, write_json


PROPS_PATH = "utils/props.json"
PROPS_URL = "https://hay.toolforge.org/propbrowse/props.json"

PROPS_INDEX_PATH = "utils/props-index.json"


def read_props_index() -> dict[str, list[str]] | None:
    """Read the index of Wikidata properties and its aliases.

    Note:
        If the index file is not found, it will be downloaded from `PROPS_URL`.

    Returns:
        dict[str, set[str]]: The index of properties and its aliases.
    """

    try:
        index = read_json(PROPS_INDEX_PATH)
        log.info(f"Cached index found `{PROPS_INDEX_PATH}`")
    except FileNotFoundError:
        try:
            log.info(f"Index not found at `{PROPS_INDEX_PATH}`")
            index = create_props_index()
        except RuntimeError as e:
            log.exception(e)
            return None

    log.info(f"Found {len(index)} items in the index")

    return index


def download_props() -> list[dict]:
    """Download the Wikidata properties JSON dump.

    Returns:
        list[dict]: The list of Wikidata properties.
    """

    log.info(f"Downloading Wikidata properties from `{PROPS_URL}`")
    response = requests.get(PROPS_URL)

    if response.status_code == 200:
        write_json(PROPS_PATH, response.json())
        log.success(f"Downloaded Wikidata properties from `{PROPS_URL}`")

        return response.json()
    else:
        raise RuntimeError("Failed to download Wikidata properties from `{PROPS_URL}`")


def create_props_index() -> dict[str, list[str]]:
    """Create an searchable index for Wikidata properties and its aliases.

    Args:
        data (any): The JSON dump to index.

    Returns:
        dict[str, set[str]]: The index of properties and its aliases.
    """

    try:
        # Read the JSON dump of Wikidata properties.
        # Download the JSON dump from: https://hay.toolforge.org/propbrowse/props.json
        props: list[dict] = read_json(PROPS_PATH)
    except FileNotFoundError:
        props = download_props()

    # Remove all properties with datatype `external-id`.
    # External ID is an unique identifier for an external database (e.g., ISBN, DOI),
    # which are not useful for our use case of searching text-based values.
    props = filter_props(props, "datatype", "external-id", inverse=True)

    log.info(f"Creating index for {len(props)} items")

    # Create an index for the properties and its aliases
    index = dict()

    def add_index(key, value):
        try:
            index[key].update(value)
        except KeyError:
            index[key] = set(value)

    for item in props:
        # add {label: [label, alias1, alias2, ...]} to the index
        add_index(item["label"], [item["label"]] + item["aliases"])

        # add {aliasN: [label, alias1, alias2, ...]} to the index
        for alias in item["aliases"]:
            add_index(alias, [item["label"]] + item["aliases"])

    # Save the filtered properties and the index
    log.info(f"Created index with {len(index)} items at `{PROPS_INDEX_PATH}`")
    write_json(PROPS_INDEX_PATH, index)

    return index


def filter_props(
    props: list[dict], filter_property: str, filter_value: str, inverse: bool = False
) -> list[dict]:
    """Filter a JSON array of Wikidata properties.

    Note:
        The JSON dump can be downloaded from:
        https://hay.toolforge.org/propbrowse/props.json

        Wikidata property JSON format:
        ```json
        [
            {
                "datatype": "commonsMedia" |
                            "external-id" |
                            "geo-shape" |
                            "globe-coordinate" |
                            "math" |
                            "monolingualtext" |
                            "musical-notation" |
                            "quantity" |
                            "string" |
                            "tabular-data" |
                            "time" |
                            "url" |
                            "wikibase-form" |
                            "wikibase-item" |
                            "wikibase-lexeme" |
                            "wikibase-property" |
                            "wikibase-sense",
                "id": "P69",
                "label": "educated at",
                "description": "...",
                "aliases": [
                    "studied at",
                    "alumni of",
                    ...
                ],
                "example": [33760, 17714, ...],
                "types": ["for items about people", ...]
            },
            ...
        ]
        ```
        Details for all datatypes are available here:
        https://www.wikidata.org/wiki/Help:Data_type#Technical_details

    Args:
        props (any): The JSON dump of properties to filter from.
        property_name (str): The name of the property to filter by.
        property_value (str): The value of the property to filter by.
        inverse (bool): If True, remove all items that match the property value.

    Returns:
        list[any]: The filtered JSON array.
    """

    if inverse:
        log.info(
            f"Filtering {len(props)} items that doesn't have '{filter_property}'='{filter_value}'"
        )

        # keep all items that doesn't have the property
        results = [item for item in props if item.get(filter_property) != filter_value]
    else:
        log.info(
            f"Filtering {len(props)} items that have '{filter_property}'='{filter_value}'"
        )

        # keep all items that have the property
        results = [item for item in props if item.get(filter_property) == filter_value]

    log.info(f"Found {len(results)} items")

    return results
