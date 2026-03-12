import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class MccService:
    ALLOWED_DATA_FILES = "main/config/mcc_codes.json"

    def __init__(self):
        self._mcc_map: dict[str, str] = {}  # Initialize before _load_mapping
        path = Path(__file__).parent.parent.parent.parent / self.ALLOWED_DATA_FILES
        path = path.resolve()

        if not path.exists() or not path.is_file():
            logger.error(f"MccService failed to initialize from {path}")
            raise FileNotFoundError(f"MCC codes file not found: {path}")

        logger.info(f"[*] MccService: Loading MCC codes from {path.absolute()}")
        self._load_mapping(path)

    def _load_mapping(self, path: Path):
        """
        Reads the JSON array from the file and builds a flat dictionary.
        """
        with open(path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)

            for item in raw_data:
                mcc_code = item.get("mcc")

                description = item.get("edited_description") or item.get("combined_description") or "Unknown Category"

                if mcc_code:
                    self._mcc_map[str(mcc_code)] = description

        logger.info(f"MccService: Successfully loaded {len(self._mcc_map)} MCC descriptions into memory.")

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
