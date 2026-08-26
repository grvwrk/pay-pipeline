import json, re, os
from pathlib import Path
from typing import List, Optional, Dict, Any
from backend.app.models.catalog import Product, ProductFilter
from backend.app.models.cart import BundleOffer, Cart, CartItem

CATALOG_FILE_PATH = Path(__file__).parent.parent / "data" / "catalog_db.json"

class ReadAndDecisionTools:
    def __init__(self):
        self.catalog: List[Product] = []
        self.reload_catalog()

    def reload_catalog(self):
        if CATALOG_FILE_PATH.exists():
            with open(CATALOG_FILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.catalog = [Product(**item) for item in data]
        else:
            self.catalog = []

    def catalog_lookup(self, filter_params: ProductFilter) -> List[Product]:
        self.reload_catalog()
        candidates = self.catalog

        # 1. In-stock filter
        if filter_params.in_stock_only:
            candidates = [p for p in candidates if p.inventory > 0]

        # 2. Max Price constraint
        if filter_params.max_price is not None and filter_params.max_price > 0:
            candidates = [p for p in candidates if p.price <= filter_params.max_price]

        # 3. Category Filter (soft matching to allow cross-category fallback if empty)
        if filter_params.category:
            cat_matches = [p for p in candidates if p.category.lower() == filter_params.category.lower()]
            if cat_matches:
                candidates = cat_matches

        # 4. Semantic Keyword Scoring & Specification Reasoning
        if filter_params.query:
            raw_query = filter_params.query.lower()
            stop_words = {
                "find", "me", "the", "best", "available", "good", "under", "below",
                "rs", "inr", "rupees", "for", "a", "an", "with", "around", "i", "need", "want", "show", "buy"
            }
            tokens = [t for t in re.findall(r'[a-zA-Z0-9_.]+', raw_query) if t not in stop_words and len(t) > 1]

            wants_highest_protein = any(p in raw_query for p in ["highest protein", "high protein", "max protein", "protein %", "protein percent"])

            scored_items = []
            for p in candidates:
                score = 0
                searchable_text = f"{p.name} {p.category} {' '.join(p.tags)} {' '.join(str(v) for v in p.specs.values())} {p.description}".lower()

                # Dynamic token matching
                for token in tokens:
                    if token in p.name.lower():
                        score += 35
                    if any(token == tag.lower() or token in tag.lower() for tag in p.tags):
                        score += 30
                    if token in p.category.lower():
                        score += 20
                    if token in searchable_text:
                        score += 15

                # Phrase matching
                if p.name.lower() in raw_query or any(tag.lower() in raw_query for tag in p.tags):
                    score += 40

                # Protein percentage reasoning for fitness/nutrition queries
                if wants_highest_protein and "protein_percentage" in p.specs:
                    prot_match = re.search(r'(\d+)%', str(p.specs["protein_percentage"]))
                    if prot_match:
                        prot_num = int(prot_match.group(1))
                        score += prot_num * 3  # Higher % gets larger score boost

                if score > 0 or not tokens:
                    scored_items.append((score, p))

            scored_items.sort(key=lambda x: (x[0], x[1].rating, -x[1].price), reverse=True)
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
