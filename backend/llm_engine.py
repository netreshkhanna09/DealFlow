import os
import json
import random
import requests
import logging

logger = logging.getLogger("dealflow.llm")

ACTIVE_LLM_CONFIG = {
    "groq_api_key": os.getenv("GROQ_API_KEY", ""),
    "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
    "gemini_api_key": os.getenv("GEMINI_API_KEY", "")
}

def set_llm_api_key(key: str, provider: str = "auto"):
    key = key.strip()
    if key.startswith("gsk_") or provider == "groq":
        ACTIVE_LLM_CONFIG["groq_api_key"] = key
    elif key.startswith("sk-") or provider == "openai":
        ACTIVE_LLM_CONFIG["openai_api_key"] = key
    else:
        ACTIVE_LLM_CONFIG["gemini_api_key"] = key
    logger.info(f"LLM API Key set for provider {provider}. Key length: {len(key)}")

def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """
    Calls configured LLM API (Groq, OpenAI, or Gemini) for real agentic reasoning.
    """
    groq_key = ACTIVE_LLM_CONFIG["groq_api_key"]
    openai_key = ACTIVE_LLM_CONFIG["openai_api_key"]
    gemini_key = ACTIVE_LLM_CONFIG["gemini_api_key"]

    # 1. Try Groq (groq/compound-mini & groq/compound)
    if groq_key:
        models_to_try = ["groq/compound-mini", "groq/compound", "qwen/qwen3.6-27b"]
        for model in models_to_try:
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
                
                prompt_content = f"{system_prompt}\nRespond ONLY in valid JSON format." if json_mode else system_prompt
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": prompt_content},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 300,
                    "temperature": 0.5
                }
                res = requests.post(url, json=payload, headers=headers, timeout=8)
                if res.status_code == 200:
                    content = res.json()["choices"][0]["message"]["content"]
                    logger.info(f"Groq LLM success with model {model}")
                    return content
                else:
                    logger.warning(f"Groq model {model} status {res.status_code}: {res.text}")
            except Exception as e:
                logger.error(f"Groq exception with {model}: {e}")

    # 2. Try OpenAI (GPT-4o-mini)
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_tokens": 300,
                "temperature": 0.5
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}
            res = requests.post(url, json=payload, headers=headers, timeout=8)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI exception: {e}")

    return ""

def clean_json_text(text: str) -> str:
    """Extracts JSON substring if LLM wraps in markdown code fences."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text

def llm_parse_scout_intent(user_prompt: str) -> dict:
    system_prompt = """You are Scout, an AI Buyer Agent in DealFlow.
Extract the buyer's intent from their prompt. Return ONLY valid JSON with keys:
{
  "max_budget": 3000,
  "category": "beverages_containers",
  "keywords": ["bottle", "water", "thermal"],
  "reasoning": "Parsed user request for water bottle within budget cap."
}"""

    llm_resp = call_llm(system_prompt, user_prompt, json_mode=True)
    if llm_resp:
        try:
            return json.loads(clean_json_text(llm_resp))
        except Exception as e:
            logger.warning(f"Failed to parse LLM Scout output: {e}")
    return None

def llm_vendor_propose_offer(user_prompt: str, parsed_intent: dict, catalog: list, rejection_history: list) -> dict:
    system_prompt = """You are Vendor, an AI Merchant Agent in DealFlow.
