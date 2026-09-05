import os
import requests
import uuid
import logging

logger = logging.getLogger("dealflow.razorpay")

class RazorpayClientManager:
    def __init__(self, key_id: str = None, key_secret: str = None):
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID", "rzp_test_mockKey123")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET", "mockSecret456")
        self.is_real_api = self.key_id.startswith("rzp_test_") and not "mockKey" in self.key_id

    def create_order(self, amount_in_inr: float, receipt: str, notes: dict = None) -> dict:
        """
        Creates an Order on Razorpay API or generates a test-mode order payload.
        Amount must be converted to paise (1 INR = 100 paise).
        """
        amount_paise = int(amount_in_inr * 100)
        
        if self.is_real_api:
            try:
                url = "https://api.razorpay.com/v1/orders"
                payload = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt,
                    "notes": notes or {}
                }
                res = requests.post(url, json=payload, auth=(self.key_id, self.key_secret), timeout=10)
                if res.status_code == 200 or res.status_code == 201:
                    data = res.json()
                    return {
                        "status": "created",
                        "order_id": data.get("id"),
                        "amount": data.get("amount") / 100,
                        "currency": data.get("currency"),
                        "receipt": data.get("receipt"),
                        "mode": "live_razorpay_test"
                    }
                else:
                    logger.warning(f"Razorpay API error: {res.status_code} {res.text}")
            except Exception as e:
                logger.error(f"Razorpay API exception: {e}")

        # Fallback / Test Mode Execution Payload
        mock_id = f"order_rzp_{uuid.uuid4().hex[:10]}"
        return {
            "status": "created",
            "order_id": mock_id,
            "amount": amount_in_inr,
            "currency": "INR",
            "receipt": receipt,
            "mode": "test_mode_simulated"
        }

    def create_payment_link(self, amount_in_inr: float, description: str, customer_name: str = "AI Buyer Agent") -> dict:
        """
        Generates a Razorpay Payment Link for the negotiated deal.
        """
        amount_paise = int(amount_in_inr * 100)
        
        if self.is_real_api:
            try:
                url = "https://api.razorpay.com/v1/payment_links"
                payload = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "accept_partial": False,
                    "description": description,
                    "customer": {
                        "name": customer_name,
                        "email": "buyer.agent@dealflow.ai",
                        "contact": "+919999999999"
                    },
                    "notify": {"email": False, "sms": False},
                    "reminder_enable": False
                }
                res = requests.post(url, json=payload, auth=(self.key_id, self.key_secret), timeout=10)
                if res.status_code in (200, 201):
                    data = res.json()
                    return {
                        "status": "created",
                        "payment_link_id": data.get("id"),
                        "short_url": data.get("short_url"),
                        "amount": amount_in_inr,
                        "mode": "live_razorpay_test"
                    }
            except Exception as e:
                logger.error(f"Razorpay Payment Link exception: {e}")

        # Simulated link pointing to hosted local Razorpay test checkout page
        link_id = f"plink_{uuid.uuid4().hex[:10]}"
        return {
            "status": "created",
            "payment_link_id": link_id,
            "short_url": f"/checkout.html?link_id={link_id}&amount={amount_in_inr}&desc={requests.utils.quote(description)}",
            "amount": amount_in_inr,
            "mode": "test_mode_simulated"
        }

    def simulate_payment_verification(self, payment_link_id: str, force_fail: bool = False) -> dict:
        """
        Simulates payment status verification.
        Supports deliberate failure simulation for hackathon demo.
        """
        if force_fail:
            return {
                "success": False,
                "status": "failed",
                "error_code": "PAYMENT_DECLINED_INSUFFICIENT_FUNDS",
                "message": "Transaction declined by issuing bank during test authorization."
            }
        
        return {
            "success": True,
            "status": "captured",
            "payment_id": f"pay_{uuid.uuid4().hex[:10]}",
            "message": "Payment captured successfully via Razorpay test mode."
        }

# Shared Singleton
razorpay_manager = RazorpayClientManager()
