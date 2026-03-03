import json
from pathlib import Path


class FilesUtilsService:
    def read_json(self, file_path: str):
        """
        Reads a JSON file and returns its content.
        """

        transactions_file = Path(__file__).parent.parent / "data" / file_path

        with open(transactions_file, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data


# Dependency Injection provider function
def get_files_utils_service():
    return FilesUtilsService()
