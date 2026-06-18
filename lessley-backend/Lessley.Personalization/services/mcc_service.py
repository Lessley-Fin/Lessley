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
        Convert a user category tag to MCC codes.

        Categories are stored as MCC string labels (the MCC code itself), so a tag that is a
        known MCC code maps directly to that code. A legacy text label falls back to a
        description substring match. Used by RecommendationService for club-matching without
        re-running the full spending analysis.
        """
        tag = str(tag).strip()
        if not tag:
            return []

        # Primary path: the tag is an MCC code (MCC string label).
        if tag in self._mcc_map:
            try:
                return [int(tag)]
            except ValueError:
                pass

        # Fallback: legacy text label → match against MCC descriptions.
        tag_upper = tag.upper()
        codes: List[int] = []
        for mcc_code, description in self._mcc_map.items():
            desc_upper = description.upper()
            if tag_upper in desc_upper or desc_upper in tag_upper:
                try:
                    codes.append(int(mcc_code))
                except ValueError:
                    pass
        return codes
