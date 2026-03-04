import json
from pathlib import Path


class MccService:
    def __init__(self, file_path: str = "main/config/mcc_codes.json"):
        # This will hold our fast, in-memory O(1) lookup map
        self._mcc_map: dict[str, str] = {}
        self._load_mapping(file_path)

    def _load_mapping(self, file_path: str):
        """
        Reads the JSON array from the file and builds a flat dictionary.
        """
        path = Path(__file__).parent.parent.parent.parent / file_path
        print(f"[*] MccService: Loading MCC codes from {path.absolute()}")
        if not path.exists():
            print(f"[!] CRITICAL: MCC file not found at {path.absolute()}")
            return

        with open(path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)

            # The greggles JSON is a list of dictionary objects
            for item in raw_data:
                mcc_code = item.get("mcc")

                # Prioritize edited_description, fallback to combined if missing
                description = (
                    item.get("edited_description")
                    or item.get("combined_description")
                    or "Unknown Category"
                )

                if mcc_code:
                    self._mcc_map[str(mcc_code)] = description

        print(
            f"[*] MccService: Successfully loaded {len(self._mcc_map)} MCC descriptions into memory."
        )

    def get_mcc(self) -> dict[str, str]:
        """
        Returns the entire MCC mapping as a dictionary.
        """
        return self._mcc_map

    def get_mcc_by_id(self, category_code: str) -> str:
        """
        Returns the clean, human-readable description for an MCC.
        """
        return self._mcc_map.get(str(category_code), "Unknown Category")


# Instantiate it once as a Singleton for Dependency Injection
mcc_service_singleton = MccService()


def get_mcc_service() -> MccService:
    return mcc_service_singleton
