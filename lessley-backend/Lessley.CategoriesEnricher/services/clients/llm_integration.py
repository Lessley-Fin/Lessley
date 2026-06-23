from pydantic import BaseModel, Field
from typing import List, Literal
from openai import OpenAI
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

# Initialize OpenAI client from settings
client = OpenAI(
    base_url="https://models.inference.ai.azure.com/",
    api_key=settings.OpenAI_ApiKey or "",
)


# 1. Define DTOs for store classification
class StoreCategory(BaseModel):
    official_name: str
    mcc_codes: List[str] = Field(
        description="A ranked list of the 1 to 3 most relevant category names from the canonical set (e.g. GROCERIES, RESTAURANT, ELECTRONICS, CLOTHES_&_ACCESSORIES, etc.)."
    )
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]


# 2. Define DTOs for deal classification
class DealCategory(BaseModel):
    category: str
    subcategory: str
    relevance_score: float  # 0.0 to 1.0
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]


# 3. Classification function for stores
def get_store_category(store_name: str) -> StoreCategory:
    """
    Classifies a store by name and returns its primary category and MCC code.

    Args:
        store_name: The name of the store to classify

    Returns:
        StoreCategory with primary_category, mcc_code, and confidence_level
    """
    logger.debug(f"Classifying store: {store_name.strip()}", extra={"reason": "LLM store classification requested"})

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert data normalization and financial classification engine for the Israeli brands and retail market. "
                    "Assume that the store exists but have typos or inconsistencies. Try to identify the official store name. "
                    "Process raw, messy store strings (typos, hyphens, missing spaces, domain extensions) and perform Entity Resolution. "
                    "1. Return the official name of the store if you can identify it. If not, return the cleaned name with typos corrected and extraneous characters removed. "
                    "2. Provide an array of the top 1 to 3 most relevant category names from this canonical set: "
                    "ALCOHOL_&_TOBACCO, BARS, BEAUTY, BOOKS_&_GAMES, BUSINESS_EXPENSES, CAPITAL_MARKET, CAR_&_FUEL, CHARITY, "
                    "CLOTHES_&_ACCESSORIES, COFFEE_&_SNACKS, COMMUNICATIONS, CULTURE_&_EVENTS, EDUCATION, ELECTRONICS, FEES, "
                    "FINANCE_OTHER, FLIGHTS, FOOD_&_DRINKS_OTHER, FURNITURE_&_INTERIOR, GARDEN, GIFTS, GROCERIES, HEALTHCARE, "
                    "HEALTH_&_BEAUTY_OTHER, HOBBIES, HOBBY_&_SPORTS_EQUIPMENT, HOME, HOME_IMPROVEMENTS_OTHER, "
                    "HOUSEHOLD_&_SERVICES_-_OTHER, INSURANCE_&_FEES, KIDS, LEISURE_OTHER, LOANS, OTHER, PETS, PHARMACY, "
                    "PUBLIC_TRANSPORT, RENOVATION_&_REPAIRS, RESTAURANT, SAVINGS, SERVICES, SHOPPING_OTHER, SPORTS_&_FITNESS, "
                    "TRANSPORT_OTHER, UTILITIES, VACATION. "
                    "Rank the array from most specific/likely to least specific/likely. "
                    "3. Provide a confidence_level of HIGH, MEDIUM, or LOW based on how certain you are. Use HIGH if you're very certain and found a clear match, MEDIUM if fairly certain, LOW if uncertain. If you cannot classify, return LOW. "
                    "EXAMPLES: "
                    "a) Input: 'nikestore' -> official_name: 'Nike', mcc_codes: ['HOBBY_&_SPORTS_EQUIPMENT', 'CLOTHES_&_ACCESSORIES']. "
                    "b) Input: 'shufersal-deal' -> official_name: 'Shufersal', mcc_codes: ['GROCERIES']. "
                    "c) Input: 'ksp.co.il' -> official_name: 'KSP', mcc_codes: ['ELECTRONICS']."
                ),
            },
            {"role": "user", "content": f"Analyze and classify this store string: {store_name.strip()}"},
        ],
        response_format=StoreCategory,
        temperature=0.0,  # Deterministic output for classification
        seed=42,  # Fixed seed for reproducibility
    )

    return completion.choices[0].message.parsed


# 4. Classification function for deals
def get_deal_category(deal_name: str, deal_description: str | None = None) -> DealCategory:
    """
    Classifies a deal/promotion and returns its category and relevance.

    Args:
        deal_name: The name or title of the deal
        deal_description: Optional description of the deal

    Returns:
        DealCategory with category, subcategory, relevance_score, and confidence_level
    """
    description_text = f"{deal_name}. {deal_description}" if deal_description else deal_name

    logger.info(
        f"Classifying deal: {description_text}",
        extra={
            "reason": "LLM deal classification requested",
            "extra_data": {"deal_name": deal_name, "deal_description": deal_description},
        },
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a financial and retail classification API. Given a deal or promotion description, classify it into appropriate categories and provide a relevance score (0.0-1.0) indicating how relevant it is to financial planning. Use 'HIGH' confidence if you're very certain, 'MEDIUM' if fairly certain, 'LOW' if uncertain.",
            },
            {"role": "user", "content": f"Classify this deal: {description_text.strip()}"},
        ],
        response_format=DealCategory,
    )

    return completion.choices[0].message.parsed
