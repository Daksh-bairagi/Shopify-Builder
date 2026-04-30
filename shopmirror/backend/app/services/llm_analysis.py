"""
llm_analysis.py — C2 heuristic: does a product title contain a category noun?

Zero LLM calls. Uses product_type field + a curated category noun list.
"""
from __future__ import annotations

from app.models.merchant import Product


# ---------------------------------------------------------------------------
# Curated set of category nouns an AI agent would use to identify product type
# ---------------------------------------------------------------------------

_CATEGORY_NOUNS: set[str] = {
    # apparel
    "shirt", "t-shirt", "tshirt", "tee", "top", "blouse", "jacket", "coat",
    "hoodie", "sweater", "cardigan", "pullover", "vest", "pants", "jeans",
    "shorts", "skirt", "dress", "gown", "suit", "blazer", "leggings", "tights",
    "socks", "underwear", "bra", "bikini", "swimsuit", "pajamas", "robe",
    # footwear
    "shoe", "shoes", "sneaker", "sneakers", "boot", "boots", "sandal",
    "sandals", "heel", "heels", "loafer", "slip-on", "moccasin",
    # accessories
    "hat", "cap", "beanie", "scarf", "gloves", "glove", "belt", "bag",
    "handbag", "backpack", "wallet", "purse", "tote", "clutch", "pouch",
    # beauty / health
    "serum", "cream", "lotion", "oil", "balm", "mask", "cleanser",
    "moisturizer", "sunscreen", "perfume", "cologne", "shampoo", "conditioner",
    "supplement", "vitamin", "protein", "gel", "spray", "powder", "lip",
    # home
    "pillow", "blanket", "towel", "sheet", "duvet", "curtain", "rug", "mat",
    "lamp", "light", "candle", "vase", "frame", "mirror", "shelf", "desk",
    "chair", "table", "stool", "cabinet", "drawer", "organizer", "storage",
    # kitchen
    "mug", "cup", "glass", "bottle", "bowl", "plate", "pan", "pot",
    "knife", "fork", "spoon",
    # tech
    "phone", "case", "charger", "cable", "stand", "keyboard", "mouse",
    "headphone", "headphones", "earphones", "earbuds", "speaker", "watch",
    "tracker", "camera", "monitor", "tablet", "laptop",
    # sports
    "mat", "band", "dumbbell", "weight", "kettle", "yoga", "ball", "tent",
    # stationery
    "notebook", "journal", "pen", "pencil", "planner", "sticker", "poster",
    "print", "card", "calendar",
    # toys / gifts
    "toy", "game", "puzzle", "doll", "figure", "kit",
    # jewellery
    "ring", "necklace", "bracelet", "earring", "earrings", "chain", "pendant",
    "brooch", "anklet",
    # food / drink
    "tea", "coffee", "chocolate", "candy", "snack", "bar",
    # bundles
    "set", "bundle", "pack", "collection", "box",
}


# ---------------------------------------------------------------------------
# Core heuristic
# ---------------------------------------------------------------------------

def _title_has_category_noun(product: Product) -> tuple[bool, str | None]:
    """
    Return (found, noun_found).

    Strategy (in order):
    1. Check if any token in product_type appears in the title.
    2. Check title tokens against the curated noun list.
    """
    import re
    title_tokens = set(re.split(r"[\s\-/]+", product.title.lower()))

    # 1. product_type tokens in title
    if product.product_type:
        type_tokens = re.split(r"[\s\-/]+", product.product_type.lower())
        for tok in type_tokens:
            tok = tok.strip()
            if len(tok) > 2 and tok in title_tokens:
                return True, tok

    # 2. curated noun list
    for tok in title_tokens:
        tok = tok.strip('.,!?()')
        if tok in _CATEGORY_NOUNS:
            return True, tok

    return False, None


# ---------------------------------------------------------------------------
# Public API — same signature as before, now zero LLM calls
# ---------------------------------------------------------------------------

async def analyze_products(products: list[Product]) -> list[dict]:
    """
    Determine which products have brand-name-only titles (no category noun).

    Returns a list of dicts with keys:
        - product_id: str
        - title_contains_category_noun: bool

    Async for API compatibility; implementation is fully synchronous.
    """
    results: list[dict] = []
    for product in products:
        found, noun = _title_has_category_noun(product)
        results.append({
            "product_id": product.id,
            "title_contains_category_noun": found,
        })
    return results
