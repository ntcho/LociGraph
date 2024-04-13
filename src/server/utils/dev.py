from dotenv import get_key

# Load environment variables from `.env` file
ENV: str | None = get_key(".env", "ENV")

PROD: bool = ENV is not None and ENV == "production"
DEV: bool = not PROD


def read_file_to_base64(file_path: str) -> str:
    from base64 import b64encode

    with open(file_path, "rb") as file:
        file_content = file.read()
        base64_string = b64encode(file_content).decode("utf-8")

        return base64_string


def read_mock_response(file_path: str) -> str | None:
    try:
        if DEV:
            from utils.file import read_txt

            return read_txt(file_path)
        return None
    except FileNotFoundError:
        return None


from datetime import datetime


def get_timestamp() -> str:
    return datetime.now().strftime("%y-%m-%d_%H-%M-%S")
