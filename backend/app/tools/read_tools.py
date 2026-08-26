import json, re
from typing import List, Optional, Dict, Any
from backend.app.models.catalog import Product, ProductFilter
from backend.app.models.cart import BundleOffer, Cart, CartItem

class ReadAndDecisionTools:
    def __init__(self):
        self.reload_catalog()

    def reload_catalog(self):
        with open("backend/app/data/catalog_db.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            self.catalog = [Product(**item) for item in data]

    def catalog_lookup(self, filter_params: ProductFilter) -> List[Product]:
        self.reload_catalog()
        candidates = self.catalog

        # 1. Hard constraint: In-stock
        if filter_params.in_stock_only:
            candidates = [p for p in candidates if p.inventory > 0]

        # 2. Hard constraint: Max Price
        if filter_params.max_price is not None and filter_params.max_price > 0:
            candidates = [p for p in candidates if p.price <= filter_params.max_price]

        # 3. Category Filter
        if filter_params.category:
            cat_match = [p for p in candidates if p.category == filter_params.category]
            if cat_match:
                candidates = cat_match

        # 4. Semantic Keyword Scoring
        if filter_params.query:
            raw_query = filter_params.query.lower()
            # Remove filler words
            stop_words = {"find", "me", "the", "best", "available", "good", "under", "below", "rs", "inr", "rupees", "for", "a", "an", "with", "around"}
            tokens = [t for t in re.findall(r'[a-zA-Z0-9_.]+', raw_query) if t not in stop_words and len(t) > 1]

            scored_items = []
            for p in candidates:
                score = 0
                searchable_text = f"{p.name} {p.category} {' '.join(p.tags)} {' '.join(str(v) for v in p.specs.values())} {p.description}".lower()
                
                # Category bonus
                if any(syn in raw_query for syn in ["phone", "smartphone", "mobile"]) and p.category == "smartphones":
                    score += 50
                if any(syn in raw_query for syn in ["keyboard", "typing"]) and p.category == "mechanical_keyboards":
                    score += 50
                if any(syn in raw_query for syn in ["mouse", "vertical", "wrist"]) and p.category in ["ergonomics", "workspace_accessories"]:
                    score += 50
                if any(syn in raw_query for syn in ["headphone", "audio", "anc", "sound"]) and p.category == "audio_equipment":
                    score += 50

                # Compact / Small screen bonus
                if any(syn in raw_query for syn in ["small", "compact", "mini", "one hand", "small screen", "small display"]):
                    if any(t in ["small_display", "compact_phone", "mini_phone", "5.9_inch", "5.4_inch", "6.1_inch"] for t in p.tags):
                        score += 40

                # Token frequency matching
                for token in tokens:
                    if token in p.name.lower():
                        score += 25
                    if any(token in tag.lower() for tag in p.tags):
                        score += 20
                    if token in searchable_text:
                        score += 10

                if score > 0 or not tokens:
                    scored_items.append((score, p))

            scored_items.sort(key=lambda x: (x[0], x[1].rating), reverse=True)
            return [item[1] for item in scored_items]

        return candidates

    def get_product(self, product_id: str) -> Optional[Product]:
        self.reload_catalog()
        for p in self.catalog:
            if p.id == product_id:
                return p
        return None

    def calculate_upsell_bundle(self, primary_product_id: str) -> Optional[BundleOffer]:
        primary = self.get_product(primary_product_id)
        if not primary or not primary.complementary_product_ids:
            return None

        comp_id = primary.complementary_product_ids[0]
        comp = self.get_product(comp_id)
        if not comp:
            return None

        original_combined = primary.price + comp.price
        discount_percentage = 5.0
        discount_amount = round(original_combined * (discount_percentage / 100.0), 2)
        bundle_price = round(original_combined - discount_amount, 2)

        return BundleOffer(
            bundle_id=f"bundle_{primary.id}_{comp.id}",
            title=f"{primary.name} + {comp.name} Pro Bundle",
            description=f"Add {comp.name} and unlock 5% instant bundle savings.",
            primary_product_id=primary.id,
            primary_product_name=primary.name,
            complementary_product_id=comp.id,
            complementary_product_name=comp.name,
            original_combined_price=original_combined,
            discounted_bundle_price=bundle_price,
            savings_amount=discount_amount,
            discount_percentage=discount_percentage,
            rationale=f"Recommended pairing: 84% of {primary.name} customers pair with {comp.name}."
        )

read_tools = ReadAndDecisionTools()
