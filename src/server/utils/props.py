from utils.file import read_json, write_json


def filter_props(
    data: list[dict],
    filter_property: str,
    filter_value: str,
    inverse: bool = False,
) -> list[dict]:
    """Filter a JSON array of WikiData properties.

    Note:
        The JSON dump can be downloaded from:
        https://hay.toolforge.org/propbrowse/props.json

        WikiData property JSON format:
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
        data (any): The JSON dump to filter.
        property_name (str): The name of the property to filter by.
        property_value (str): The value of the property to filter by.
        inverse (bool): If True, remove all items that match the property value.

    Returns:
        list[any]: The filtered JSON array.
    """
    if inverse:
        filtered_data = [
            item for item in data if item.get(filter_property) != filter_value
        ]
    else:
        filtered_data = [
            item for item in data if item.get(filter_property) == filter_value
        ]

    return filtered_data


def create_props_index(
    data: list[dict],
) -> dict[str, set[str]]:
    """Create an searchable index for WikiData properties and its aliases.

    Args:
        data (any): The JSON dump to index.

    Returns:
        dict[str, set[str]]: The index of properties and its aliases.
    """
    index = dict()

    def add_index(key, value):
        try:
            index[key].update(value)
        except KeyError:
            index[key] = set(value)

    for item in data:
        # add {label: [label, alias1, alias2, ...]} to the index
        add_index(item["label"], [item["label"]] + item["aliases"])

        # add {aliasN: [label, alias1, alias2, ...]} to the index
        for alias in item["aliases"]:
            add_index(alias, [item["label"]] + item["aliases"])

    return index


# Read the JSON dump of WikiData properties.
# Download the JSON dump from: https://hay.toolforge.org/propbrowse/props.json
data: list[dict] = read_json("props.json")

# Remove all properties with datatype `external-id`.
# External ID is an unique identifier for an external database (e.g., ISBN, DOI),
# which are not useful for our use case of searching text-based values.
props = filter_props(data, "datatype", "external-id", inverse=True)

# Create an index for the properties and its aliases.
index = create_props_index(props)

# Save the filtered properties and the index.
write_json("props-index.json", index)
