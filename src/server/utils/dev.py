from base64 import b64encode

def read_file_to_base64(file_path: str) -> str:

    with open(file_path, "rb") as file:
        file_content = file.read()
        base64_string = b64encode(file_content).decode("utf-8")

        return base64_string