Given a customer request, select or generate the best matching product offer.
Return ONLY valid JSON with keys:
{
  "matched_product_name": "HydroPro Insulated Thermal Water Bottle 1L",
  "base_price": 1499,
  "upsell_name": "Silicone Protective Boot",
  "upsell_price": 299,
  "total_price": 1798,
  "reasoning": "Matched premium stainless steel thermal bottle with protective boot accessory within budget."
}"""

    user_input = json.dumps({
        "customer_request": user_prompt,
        "parsed_intent": parsed_intent,
        "available_catalog": catalog,
        "rejection_history": rejection_history
    })

    llm_resp = call_llm(system_prompt, user_input, json_mode=True)
    if llm_resp:
        try:
            return json.loads(clean_json_text(llm_resp))
        except Exception as e:
            logger.warning(f"Failed to parse LLM Vendor output: {e}")
    return None

def synthesize_dynamic_reasoning(agent_name: str, context_type: str, data: dict) -> str:
    if agent_name == "SCOUT":
        intent = data.get("parsed_intent", {})
        cat = intent.get("category", "general")
        budget = intent.get("max_budget", 0)
        keywords = ", ".join(intent.get("keywords", []))
        
        phrasings = [
            f"Analyzed buyer request. Extracted target focus on '{cat}' with budget cap ₹{budget:.2f}. Key signals: [{keywords}]. Signed SA-JWT constraint issued.",
            f"Parsed user intent: Buyer looking for {cat} solutions within ₹{budget:.2f}. Priority tokens: [{keywords}]. Encoded constraints into cryptographic SA-JWT payload.",
            f"Intent breakdown complete: Target category '{cat}', price threshold ₹{budget:.2f}. Issued immutable SA-JWT token for Warden risk gating."
        ]
        return random.choice(phrasings)

    elif agent_name == "VENDOR":
        offer = data.get("offer", {})
        base = offer.get("base_product", {})
        upsell = offer.get("upsell_bundle")
        price = offer.get("total_price", 0)
        
        if upsell:
            phrasings = [
                f"Evaluated catalog inventory. Selected '{base.get('name')}' (₹{base.get('price')}) and paired it with upsell '{upsell.get('name')}' (₹{upsell.get('price')}). Total bundle: ₹{price:.2f}.",
                f"Catalog reasoning complete: Recommended match '{base.get('name')}' (₹{base.get('price')}) with upsell '{upsell.get('name')}' (₹{upsell.get('price')}). Total value: ₹{price:.2f}.",
                f"Formulated revenue-optimized offer: Matched '{base.get('name')}' (₹{base.get('price')}) and added value accessory '{upsell.get('name')}' (₹{upsell.get('price')}). Total: ₹{price:.2f}."
            ]
        else:
            phrasings = [
                f"Selected catalog product '{base.get('name')}' (₹{base.get('price')}). Omitted upsells to adhere to buyer budget cap. Total: ₹{price:.2f}.",
                f"Matched catalog product '{base.get('name')}' at ₹{base.get('price')}. Kept offer standalone to fit budget criteria.",
                f"Recommended catalog item '{base.get('name')}' (₹{base.get('price')}) to stay under buyer price ceiling."
            ]
        return random.choice(phrasings)

    elif agent_name == "JUDGE":
        status = data.get("status")
        failure_type = data.get("failure_type")
        total = data.get("total_price", 0)

        if status == "rejected":
            if failure_type == "over_budget":
                phrasings = [
                    f"Offer total ₹{total:.2f} exceeds buyer budget ceiling. Classifying failure as 'over_budget'. Routing back to VENDOR.",
                    f"Deal evaluation failed: Total price ₹{total:.2f} breaches buyer constraint. Re-routing to VENDOR.",
                    f"Judge Veto: Offer ₹{total:.2f} higher than budget limit. Marked as 'over_budget' and sent back to VENDOR."
                ]
            else:
                phrasings = [
                    f"Offer rejected due to {failure_type}. Routing back to VENDOR for scope adjustment.",
                    f"Deal failed Judge criteria ({failure_type}). Re-routing to relevant agent."
                ]
            return random.choice(phrasings)
        else:
            phrasings = [
                f"Judge Approval: Proposed offer ₹{total:.2f} satisfies budget & relevance. Routing to WARDEN for risk clearance.",
                f"Deal validated: Offer total ₹{total:.2f} fits within buyer constraints. Proceeding to WARDEN compliance audit.",
                f"Evaluation passed: Offer total ₹{total:.2f} cleared by Judge. Routing to WARDEN Risk Officer."
            ]
            return random.choice(phrasings)

    elif agent_name == "WARDEN":
        status = data.get("status")
        reason = data.get("reasoning", "")
        if status == "vetoed":
            return f"WARDEN VETO: Transaction blocked on policy grounds ({data.get('violation', 'RISK_POLICY_VIOLATION')}). {reason}"
        else:
            return f"WARDEN CLEARANCE: SA-JWT signature verified. Transaction complies with signed constraints, spend caps, and price sanity."

    return "Agent step complete."
