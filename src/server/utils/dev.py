from base64 import b64encode
from datetime import datetime


def read_file_to_base64(file_path: str) -> str:
    with open(file_path, "rb") as file:
        file_content = file.read()
        base64_string = b64encode(file_content).decode("utf-8")

        return base64_string


def get_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")
