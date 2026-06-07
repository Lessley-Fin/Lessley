import logging
from typing import List

from models.db.entities import MccCode

logger = logging.getLogger(__name__)


class MccService:
    def __init__(self):
        self._mcc_map: dict[str, str] = {}
        logger.info("MccService initialized. Call initialize() to load data.")

    async def initialize(self):
        """
        Reads MCC codes from the MongoDB database and builds a flat dictionary.
        """
        logger.info("Loading MCC codes from database...")
        try:
            mcc_codes = await MccCode.find_all().to_list()
            for item in mcc_codes:
                mcc_code_val = item.mcc
                description = item.category or "N/A"
                if mcc_code_val:
                    self._mcc_map[str(mcc_code_val)] = description

            logger.info(f"MccService: Successfully loaded {len(self._mcc_map)} MCC descriptions into memory.")
        except Exception as e:
            logger.error(f"Error loading MCC codes from database: {e}", exc_info=True)
            raise

    def get_mcc(self) -> dict[str, str]:
        """
        Returns the entire MCC mapping as a dictionary.
        """
        return self._mcc_map

    def get_mcc_by_id(self, category_code: str) -> str:
        """
        Returns the clean, human-readable description for an MCC.
        """
        return self._mcc_map.get(str(category_code), "N/A")

    def get_mcc_codes_by_tag(self, tag: str) -> List[int]:
        """
        Reverse-lookup: return MCC codes whose description contains the tag string.
        Used by RecommendationService to convert user category tags back to MCC codes
        for club-matching without re-running the full spending analysis.
        """
        tag_upper = tag.strip().upper()
        codes: List[int] = []
        for mcc_code, description in self._mcc_map.items():
            desc_upper = description.upper()
            if tag_upper in desc_upper or desc_upper in tag_upper:
                try:
                    codes.append(int(mcc_code))
                except ValueError:
                    pass
        return codes
