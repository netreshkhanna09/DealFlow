import uuid
from razorpay_client import razorpay_manager

class TellerPaymentExecutorAgent:
    """
    TELLER (Payment Executor Agent):
    The ONLY agent holding Razorpay API access.
    Creates Order/Payment Link on Razorpay, polls payment status, and manages retries.
    """
    def __init__(self, name: str = "Teller"):
        self.name = name

    def execute_payment(self, negotiation_id: str, offer: dict, simulate_failure: bool = False, retry_count: int = 0) -> dict:
        total_price = offer.get("total_price", 0.0)
        base_name = offer.get("base_product", {}).get("name", "Product")
        receipt_id = f"rcpt_{negotiation_id[:8]}"

        description = f"DealFlow AI Purchase: {base_name}"
        if offer.get("upsell_bundle"):
            description += f" + {offer['upsell_bundle']['name']}"

        # Step 1: Create Razorpay Order & Payment Link
        rzp_order = razorpay_manager.create_order(total_price, receipt=receipt_id, notes={"negotiation_id": negotiation_id})
        rzp_link = razorpay_manager.create_payment_link(total_price, description=description)

        # Step 2: Poll / Verify Payment Status (with simulated failure option)
        verification = razorpay_manager.simulate_payment_verification(rzp_link["payment_link_id"], force_fail=simulate_failure)

        if not verification["success"]:
            reasoning = f"TELLER PAYMENT FAILURE (Attempt {retry_count + 1}): {verification['message']}"
            return {
                "success": False,
                "status": "payment_failed",
                "failure_type": "payment_failed",
                "route_to": "TELLER" if retry_count < 2 else "FALLBACK",
                "order_id": rzp_order.get("order_id"),
                "payment_link": rzp_link.get("short_url"),
                "reasoning": reasoning,
                "retry_count": retry_count + 1
            }

        reasoning = f"TELLER SUCCESS: Generated Razorpay Order ({rzp_order['order_id']}) & Payment Link ({rzp_link['short_url']}). Payment captured via test mode."
        return {
            "success": True,
            "status": "completed",
            "failure_type": None,
            "route_to": "SCRIBE",
            "order_id": rzp_order.get("order_id"),
            "payment_link": rzp_link.get("short_url"),
            "amount": total_price,
            "mode": rzp_order.get("mode"),
            "reasoning": reasoning,
            "retry_count": retry_count
        }
