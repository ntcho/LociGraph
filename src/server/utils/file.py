import json


def read_txt(file_path: str) -> str:
    with open(file_path, "r") as file:
        return file.read()


def read_json(file_path: str):
    with open(file_path, "r") as file:
        data = json.load(file)

    return data


def write_json(file_path: str, data) -> None:
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4, default=seralize_sets)


def seralize_sets(obj):
    """Serializer for `json.dump()`. Adds support for serializing set to list."""
    # from https://stackoverflow.com/a/60544597/4524257
    if isinstance(obj, set):
        return list(obj)
    return obj