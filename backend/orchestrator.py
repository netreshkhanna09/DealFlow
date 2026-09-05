import uuid
import time
import logging
from database import log_agent_action, record_past_failure, fetch_audit_trail
from agents.scout import ScoutBuyerAgent
from agents.vendor import VendorMerchantAgent
from agents.judge import JudgeCriticAgent
from agents.warden import WardenRiskAgent
from agents.teller import TellerPaymentExecutorAgent
from agents.scribe import ScribeAuditAgent

logger = logging.getLogger("dealflow.orchestrator")

class DealFlowOrchestrator:
    """
    DealFlow Multi-Agent Orchestrator:
    Executes dynamic state machine routing between Scout, Vendor, Judge, Warden, Teller, and Scribe.
    Enforces loop caps, dynamic failure-type routing, and long-term memory updates.
    """
    def __init__(self):
        self.scout = ScoutBuyerAgent()
        self.vendor = VendorMerchantAgent()
        self.judge = JudgeCriticAgent()
        self.warden = WardenRiskAgent()
        self.teller = TellerPaymentExecutorAgent()
        self.scribe = ScribeAuditAgent()

    def run_negotiation(self, user_prompt: str, simulate_risk_veto: bool = False, simulate_payment_fail: bool = False) -> dict:
        negotiation_id = f"deal_{uuid.uuid4().hex[:8]}"
        step_index = 1
        loop_count = 0
        max_loops = 3
        rejection_history = []
        
        current_state = {
            "negotiation_id": negotiation_id,
            "user_prompt": user_prompt,
            "parsed_intent": None,
            "current_offer": None,
            "judge_result": None,
            "warden_result": None,
            "teller_result": None,
            "status": "PROCESSING",
            "failure_type": None,
            "loop_count": 0,
            "history": []
        }

        # Step 1: SCOUT Agent (Parse Intent & Issue SA-JWT)
        scout_res = self.scout.parse_intent(user_prompt)
        current_state["parsed_intent"] = scout_res["parsed_intent"]
        current_state["sa_jwt"] = scout_res.get("sa_jwt")
        
        log_agent_action(
            negotiation_id=negotiation_id,
            step_index=step_index,
            agent_name="SCOUT",
            action="parse_intent",
            status="success",
            reasoning=scout_res["reasoning"],
            payload=scout_res["parsed_intent"]
        )
        step_index += 1

        # Negotiation Loop
        target_agent = "VENDOR"
        
        while loop_count < max_loops:
            current_state["loop_count"] = loop_count

            if target_agent == "VENDOR":
                # VENDOR Agent (Propose Offer)
                vendor_res = self.vendor.propose_offer(current_state["parsed_intent"], rejection_history)
                current_state["current_offer"] = vendor_res["offer"]

                log_agent_action(
                    negotiation_id=negotiation_id,
                    step_index=step_index,
                    agent_name="VENDOR",
                    action="propose_offer",
                    status="success",
                    reasoning=vendor_res["reasoning"],
                    payload=vendor_res["offer"]
                )
                step_index += 1
                target_agent = "JUDGE"

            elif target_agent == "JUDGE":
                # SCOUT & JUDGE Agent (Evaluate Offer)
                scout_eval = self.scout.evaluate_offer(current_state["current_offer"], current_state["parsed_intent"])
                judge_res = self.judge.evaluate_deal(current_state["current_offer"], current_state["parsed_intent"], scout_eval)
                current_state["judge_result"] = judge_res

                log_agent_action(
                    negotiation_id=negotiation_id,
                    step_index=step_index,
                    agent_name="JUDGE",
                    action="evaluate_deal",
                    status=judge_res["status"],
                    reasoning=judge_res["reasoning"],
                    payload=judge_res
                )
                step_index += 1

                if judge_res["status"] == "rejected":
                    # Record in Long-term Memory
                    base_id = current_state["current_offer"]["base_product"]["id"]
                    upsell_id = current_state["current_offer"].get("upsell_bundle", {}).get("id") if current_state["current_offer"].get("upsell_bundle") else None
                    record_past_failure(base_id, upsell_id, judge_res["failure_type"], judge_res["reasoning"])

                    rejection_history.append(judge_res)
                    loop_count += 1

                    if loop_count >= max_loops:
                        current_state["status"] = "FAILED_LOOP_CAP_EXCEEDED"
                        current_state["failure_type"] = judge_res["failure_type"]
                        break
                    
                    target_agent = judge_res["route_to"]
                else:
                    target_agent = "WARDEN"

            elif target_agent == "SCOUT":
                # Re-parse or adjust SCOUT intent
                scout_res = self.scout.parse_intent(user_prompt)
                log_agent_action(
                    negotiation_id=negotiation_id,
                    step_index=step_index,
                    agent_name="SCOUT",
                    action="renegotiate_scope",
                    status="success",
                    reasoning="Scout re-adjusting intent based on Judge/Warden feedback.",
                    payload=scout_res["parsed_intent"]
                )
                step_index += 1
                target_agent = "VENDOR"

            elif target_agent == "WARDEN":
                # WARDEN Agent (Risk, Spend Cap Gate & SA-JWT Constraint Check)
                sa_jwt_token = current_state.get("sa_jwt")
                warden_res = self.warden.audit_transaction(
                    offer=current_state["current_offer"],
                    user_prompt=user_prompt,
                    sa_jwt_token=sa_jwt_token,
                    force_risk_veto=simulate_risk_veto
                )
                current_state["warden_result"] = warden_res

                log_agent_action(
                    negotiation_id=negotiation_id,
                    step_index=step_index,
                    agent_name="WARDEN",
                    action="risk_audit",
                    status=warden_res["status"],
                    reasoning=warden_res["reasoning"],
                    payload=warden_res
                )
                step_index += 1

                if not warden_res["approved"]:
                    current_state["status"] = "RISK_VETOED"
                    current_state["failure_type"] = warden_res["failure_type"]
                    # Graceful termination on Risk Veto
                    break
                else:
                    target_agent = "TELLER"

            elif target_agent == "TELLER":
                # TELLER Agent (Payment Execution via Razorpay)
                teller_res = self.teller.execute_payment(
                    negotiation_id=negotiation_id,
                    offer=current_state["current_offer"],
                    simulate_failure=simulate_payment_fail,
                    retry_count=0
                )
                current_state["teller_result"] = teller_res

                log_agent_action(
                    negotiation_id=negotiation_id,
                    step_index=step_index,
                    agent_name="TELLER",
                    action="execute_payment",
                    status=teller_res["status"],
                    reasoning=teller_res["reasoning"],
                    payload=teller_res
                )
                step_index += 1

                if teller_res["success"]:
                    current_state["status"] = "SUCCESS"
                    target_agent = "SCRIBE"
                else:
                    current_state["status"] = "PAYMENT_FAILED"
                    current_state["failure_type"] = teller_res["failure_type"]
                    break

            elif target_agent == "SCRIBE":
                # SCRIBE Agent (Audit Logging & Receipt)
                scribe_res = self.scribe.finalize_negotiation(
                    negotiation_id=negotiation_id,
                    prompt=user_prompt,
                    status="SUCCESS",
                    offer=current_state["current_offer"],
                    teller_result=current_state["teller_result"],
                    loop_count=loop_count
                )
                current_state["scribe_result"] = scribe_res

                log_agent_action(
                    negotiation_id=negotiation_id,
                    step_index=step_index,
                    agent_name="SCRIBE",
                    action="finalize_audit",
                    status="success",
                    reasoning=scribe_res["reasoning"],
                    payload=scribe_res["receipt"]
                )
                break

        # Handle Graceful Fallback if negotiation ended without success
        if current_state["status"] != "SUCCESS":
            fallback_message = self._generate_graceful_fallback(current_state)
            current_state["fallback_message"] = fallback_message
            
            self.scribe.finalize_negotiation(
                negotiation_id=negotiation_id,
                prompt=user_prompt,
                status=current_state["status"],
                offer=current_state["current_offer"],
                teller_result=current_state["teller_result"],
                loop_count=loop_count,
                failure_reason=fallback_message
            )

        # Retrieve full audit trail logs
        current_state["audit_trail"] = fetch_audit_trail(negotiation_id)
        return current_state

    def _generate_graceful_fallback(self, state: dict) -> str:
        status = state.get("status")
        failure_type = state.get("failure_type")

        if status == "RISK_VETOED":
            return "Negotiation safely paused by Warden (Risk Agent): Transaction exceeded spend cap or triggered fraud prevention rules. No money was charged."
        elif status == "PAYMENT_FAILED":
            return "Payment authorization failed after maximum retries on Razorpay test mode. The deal was saved in your draft history so you can retry with another payment method."
        elif status == "FAILED_LOOP_CAP_EXCEEDED":
            return f"Deal negotiation paused after 3 dynamic iterations (Reason: {failure_type}). Merchant offers could not strictly satisfy all buyer budget constraints without sacrificing product quality."
        else:
            return "Negotiation incomplete. System state preserved."

# Shared Orchestrator Instance
orchestrator = DealFlowOrchestrator()
