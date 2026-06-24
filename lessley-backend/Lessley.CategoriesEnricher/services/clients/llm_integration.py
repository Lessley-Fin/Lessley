from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Literal
from openai import OpenAI
import logging
from config.settings import settings
import httpx

logger = logging.getLogger(__name__)

# Initialize OpenAI client from settings
# client = OpenAI(
#     base_url="https://models.inference.ai.azure.com/",
#     api_key=settings.OpenAI_ApiKey or "",
# )
# llm_model = "gpt-4o-mini"


http_client = httpx.Client(
    verify=False,
    headers={"Host": settings.COLLEGE_MODEL_HOST},
    timeout=httpx.Timeout(120.0, connect=10.0),
)

client = OpenAI(
    base_url=settings.COLLEGE_API_BASE,
    api_key=settings.OpenAI_ApiKey or "",
    http_client=http_client,
)
llm_model = settings.COLLEGE_MODEL_NAME


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


class MccCategory(str, Enum):
    ALCOHOL_AND_TOBACCO = "ALCOHOL_&_TOBACCO"
    BARS = "BARS"
    BEAUTY = "BEAUTY"
    BOOKS_AND_GAMES = "BOOKS_&_GAMES"
    BUSINESS_EXPENSES = "BUSINESS_EXPENSES"
    CAPITAL_MARKET = "CAPITAL_MARKET"
    CAR_AND_FUEL = "CAR_&_FUEL"
    CHARITY = "CHARITY"
    CLOTHES_AND_ACCESSORIES = "CLOTHES_&_ACCESSORIES"
    COFFEE_AND_SNACKS = "COFFEE_&_SNACKS"
    COMMUNICATIONS = "COMMUNICATIONS"
    CULTURE_AND_EVENTS = "CULTURE_&_EVENTS"
    EDUCATION = "EDUCATION"
    ELECTRONICS = "ELECTRONICS"
    FEES = "FEES"
    FINANCE_OTHER = "FINANCE_OTHER"
    FLIGHTS = "FLIGHTS"
    FOOD_AND_DRINKS_OTHER = "FOOD_&_DRINKS_OTHER"
    FURNITURE_AND_INTERIOR = "FURNITURE_&_INTERIOR"
    GARDEN = "GARDEN"
    GIFTS = "GIFTS"
    GROCERIES = "GROCERIES"
    HEALTHCARE = "HEALTHCARE"
    HEALTH_AND_BEAUTY_OTHER = "HEALTH_&_BEAUTY_OTHER"
    HOBBIES = "HOBBIES"
    HOBBY_AND_SPORTS_EQUIPMENT = "HOBBY_&_SPORTS_EQUIPMENT"
    HOME = "HOME"
    HOME_IMPROVEMENTS_OTHER = "HOME_IMPROVEMENTS_OTHER"
    HOUSEHOLD_AND_SERVICES_OTHER = "HOUSEHOLD_&_SERVICES_-_OTHER"
    INSURANCE_AND_FEES = "INSURANCE_&_FEES"
    KIDS = "KIDS"
    LEISURE_OTHER = "LEISURE_OTHER"
    LOANS = "LOANS"
    OTHER = "OTHER"
    PETS = "PETS"
    PHARMACY = "PHARMACY"
    PUBLIC_TRANSPORT = "PUBLIC_TRANSPORT"
    RENOVATION_AND_REPAIRS = "RENOVATION_&_REPAIRS"
    RESTAURANT = "RESTAURANT"
    SAVINGS = "SAVINGS"
    SERVICES = "SERVICES"
    SHOPPING_OTHER = "SHOPPING_OTHER"
    SPORTS_AND_FITNESS = "SPORTS_&_FITNESS"
    TRANSPORT_OTHER = "TRANSPORT_OTHER"
    UTILITIES = "UTILITIES"
    VACATION = "VACATION"


class DealClassification(BaseModel):
    store_official_name: str = Field(description="The official/canonical name of the store.")
    mcc_codes: List[MccCategory] = Field(
        min_length=1,
        max_length=2,
        description="1 or 2 distinct MCC category names, ranked by relevance. If 2 are returned they must be different from each other."
    )
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]
    reasoning: str = Field(description="Brief explanation of why these categories were chosen.")


_CANONICAL_CATEGORIES = ", ".join(c.value for c in MccCategory)

_CLASSIFY_DEAL_SYSTEM_PROMPT = (
    "You are an expert financial classification engine for the Israeli retail market. "
    "Given a store and its associated deal/promotion, classify the store into the most relevant MCC categories.\n\n"
    "RULES:\n"
    "1. You MUST ONLY select categories from this canonical set: " + _CANONICAL_CATEGORIES + ".\n"
    "2. Do NOT invent, modify, or combine categories. Use the exact strings above.\n"
    "3. Return 1 or 2 categories. If the store clearly fits a single category, return only 1. If it spans two distinct categories, return 2 — but the two MUST be different from each other.\n"
    "4. Use all provided signals: store name, store URL, deal link, deal title, deal description, and store images.\n"
    "5. Provide a confidence_level: HIGH if the classification is clearly supported by the context, "
    "MEDIUM if somewhat ambiguous, LOW if the context is insufficient.\n"
    "6. Provide a brief reasoning explaining which signals led to your classification.\n"
    "7. If the store name is messy (typos, domain extensions), resolve it to the official brand name.\n"
    "8. Always prioritize the store's URL and deal title/description over store's name when determining categories.\n"
    "9. Your BEST SIGNAL is the store's URL and benefit deals. try to navigation and scan the website and picture for accurate results.\n"
)


def classify_deal_store(
    deal_title: str,
    deal_description: str | None,
    store_name: str,
    store_url: str | None,
    deal_url: str | None,
    benefit_url: str | None,
    store_image_urls: list[str] | None,
) -> DealClassification:
    logger.info(
        f"Classifying deal store: {store_name} - {deal_title}",
        extra={
            "reason": "LLM deal-store classification requested",
            "extra_data": {
                "store_name": store_name,
                "deal_title": deal_title,
                "store_url": store_url,
                "benefit_url": benefit_url,
                "deal_url": deal_url,
            },
        },
    )

    context_text = (
        "=== PRIMARY SIGNALS (strongest evidence — base your decision on these) ===\n"
        f"Store URL: {store_url or 'N/A'}\n"
        f"Benefit Link: {benefit_url or 'N/A'}\n"
        f"Deal Link: {deal_url or 'N/A'}\n\n"
        "=== SECONDARY SIGNALS ===\n"
        f"Deal Title: {deal_title or 'N/A'}\n"
        f"Deal Description: {deal_description or 'N/A'}\n\n"
        "=== WEAK SIGNAL (corroborate only; may be generic, partial, or contain typos) ===\n"
        f"Store Name: {store_name or 'N/A'}"
    )

    user_content: list[dict] = [{"type": "text", "text": context_text}]

    for url in (store_image_urls or [])[:3]:
        user_content.append({"type": "image_url", "image_url": {"url": url, "detail": "low"}})

    completion = client.beta.chat.completions.parse(
        model=llm_model,
        messages=[
            {"role": "system", "content": _CLASSIFY_DEAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        response_format=DealClassification,
        temperature=0.0,
        seed=42,
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
        model=llm_model,
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
