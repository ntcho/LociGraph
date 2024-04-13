from utils.logging import log, log_func


from litestar import Litestar, post, exceptions

from models.mrebel.extract import extract as mrebel_extract

from dtos import Relation

import utils.error as error


@post("/extract/", sync_to_thread=True)
@log_func()
def extract_relation(data: str) -> list[Relation]:
    """Extract relation triplets from the given paragraph.

    Note:
        This litestar app runs on a separate litestar instance in order to enable hot
        reload on the main litestar app.
        Use `LITESTAR_APP=models.app:app litestar run --port 8001` to start the server.

    Args:
        data (str): String containing the paragraph to extract relations from.

    Returns:
        list[Relation]: List of extracted relations triplets.
    """

    log.info(f"Extracting relations from text (len(data)={len(data)})")

    if data is None or data == "":
        raise exceptions.HTTPException(
            status_code=400,
            detail=f"Couldn't read request body. {error.CHECK_INPUT}",
        )

    if mrebel_extract is None:
        raise exceptions.HTTPException(
            status_code=500,
            detail=f"Failed to load the mREBEL model. {error.CHECK_SERVER}",
        )

    return mrebel_extract(data)


# Separate litestar instance for mREBEL model
app = Litestar(route_handlers=[extract_relation])
