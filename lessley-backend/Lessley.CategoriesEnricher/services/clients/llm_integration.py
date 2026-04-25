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


# MCC Reference Database - Categorized with specificity levels
MCC_REFERENCE = {
    # GENERAL/MISCELLANEOUS (AVOID UNLESS TRULY NEEDED)
    "GENERAL": {
        5999: {"name": "Miscellaneous and Specialty Retail", "specificity": "VERY_GENERAL"},
        5411: {"name": "Grocery Stores, Supermarkets", "specificity": "GENERAL"},
        5699: {"name": "Miscellaneous Apparel and Accessory Stores", "specificity": "GENERAL"},
    },
    
    # SPECIFIC RETAIL CATEGORIES
    "APPAREL": {
        5651: {"name": "Family Clothing Stores", "specificity": "SPECIFIC"},
        5655: {"name": "Sports Apparel and Accessory Shops", "specificity": "SPECIFIC"},
        5957: {"name": "Shoe Stores", "specificity": "SPECIFIC"},
    },
    
    "ELECTRONICS": {
        5732: {"name": "Electronic Equipment Stores", "specificity": "SPECIFIC"},
        5734: {"name": "Computer/Software Stores", "specificity": "SPECIFIC"},
        5722: {"name": "Electrical Parts and Equipment Stores", "specificity": "SPECIFIC"},
    },
    
    "BOOKS": {
        5942: {"name": "Book Stores", "specificity": "SPECIFIC"},
        5943: {"name": "Stationery Stores", "specificity": "SPECIFIC"},
    },
    
    "SPORTS": {
        5941: {"name": "Sporting Goods Stores", "specificity": "SPECIFIC"},
        5655: {"name": "Sports Apparel and Accessory Shops", "specificity": "SPECIFIC"},
        5999: {"name": "Miscellaneous and Specialty Retail", "specificity": "GENERAL"},
    },
    
    "DINING": {
        5812: {"name": "Eating Places and Restaurants", "specificity": "SPECIFIC"},
        5814: {"name": "Fast Food Restaurants", "specificity": "SPECIFIC"},
        5813: {"name": "Drinking Places (Bars, Nightclubs)", "specificity": "SPECIFIC"},
    },
    
    "ENTERTAINMENT": {
        7832: {"name": "Motion Picture Theaters", "specificity": "SPECIFIC"},
        7999: {"name": "Entertainment/Recreation Services", "specificity": "SPECIFIC"},
        5945: {"name": "Toy and Hobby Shops", "specificity": "SPECIFIC"},
    },
    
    "TRAVEL": {
        4722: {"name": "Travel Agencies", "specificity": "SPECIFIC"},
        7011: {"name": "Lodging - Hotels and Motels", "specificity": "SPECIFIC"},
    },
    
    "HEALTH_BEAUTY": {
        5912: {"name": "Drug Stores", "specificity": "SPECIFIC"},
        5977: {"name": "Cosmetics Stores", "specificity": "SPECIFIC"},
    },
}

# MCC codes to AVOID as primary choices (too generic)
GENERAL_MCCS = {5999, 5411, 5699, 7299, 7299}


# 1. Define DTOs for store classification
class StoreCategory(BaseModel):
    official_name: str
    mcc_codes: List[int] = Field(
        description="A ranked list of the 1 to 5 most accurate MCC codes, from most specific to least specific. Return empty array if not sure. Avoid general MCCs (5999, 5411, 5699) unless the store is truly miscellaneous."
    )
    confidence_level: Literal["HIGH", "MEDIUM", "LOW", "UNCERTAIN"]
    reasoning: str = Field(
        description="Brief explanation of why these MCCs were chosen and the confidence level"
    )


# 2. Define DTOs for deal classification
class DealCategory(BaseModel):
    category: str
    subcategory: str
    relevance_score: float  # 0.0 to 1.0
    confidence_level: Literal["HIGH", "MEDIUM", "LOW"]


# Helper function to filter MCCs by confidence
def filter_mcc_by_confidence(mcc_codes: List[int], confidence: str, was_uncertain: bool = False) -> List[int]:
    """
    Filter MCCs based on confidence level and rules about general MCCs.
    
    HIGH confidence: Return all MCCs (up to 5) if they're not all general
    MEDIUM confidence: Return only specific MCCs, minimum necessary
    LOW confidence: Return only 1-2 most specific MCCs
    UNCERTAIN: Return empty array
    """
    if was_uncertain or confidence == "UNCERTAIN":
        return []
    
    # Filter out general MCCs first
    specific_mccs = [mcc for mcc in mcc_codes if mcc not in GENERAL_MCCS]
    general_mccs = [mcc for mcc in mcc_codes if mcc in GENERAL_MCCS]
    
    if confidence == "HIGH":
        # Return all specific MCCs (up to 5), then add general if needed for context
        if specific_mccs:
            return specific_mccs[:5]
        elif general_mccs:
            return general_mccs[:5]
        else:
            return mcc_codes[:5]
    
    elif confidence == "MEDIUM":
        # Return only specific MCCs (1-3), avoid general ones
        if specific_mccs:
            return specific_mccs[:3]
        else:
            return []  # Don't return general MCCs if medium confidence
    
    elif confidence == "LOW":
        # Return only the most confident specific MCC (1 max)
        if specific_mccs:
            return specific_mccs[:1]
        else:
            return []
    
    return []


