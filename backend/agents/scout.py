import re
import json
import base64
import hmac
import hashlib

class ScoutBuyerAgent:
    """
    SCOUT (Buyer Agent):
    Interprets ANY natural language prompt typed manually by the user.
    Extracts budget ceilings (handles ₹3500, < 2000, 10k, etc.), intent keywords, and target category.
    Generates cryptographically signed SA-JWT constraint tokens.
    """
    def __init__(self, name: str = "Scout"):
        self.name = name

    def parse_intent(self, user_prompt: str) -> dict:
        prompt_lower = user_prompt.lower()
        
        # 1. Budget extraction (handles "10k", "5k", "₹3500", "< 2000", "under 10000")
        budget = 10000.0  # default cap if unspecified
        
        # Check for 'k' notation (e.g. 10k -> 10000, 5.5k -> 5500)
        k_match = re.search(r'(?:under|below|less than|<|budget|around|max)?\s*(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*k\b', prompt_lower)
        if k_match:
            budget = float(k_match.group(1)) * 1000.0
        else:
            # Check standard numeric digits
            numeric_match = re.search(r'(?:under|below|less than|<|budget|around|max)?\s*(?:₹|rs\.?|inr)?\s*(\d{3,6})', prompt_lower)
            if numeric_match:
                budget = float(numeric_match.group(1))

        # 2. Extract semantic keyword tokens (stripping common stop words)
        stop_words = {"under", "below", "less", "than", "budget", "around", "max", "for", "with", "a", "an", "the", "in", "rs", "inr", "k", "and", "or", "looking", "need", "want", "buy"}
        raw_words = re.findall(r'\b[a-z0-9\-\+]+\b', prompt_lower)
        keywords = [w for w in raw_words if w not in stop_words and not w.isdigit()]

        # 3. Dynamic Category Detection based on semantic tokens
        category = "all"
        if any(w in prompt_lower for w in ["shoe", "shoes", "sneaker", "sneakers", "running", "footwear", "walk", "walking"]):
            category = "footwear"
        elif any(w in prompt_lower for w in ["watch", "smartwatch", "wearable", "wearables", "fitness", "tracker", "band"]):
            category = "wearables"
        elif any(w in prompt_lower for w in ["headphone", "headphones", "earbud", "earbuds", "audio", "anc", "sound", "music", "headset"]):
            category = "audio"
        elif any(w in prompt_lower for w in ["mouse", "keyboard", "gaming", "peripheral", "peripherals", "rgb", "typing"]):
            category = "peripherals"
        elif any(w in prompt_lower for w in ["hub", "dock", "usbc", "cable", "accessory", "accessories", "adapter"]):
            category = "accessories"
        elif any(w in prompt_lower for w in ["api", "service", "subscription", "code", "dev", "ai", "software"]):
            category = "services"

        parsed_data = {
            "raw_prompt": user_prompt,
            "max_budget": budget,
            "category": category,
            "keywords": keywords,
            "flexible_budget_leeway": budget * 0.05
        }

        # 4. Generate SA-JWT Token (Scope-Auth Signed Token) holding untampered constraint
        sa_jwt_payload = {
            "iss": "DealFlow_Scout_Authority",
            "constraint_statement": user_prompt,
            "max_budget": budget,
            "category": category,
            "keywords": keywords,
            "iat": 1757075000
        }

        SECRET_KEY = "dealflow_sa_jwt_secret_key_2026"
        header_b64 = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "SA-JWT"}).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(sa_jwt_payload).encode()).decode().rstrip("=")
        signature_b64 = base64.urlsafe_b64encode(hmac.new(SECRET_KEY.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()).decode().rstrip("=")
        sa_jwt_token = f"{header_b64}.{payload_b64}.{signature_b64}"

        from llm_engine import synthesize_dynamic_reasoning
        
        parsed_data["sa_jwt"] = sa_jwt_token

        reasoning = synthesize_dynamic_reasoning("SCOUT", "parse_intent", {"parsed_intent": parsed_data})
        return {
            "parsed_intent": parsed_data,
            "sa_jwt": sa_jwt_token,
            "reasoning": reasoning
        }

    def evaluate_offer(self, offer: dict, intent: dict) -> dict:
        total_price = offer.get("total_price", 0.0)
        max_budget = intent["max_budget"]
        flex_budget = max_budget + intent.get("flexible_budget_leeway", 0.0)

        if total_price > flex_budget:
            return {
                "accepted": False,
                "reason": f"Offer price ₹{total_price:.2f} exceeds buyer budget ceiling of ₹{flex_budget:.2f}.",
                "feedback": "over_budget",
                "counter_budget": max_budget
            }

        return {
            "accepted": True,
            "reason": f"Offer price ₹{total_price:.2f} fits within buyer target budget (₹{max_budget:.2f}).",
            "feedback": "acceptable"
        }
