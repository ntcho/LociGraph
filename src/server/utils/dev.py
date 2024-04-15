from dotenv import load_dotenv
from os import getenv

# Load environment variables from `.env` file
load_dotenv(".env")

PROD: bool = getenv("ENV", "development") == "production"
DEV: bool = not PROD


def read_file_to_base64(file_path: str) -> str:
    from base64 import b64encode

    with open(file_path, "rb") as file:
        file_content = file.read()
        base64_string = b64encode(file_content).decode("utf-8")

        return base64_string


def read_mock_response(file_path: str) -> str | None:
    # check if the MOCK_RESPONSE environment variable is set to true
    if getenv("MOCK_RESPONSE", "false") == "true":
        try:
            from utils.file import read_txt

            return read_txt(file_path)

        except FileNotFoundError:
            return None

    return None


def get_timestamp() -> str:
    from datetime import datetime

    return datetime.now().strftime("%y-%m-%d_%H-%M-%S")
