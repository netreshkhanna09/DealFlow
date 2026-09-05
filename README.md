# DealFlow: Multi-Agent Commerce Engine & Razorpay Payment Gateway

**Razorpay AI Buildathon Submission — Track 01: AI Growth & Agentic Commerce**

DealFlow is an enterprise-grade multi-agent commerce framework designed to model autonomous, two-sided transaction protocols. It pairs a Buyer Agent (Scout) representing customer utility against a Merchant Agent (Vendor) optimizing merchant margins through intelligent upsells and cross-sells. 

Every commercial action in DealFlow is explainable, bounded, gated, and cryptographically verified using Scope-Auth JWT (SA-JWT) tokens before execution through official Razorpay payment gateway APIs.

---

## Technical Architecture & Agent Pipeline

### Component Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                 USER INTERFACE                                    |
|                  Fullstack Control Console / REST API Endpoints                   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                            LANGGRAPH ORCHESTRATOR                                 |
|          State Machine, Dynamic Failure Classifier & Bounded Loop Control         |
+-------+--------------------+---------------------+--------------------+-----------+
        |                    |                     |                    |
        v                    v                     v                    v
+---------------+    +---------------+     +---------------+    +---------------+
| SCOUT AGENT   |    | VENDOR AGENT  |     | JUDGE AGENT   |    | WARDEN AGENT  |
| - Intent      |    | - Catalog     |     | - Constraint  |    | - SA-JWT Check|
|   Parsing     |    |   Matching    |     |   Evaluator   |    | - Spend Cap   |
| - SA-JWT      |    | - Margin      |     | - Dynamic     |    |   Enforcement |
|   Signer      |    |   Upselling   |     |   Classifier  |    | - Policy Veto |
+-------+-------+    +-------+-------+     +-------+-------+    +-------+-------+
        |                    |                     |                    |
        +--------------------+---------------------+--------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                            TELLER PAYMENT EXECUTOR                                |
|          Razorpay Test-Mode Orders API & Payment Links API Integration            |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             SCRIBE AUDIT AGENT                                    |
|          SQLite Database Persistence (dealflow.db) & Transaction Receipts         |
+-----------------------------------------------------------------------------------+
```

### Detailed Sequence & Routing Protocol

```
[ User Request ]
       |
       v
[ SCOUT: Intent Parsing & SA-JWT Signing ]
       |
       v
[ VENDOR: Catalog Matching & Upsell Strategy ] <----------------------+
       |                                                               |
       v                                                               |
[ JUDGE: Constraint & Budget Evaluation ]                              |
       |                                                               |
       +---> [ Rejected: over_budget / irrelevant_upsell ] ------------+ (Re-route VENDOR, Loop <= 3)
       |
       +---> [ Approved: acceptable ]
                   |
                   v
[ WARDEN: SA-JWT Signature Audit & Risk Policy Gate ]
       |
       +---> [ Vetoed: risk_blocked / spend_cap_exceeded ] ------------> [ GRACEFUL FALLBACK (Halt Execution) ]
       |
       +---> [ Cleared: risk_passed ]
                   |
                   v
[ TELLER: Razorpay Order Creation & Payment Execution ]
       |
       +---> [ Payment Decline ] --------------------------------------> [ Bounded Retry (Max 2 Attempts) ]
       |
       +---> [ Payment Success ]
                   |
                   v
[ SCRIBE: SQLite Database Commitment & Audit Trail Receipt ]
```

---

## Agent Specifications & Operational Roles

| Agent | Module | Operational Scope | Safety & Compliance Responsibility |
| :--- | :--- | :--- | :--- |
| **Scout** | `backend/agents/scout.py` | Parses natural language intent, extracts budget caps, and dynamically categorizes buyer requirements. | Generates cryptographic SA-JWT tokens (`Header.Payload.Signature`) locking initial buyer constraints. |
| **Vendor** | `backend/agents/vendor.py` | Queries structured JSON catalog (`catalog.json`) to select base products and recommend margin-maximizing upsells. | Queries long-term memory (`past_failures` DB table) to avoid repeating rejected configurations. |
| **Judge** | `backend/agents/judge.py` | Evaluates proposed offers against buyer constraints and classifies failure types at runtime. | Determines precise routing target (`VENDOR` for pricing/upsell fixes; `SCOUT` for requirement scope renegotiation). |
| **Warden** | `backend/agents/warden.py` | Performs compliance checks, spend cap enforcement, and price sanity verification. | Decodes and verifies SA-JWT signature. Has absolute VETO authority; holds zero payment keys. |
| **Teller** | `backend/agents/teller.py` | Manages Razorpay test-mode API transactions (`Orders API`, `Payment Links API`). | Sole holder of Razorpay API keys. Handles bounded payment retry logic (max 2 retries). |
| **Scribe** | `backend/agents/scribe.py` | Generates immutable transaction receipts and commits full decision trails to storage. | Persists structured JSON audit logs to SQLite (`dealflow.db`). |

---

## Security Architecture: SA-JWT Constraint Verification

To protect agentic payment flows from prompt-injection exploits mid-negotiation:

1. **Signed Scope Token Generation**: Scout encodes the initial user prompt and budget cap into an HMAC-signed JWT token payload.
2. **Untampered Constraint Enforcement**: Warden decodes the SA-JWT signature and audits proposed deals against the signed token—not live conversation memory.
3. **Prompt Injection Immunity**: Even if downstream LLM reasoning is manipulated during negotiation, Warden enforces rules against the original cryptographic token.

---

## Repository Structure

```
dealflow/
├── backend/
│   ├── app.py                # FastAPI REST API server
│   ├── orchestrator.py       # State machine & dynamic router
│   ├── database.py           # SQLite database layer
│   ├── razorpay_client.py    # Razorpay API client
│   ├── llm_engine.py         # LLM inference layer (Groq / OpenAI / Gemini)
│   ├── catalog.json          # Structured product catalog
│   └── agents/               # Scout, Vendor, Judge, Warden, Teller, Scribe
├── frontend/
│   ├── index.html            # Dashboard control center
│   ├── checkout.html         # Razorpay gateway checkout simulator
│   ├── styles.css            # Light mode design system
│   └── app.js                # Frontend state & execution tracer
├── run.py                    # Server startup script
├── requirements.txt          # Dependency manifest
└── README.md                 # Technical documentation
```

---

## Quick Start & Installation

### 1. Prerequisites
- Python 3.9 or higher

### 2. Environment Setup
```bash
git clone https://github.com/netreshkhanna09/DealFlow.git
cd DealFlow
pip install -r requirements.txt
```

### 3. Execution
```bash
python run.py
```
Access the application dashboard at `http://127.0.0.1:8000`.

---

## Verification & Failure Case Testing

1. **Over-Budget Re-negotiation Loop**: Input `Mechanical Keyboard under 1500`. Judge detects budget overrun on Loop 1 and re-routes to Vendor to select a fitting item.
2. **Warden Spend Cap Veto**: Input `Enterprise AI Workstation Setup 25000`. Warden flags ₹24,999 offer against ₹10,000 spend cap and issues a `RISK_VETOED` policy block.
3. **Payment Decline Retry**: Send POST request to `/api/negotiate` with `{"simulate_payment_fail": true}` to test Teller's 2-attempt retry cap and graceful fallback messaging.
