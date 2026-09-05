import json
from database import log_agent_action, save_negotiation_summary

class ScribeAuditAgent:
    """
    SCRIBE (Audit / Distribution Agent):
    Writes full decision trail to SQLite DB, generates transaction receipt,
    and updates negotiation logs.
    """
    def __init__(self, name: str = "Scribe"):
        self.name = name

    def finalize_negotiation(self, negotiation_id: str, prompt: str, status: str, offer: dict, teller_result: dict, loop_count: int, failure_reason: str = None) -> dict:
        total_price = offer.get("total_price", 0.0) if offer else 0.0
        order_id = teller_result.get("order_id") if teller_result else None
        payment_link = teller_result.get("payment_link") if teller_result else None

        # Save summary to DB
        save_negotiation_summary(
            id=negotiation_id,
            prompt=prompt,
            status=status,
            final_offer=offer,
            final_price=total_price,
            rzp_order=order_id or "",
            rzp_link=payment_link or "",
            failure_reason=failure_reason or "",
            loop_count=loop_count
        )

        receipt = {
            "receipt_id": f"REC-{negotiation_id[:8].upper()}",
            "negotiation_id": negotiation_id,
            "status": status,
            "merchant": offer.get("merchant_name", "DealFlow Merchant") if offer else "DealFlow",
            "items": [
                offer.get("base_product", {}) if offer else {},
                offer.get("upsell_bundle", {}) if offer and offer.get("upsell_bundle") else None
            ],
            "total_amount_inr": total_price,
            "razorpay_order_id": order_id,
            "razorpay_payment_link": payment_link,
            "loops_executed": loop_count
        }

        reasoning = f"SCRIBE AUDIT: Finalized negotiation status '{status}'. Generated Receipt {receipt['receipt_id']} and committed audit trail to SQLite memory."
        return {
            "receipt": receipt,
            "reasoning": reasoning
        }
