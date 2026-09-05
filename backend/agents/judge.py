class JudgeCriticAgent:
    """
    JUDGE (Critic / Negotiation Evaluator):
    Compares Vendor's proposed offer against Scout's parsed constraints.
    Classifies why an offer failed (over_budget, irrelevant_upsell, scope_mismatch)
    and routes directly to the specific agent that can fix it.
    """
    def __init__(self, name: str = "Judge"):
        self.name = name

    def evaluate_deal(self, offer: dict, parsed_intent: dict, scout_evaluation: dict) -> dict:
        total_price = offer.get("total_price", 0.0)
        max_budget = parsed_intent.get("max_budget", 5000.0)
        flex_budget = max_budget + parsed_intent.get("flexible_budget_leeway", 0.0)

        from llm_engine import synthesize_dynamic_reasoning

        # 1. Check over_budget condition
        if total_price > flex_budget:
            reasoning = synthesize_dynamic_reasoning("JUDGE", "evaluate_deal", {"status": "rejected", "failure_type": "over_budget", "total_price": total_price})
            return {
                "status": "rejected",
                "failure_type": "over_budget",
                "route_to": "VENDOR",
                "reasoning": reasoning,
                "feedback_for_agent": f"Re-propose offer within target budget ceiling ₹{max_budget:.2f}."
            }

        # 2. Check upsell relevance if upsell exists
        upsell = offer.get("upsell_bundle")
        if upsell:
            upsell_price = upsell.get("price", 0.0)
            if upsell_price > (max_budget * 0.40):  # Upsell takes up >40% of total budget
                reasoning = synthesize_dynamic_reasoning("JUDGE", "evaluate_deal", {"status": "rejected", "failure_type": "irrelevant_upsell", "total_price": total_price})
                return {
                    "status": "rejected",
                    "failure_type": "irrelevant_upsell",
                    "route_to": "VENDOR",
                    "reasoning": reasoning,
                    "feedback_for_agent": "Select a lighter, lower-cost accessory or drop upsell."
                }

        # 3. Check scope mismatch
        if offer.get("base_product", {}).get("price", 0.0) > flex_budget:
            reasoning = synthesize_dynamic_reasoning("JUDGE", "evaluate_deal", {"status": "rejected", "failure_type": "scope_mismatch", "total_price": total_price})
            return {
                "status": "rejected",
                "failure_type": "scope_mismatch",
                "route_to": "SCOUT",
                "reasoning": reasoning,
                "feedback_for_agent": "Re-evaluate buyer requirements or expand category parameters."
            }

        # Deal is acceptable!
        reasoning = synthesize_dynamic_reasoning("JUDGE", "evaluate_deal", {"status": "approved", "failure_type": None, "total_price": total_price})
        return {
            "status": "approved",
            "failure_type": None,
            "route_to": "WARDEN",
            "reasoning": reasoning,
            "feedback_for_agent": "Proceed to Warden safety checks."
        }
