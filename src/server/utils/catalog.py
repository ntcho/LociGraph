from utils.logging import log, log_func, CONFIG

log.configure(**CONFIG)

import requests

from dtos import ModelDetail

from utils.file import read_json, write_json


DEFAULT_MODEL = "gemini/gemini-pro"

CATALOG_PATH = "utils/model-catalog.json"
CATALOG_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"


def read_catalog() -> dict[str, ModelDetail] | None:
    """Read the model catalog from file.

    Note:
        If the catalog file is not found, it will be downloaded from `CATALOG_URL`.

    Returns:
        dict[str, str]: Dictionary of available models.
    """

    try:
        models: dict[str, ModelDetail] = read_json(CATALOG_PATH)
        log.info(f"Cached catalog found: {CATALOG_PATH}")
    except FileNotFoundError:
        try:
            log.info(f"Catalog not found at `{CATALOG_PATH}`")
            models = download_catalog()
        except RuntimeError as e:
            log.exception(e)
            return None

    # remove non-chat/completion models (e.g. image, video)
    for id, detail in models.items():
        try:
            if detail.mode not in ["chat", "completion"]:
                models.pop(id)
        except AttributeError:
            pass

    log.info(f"Found {len(models)} models in the catalog")

    return models


def download_catalog() -> dict[str, ModelDetail]:
    """Download the model catalog from the LiteLLM GitHub repository.

    Returns:
        dict[str, str]: Dictionary of available models.
    """

    log.info(f"Downloading catalog from `{CATALOG_URL}`")
    response = requests.get(CATALOG_URL)

    if response.status_code == 200:
        write_json(CATALOG_PATH, response.json())
        log.success(f"Downloaded catalog from `{CATALOG_URL}`")

        return response.json()
    else:
        raise RuntimeError(f"Failed to download file from `{CATALOG_URL}`")
