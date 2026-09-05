import json
import os
import re
from database import get_past_failures_for_product

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog.json")

class VendorMerchantAgent:
    """
    VENDOR (Merchant Agent):
    Proposes merchant catalog items matching buyer intent.
    When a specific product/category is requested (e.g. Mechanical Keyboard),
    it proposes the best matching item so Judge can evaluate budget feasibility.
    """
    def __init__(self, name: str = "Vendor"):
        self.name = name

    def _load_catalog(self) -> list:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def propose_offer(self, parsed_intent: dict, rejection_history: list = None) -> dict:
        catalog = self._load_catalog()
        category = parsed_intent.get("category", "all")
        max_budget = parsed_intent.get("max_budget", 10000.0)
        keywords = parsed_intent.get("keywords", [])
        raw_prompt = parsed_intent.get("raw_prompt", "").lower()
        rejection_history = rejection_history or []

        # Check if previous loop was rejected due to over_budget
        recent_over_budget = any(r.get("failure_type") == "over_budget" or r.get("feedback") == "over_budget" for r in rejection_history)

        # Step 1: Score every in-stock product based on semantic relevance to prompt
        scored_candidates = []
        for item in catalog:
            if item["stock"] <= 0:
                continue

            score = 0
            # Category match weight (+10 points)
            if category != "all" and item["category"] == category:
                score += 10

            # Keyword / Tag match weight
            item_text = f"{item['name']} {item['category']} {item['description']} {' '.join(item['tags'])}".lower()
            for kw in keywords:
                if kw in item["tags"]:
                    score += 5
                elif kw in item_text:
                    score += 3

            # Exact word match in name
            for kw in keywords:
                if re.search(rf'\b{re.escape(kw)}\b', item["name"].lower()):
                    score += 8

            scored_candidates.append({
                "item": item,
                "score": score
            })

        # Sort all candidates by relevance score
        scored_candidates.sort(key=lambda c: (c["score"], c["item"]["base_price"]), reverse=True)

        # Check if top item score is 0 (query doesn't match existing catalog categories e.g. "bottle", "watch", "shoe")
        top_score = scored_candidates[0]["score"] if scored_candidates else 0

        # Try LLM Vendor Propose
        from llm_engine import llm_vendor_propose_offer, synthesize_dynamic_reasoning
        llm_offer = llm_vendor_propose_offer(raw_prompt, parsed_intent, catalog, rejection_history)

        if llm_offer and llm_offer.get("matched_product_name"):
            price_val = float(llm_offer.get("base_price", max_budget * 0.7))
            selected_base = {
                "id": f"custom_{abs(hash(raw_prompt)) % 10000}",
                "name": llm_offer["matched_product_name"],
                "price": price_val,
                "base_price": price_val,
                "msrp": price_val * 1.25
            }
            upsell_price_val = float(llm_offer.get("upsell_price", 0))
            selected_upsell = {
                "id": f"upsell_{abs(hash(raw_prompt)) % 10000}",
                "name": llm_offer.get("upsell_name"),
                "price": upsell_price_val,
                "pitch": "Complementary accessory for your request."
            } if llm_offer.get("upsell_name") else None
            custom_reasoning = llm_offer.get("reasoning")
        elif top_score == 0 and ("bottle" in raw_prompt or "flask" in raw_prompt or "container" in raw_prompt):
            # Dynamic synthesized product for bottle/flask
            selected_base = {
                "id": "prod_bottle_01",
                "name": "HydroPro Insulated Stainless Steel Thermal Water Bottle (1L)",
                "price": min(1499.0, max_budget * 0.8),
                "base_price": min(1499.0, max_budget * 0.8),
                "msrp": 1999.0
            }
            selected_upsell = {
                "id": "upsell_cleaning_01",
                "name": "Protective Silicone Boot & Bottle Cleaning Brush Set",
                "price": 299.0,
                "pitch": "Protects your bottle base from drops and keeps it sterile."
            } if (max_budget - 1499.0) >= 299.0 else None
            custom_reasoning = None
        else:
            if recent_over_budget:
                fitting = [c for c in scored_candidates if c["item"]["base_price"] <= max_budget]
                if fitting:
                    selected_base = fitting[0]["item"]
                else:
                    selected_base = scored_candidates[0]["item"]
            else:
                selected_base = scored_candidates[0]["item"]
            custom_reasoning = None

        # Step 2: Check long-term memory for past failed upsells
        past_fails = get_past_failures_for_product(selected_base["id"])
        past_failed_upsells = {pf["upsell_id"] for pf in past_fails if pf["failure_type"] == "over_budget"}

        # Step 3: Add Intelligent Upsell only if budget permits and not over_budget
        selected_upsell = None
        if not recent_over_budget and selected_base.get("upsell_options"):
            remaining_budget = max_budget - selected_base["base_price"]
            for upsell in selected_base["upsell_options"]:
                if upsell["id"] in past_failed_upsells:
                    continue  # Long-term memory avoidance!
                if upsell["price"] <= remaining_budget:
                    selected_upsell = upsell
                    break

        total_price = selected_base["base_price"] + (selected_upsell["price"] if selected_upsell else 0)

        offer = {
            "merchant_name": "DealFlow Authorized Merchant",
            "base_product": {
                "id": selected_base["id"],
                "name": selected_base["name"],
                "price": selected_base["base_price"],
                "msrp": selected_base["msrp"]
            },
            "upsell_bundle": {
                "id": selected_upsell["id"],
                "name": selected_upsell["name"],
                "price": selected_upsell["price"],
                "pitch": selected_upsell["pitch"]
            } if selected_upsell else None,
            "total_price": total_price,
            "discount_applied": max(0, selected_base["msrp"] - selected_base["base_price"]),
            "stock_reserved": True
        }

        from llm_engine import synthesize_dynamic_reasoning

        memory_note = f" (Avoiding {len(past_failed_upsells)} past rejected upsells from memory)." if past_failed_upsells else ""
        if custom_reasoning:
            reasoning = f"{custom_reasoning}{memory_note}"
        else:
            base_reasoning = synthesize_dynamic_reasoning("VENDOR", "propose_offer", {"offer": offer})
            reasoning = f"{base_reasoning}{memory_note}"

        return {
            "offer": offer,
            "reasoning": reasoning
        }
