class LIMITS:
    TOP_CATEGORIES = 20
    TOP_ACCOUNTS = 10
    TOP_STORES = 50
    MAX_PAGE_SIZE = 1000
    DAYS = 90
    HIT_THRESHOLD = 0.20


class STORE_MATCH:
    """
    Thresholds for matching a card-feed merchant name to a shop in our store list.

    Tuned against 152 real merchant names (~25 of which have a genuine match). That is a
    small sample, so treat these as a starting point to be re-checked against production
    data rather than as settled values.
    """

    # How much of the *shop's* name the merchant string has to account for. A shop whose
    # own brand word is missing from the merchant string is not that shop:
    # 'נאור סקה עיצוב שיער' covers only 0.62 of 'דן עיצוב שיער', because 'דן' is absent.
    STORE_COVERAGE_MIN = 0.65

    # How much of the *merchant's* own identifying words the shop has to account for.
    # This is the one that catches 'קפה ברלין' -> 'קפה קפה': the shop's name is fully
    # covered, but 'ברלין' — the word that actually names the merchant — is left over.
    QUERY_COVERAGE_MIN = 0.75

    # Two shops scoring within this margin of each other means the name is ambiguous,
    # and we would rather say nothing than guess.
    AMBIGUITY_MARGIN = 0.02

    TOKEN_FUZZ_MIN = 88          # word-level typo tolerance ('Games' ~ 'game')
    TOWN_FUZZ_MIN = 85           # feeds misspell town names ('גלילות' arriving as 'מלילות')
    FUZZY_MASS_DISCOUNT = 0.75   # a typo-match is weaker evidence than an exact one

    # Rarity floors, on the index's 0..1 scale (0 = in every shop name, 1 = in none).
    # A word shared by many shops (קפה, פיצה) says nothing about *which* shop this is,
    # however neatly the strings line up.
    DISTINCT_RARITY_FLOOR = 0.615   # below this a word cannot identify a shop on its own
    SOLO_RARITY_MIN = 0.671         # a one-word match has to be rarer still
    EVIDENCE_RARITY_MIN = 1.006     # total rarity a match must carry overall

    MIN_QUERY_LENGTH = 3
    MIN_DISTINCT_TOKEN_LENGTH = 3   # 2-letter words are feed truncation, never a brand

    # Words this common are useless for narrowing candidates down; skip them when
    # gathering shops to score.
    CANDIDATE_DF_CAP = 400