# 3. Classification function for stores
def get_store_category(store_name: str) -> StoreCategory:
    """
    Classifies a store by name and returns its primary category and MCC code.

    Args:
        store_name: The name of the store to classify

    Returns:
        StoreCategory with official_name, mcc_codes, and confidence_level
    """
    logger.debug(f"Classifying store: {store_name.strip()}", extra={"reason": "LLM store classification requested"})

    # Build the MCC reference context for the prompt
    mcc_context = "MERCHANT CATEGORY CODE (MCC) REFERENCE:\n"
    for category, codes in MCC_REFERENCE.items():
        mcc_context += f"\n{category}:\n"
        for mcc, info in codes.items():
            mcc_context += f"  • {mcc}: {info['name']} (Specificity: {info['specificity']})\n"

    system_prompt = (
        "You are an expert financial classification engine specializing in Israeli retail and service businesses. "
        "Your task is to classify store names to Merchant Category Codes (MCCs) with HIGH accuracy.\n\n"
        
        "CRITICAL RULES:\n"
        "1. AVOID GENERAL MCCs (5999, 5411, 5699) UNLESS THE STORE IS TRULY MISCELLANEOUS\n"
        "2. Prefer SPECIFIC MCCs that clearly match the store's primary business\n"
        "3. For HIGH confidence: Return up to 5 MCCs ranked from most to least specific\n"
        "4. For MEDIUM confidence: Return 1-3 specific MCCs only, skip general codes\n"
        "5. For LOW confidence: Return at most 1 MCC\n"
        "6. For UNCERTAIN: Return empty array []\n"
        "7. Always return the MOST SPECIFIC MCC first in the array\n\n"
        
        f"{mcc_context}\n\n"
        
        "ENTITY RESOLUTION GUIDELINES:\n"
        "- Handle typos, misspellings, and formatting issues (e.g., 'nikestore', 'nike-store', 'nikeshop' → Nike)\n"
        "- Remove domain extensions (.co.il, .com) and extraneous words (deal, promo, etc.)\n"
        "- Identify Israeli brands and local businesses\n"
        "- Use your knowledge of popular Israeli retailers, restaurants, and services\n\n"
        
        "CONFIDENCE LEVELS:\n"
        "- HIGH: You're very certain (>90% confidence) - the store name clearly indicates its business type\n"
        "- MEDIUM: Fairly certain (70-90%) - store type is clear but not 100% obvious\n"
        "- LOW: Uncertain (<70%) - store could be multiple types\n"
        "- UNCERTAIN: No reasonable confidence in any classification\n\n"
        
        "EXAMPLES OF CORRECT CLASSIFICATIONS:\n"
        "1. 'nikestore' or 'nike' → official_name: 'Nike', mcc_codes: [5655, 5941], confidence: HIGH\n"
        "   (5655 = Sports Apparel, most specific; 5941 = Sporting Goods as alternative)\n"
        "2. 'shufersal' or 'Shufersal' → official_name: 'Shufersal', mcc_codes: [5411], confidence: HIGH\n"
        "   (5411 = Grocery Stores - this IS the specific category)\n"
        "3. 'terminal-x' or 'terminalx' → official_name: 'Terminal X', mcc_codes: [5651], confidence: MEDIUM\n"
        "   (Fashion/Apparel - not miscellaneous)\n"
        "4. 'ksp' or 'ksp.co.il' → official_name: 'KSP', mcc_codes: [5732, 5734], confidence: HIGH\n"
        "   (Electronics - both 5732 and 5734 are acceptable electronics codes)\n"
        "5. 'someweirdname123' → official_name: 'someweirdname123', mcc_codes: [], confidence: UNCERTAIN\n"
        "   (Cannot determine store type - return empty array)\n\n"
        
        "IMPORTANT: If you're returning MCC codes, make sure:\n"
        "- Each code is a valid 4-digit integer\n"
        "- They're ranked from most to least specific\n"
        "- You avoid multiple general codes (never return both 5999 AND 5411 AND 5699)\n"
        "- Your confidence level matches the number and specificity of MCCs returned"
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Classify this store: {store_name.strip()}"},
        ],
        response_format=StoreCategory,
        temperature=0.0,  # Deterministic output for classification
        seed=42,  # Fixed seed for reproducibility
    )

    result = completion.choices[0].message.parsed
    
    # Post-process: Filter MCCs based on confidence level
    was_uncertain = result.confidence_level == "UNCERTAIN" or not result.mcc_codes
    filtered_mccs = filter_mcc_by_confidence(result.mcc_codes, result.confidence_level, was_uncertain)
    
    logger.debug(
        f"Classification result for {store_name.strip()}: {result.official_name} -> MCCs: {filtered_mccs} (confidence: {result.confidence_level})",
        extra={"reason": "LLM store classification completed"}
    )
    
    return StoreCategory(
        official_name=result.official_name,
        mcc_codes=filtered_mccs,
        confidence_level=result.confidence_level,
        reasoning=result.reasoning
    )


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
