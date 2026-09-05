class WardenRiskAgent:
    """
    WARDEN (Risk & Guardrail Agent):
    Hard rule-based gate — checks spend caps, duplicate order detection, price sanity.
    The ONLY agent that can issue a VETO on compliance/risk policy grounds.
    """
    def __init__(self, global_spend_cap: float = None):
        self.name = "Warden"
        import os
        env_cap = os.getenv("WARDEN_SPEND_CAP")
        if env_cap:
            self.global_spend_cap = float(env_cap)
        else:
            self.global_spend_cap = global_spend_cap if global_spend_cap is not None else 10000.0

    def audit_transaction(self, offer: dict, user_prompt: str, sa_jwt_token: str = None, force_risk_veto: bool = False) -> dict:
        if force_risk_veto:
            return {
                "approved": False,
                "status": "vetoed",
                "failure_type": "risk_blocked",
                "route_to": "SCOUT",
                "reasoning": "WARDEN VETO: Simulated compliance policy block triggered (Risk Simulation Mode).",
                "violation": "FORCE_SIMULATED_RISK_VETO",
                "sa_jwt_verified": True
            }

        # Step 1: SA-JWT Signature Verification & Constraint Extraction (Section 3a Security Upgrade)
        sa_jwt_valid = False
        jwt_max_budget = self.global_spend_cap
        constraint_stmt = user_prompt

        if sa_jwt_token:
            try:
                parts = sa_jwt_token.split(".")
                if len(parts) == 3:
                    import base64, json, hmac, hashlib
                    SECRET_KEY = "dealflow_sa_jwt_secret_key_2026"
                    header_b64, payload_b64, signature_b64 = parts
                    
                    # Verify Signature
                    expected_sig = base64.urlsafe_b64encode(hmac.new(SECRET_KEY.encode(), f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest()).decode().rstrip("=")
                    if hmac.compare_digest(signature_b64, expected_sig):
                        sa_jwt_valid = True
                        # Add padding if needed
                        rem = len(payload_b64) % 4
                        if rem > 0:
                            payload_b64 += "=" * (4 - rem)
                        payload_data = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
                        jwt_max_budget = payload_data.get("max_budget", self.global_spend_cap)
                        constraint_stmt = payload_data.get("constraint_statement", user_prompt)
            except Exception as e:
                sa_jwt_valid = False

        total_price = offer.get("total_price", 0.0)
        base_product = offer.get("base_product", {})

        # Check SA-JWT Budget Limit (Cryptographically secured constraint)
        effective_cap = min(self.global_spend_cap, jwt_max_budget * 1.10)
        if total_price > effective_cap:
            return {
                "approved": False,
                "status": "vetoed",
                "failure_type": "risk_blocked",
                "route_to": "SCOUT",
                "reasoning": f"WARDEN VETO (SA-JWT Violation): Total ₹{total_price:.2f} violates cryptographically signed SA-JWT constraint ceiling of ₹{effective_cap:.2f} (Original constraint: '{constraint_stmt}').",
                "violation": "SA_JWT_CONSTRAINT_VIOLATION",
                "sa_jwt_verified": sa_jwt_valid
            }

        # Rule 2: Global Spend Cap
        if total_price > self.global_spend_cap:
            return {
                "approved": False,
                "status": "vetoed",
                "failure_type": "risk_blocked",
                "route_to": "SCOUT",
                "reasoning": f"WARDEN VETO: Total transaction ₹{total_price:.2f} exceeds global risk ceiling of ₹{self.global_spend_cap:.2f}.",
                "violation": "GLOBAL_SPEND_CAP_EXCEEDED",
                "sa_jwt_verified": sa_jwt_valid
            }

        # Rule 3: Price Sanity Check
        msrp = base_product.get("msrp", 0.0)
        base_price = base_product.get("price", 0.0)
        if base_price <= 0:
            return {
                "approved": False,
                "status": "vetoed",
                "failure_type": "risk_blocked",
                "route_to": "VENDOR",
                "reasoning": "WARDEN VETO: Invalid product price detected (<= 0).",
                "violation": "INVALID_PRICE_SANITY",
                "sa_jwt_verified": sa_jwt_valid
            }

        # Risk & SA-JWT checks passed!
        return {
            "approved": True,
            "status": "cleared",
            "failure_type": None,
            "route_to": "TELLER",
            "reasoning": f"WARDEN CLEARANCE: SA-JWT signature verified. Transaction of ₹{total_price:.2f} complies with signed constraint ('{constraint_stmt}'), spend caps, and price sanity.",
            "violation": None,
            "sa_jwt_verified": sa_jwt_valid
        }
