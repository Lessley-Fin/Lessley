from pydantic import BaseModel
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
    primary_category: str
    mcc_code: int
    confidence_level: str  # 'HIGH', 'MEDIUM', 'LOW'


# 2. Define DTOs for deal classification
class DealCategory(BaseModel):
    category: str
    subcategory: str
    relevance_score: float  # 0.0 to 1.0
    confidence_level: str  # 'HIGH', 'MEDIUM', 'LOW'


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
                "content": "You are a financial classification API. Given a store name, return the most accurate Merchant Category Code (MCC) and a broad retail category. If the store is an Israeli brand, use your knowledge of the Israeli retail market.",
            },
            {"role": "user", "content": f"Classify this store: {store_name.strip()}"},
        ],
        response_format=StoreCategory,
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
