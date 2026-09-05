# DealFlow — Two-Sided AI Agentic Commerce & Razorpay Gateway

> **Razorpay AI Buildathon — Track 01: AI Growth & Agentic Commerce**

**DealFlow** is a multi-agent negotiation platform where autonomous Buyer and Merchant AI agents negotiate product bundles and prices in real-time, gated by a cryptographically signed Risk Warden and executed via Razorpay payment APIs.

---

## 🌟 Key Features

- **Two-Sided Negotiation Engine**: Pairs a **Buyer Agent (Scout)** optimizing user value against a **Merchant Agent (Vendor)** growing merchant revenue via intelligent upsells and cross-sells.
- **Warden SA-JWT Security Gate**: Encodes buyer constraints into cryptographically signed **SA-JWT tokens** (`Header.Payload.Signature`) to prevent mid-negotiation prompt injection attacks.
- **Judge Critic Referee**: Classifies exact failure reasons (`over_budget`, `irrelevant_upsell`, `scope_mismatch`) and routes dynamically back to the single agent capable of fixing it.
- **Razorpay Integration**: Connects with Razorpay Orders API and Payment Links API for real test-mode payment creation and capture.
- **Long-Term Memory Persistence**: Uses SQLite (`dealflow.db`) to record past failed offers so Vendor never repeats known bad upsells in future buyer sessions.
- **Live Glassmorphic Control Dashboard**: Displays active pipeline node topology, scrolling audit log traces, and payment execution state.

---

## 🤖 Multi-Agent Pipeline Topology

```
User Prompt -> SCOUT (Buyer Agent) -> VENDOR (Merchant Agent) -> JUDGE (Critic Agent)
                                                                       |
                             ┌─────────────────────────────────────────┴──────────┐
                       over_budget / irrelevant_upsell                         acceptable
                             ↓                                                    ↓
                       Re-route VENDOR                                   WARDEN (Risk Gate - SA-JWT Check)
                       (max 3 loops)                                              ↓
                                                                         TELLER (Razorpay Payment Executor)
                                                                                  ↓
                                                                         SCRIBE (SQLite Audit & Receipt)
```

| Agent | Role | Responsibility |
| :--- | :--- | :--- |
| **Scout** | Buyer Agent | Parses intent, budget ceilings, preferences; issues signed SA-JWT tokens. |
| **Vendor** | Merchant Agent | Reads catalog JSON; formulates base matching products + revenue-growing upsells. |
| **Judge** | Critic Referee | Evaluates proposed offer against buyer criteria; routes dynamically based on `failure_type`. |
| **Warden** | Risk Officer | Hard rule-based gate enforcing spend caps, price sanity, and SA-JWT signature verification. Sole VETO authority. |
| **Teller** | Payment Executor | Exclusive keyholder for Razorpay APIs (`Orders API`, `Payment Links API`). |
| **Scribe** | Audit Keeper | Writes timestamped decision trail to SQLite and generates transaction receipts. |

---

## 🚀 Quick Start & Setup

### 1. Prerequisites
- Python 3.9+ installed.

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/dealflow.git
cd dealflow
pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
Create a `.env` file inside `backend/`:
```env
GROQ_API_KEY=your_groq_api_key_here
RAZORPAY_KEY_ID=rzp_test_yourKeyId
RAZORPAY_KEY_SECRET=yourKeySecret
WARDEN_SPEND_CAP=10000.0
```

### 4. Launch Application
```bash
python run.py
```
Open your browser and navigate to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📂 Project Structure

```
dealflow/
├── backend/
│   ├── app.py                # FastAPI server hosting negotiation endpoints
│   ├── orchestrator.py       # LangGraph state machine & dynamic failure-type router
│   ├── database.py           # SQLite audit trail & past deal history storage
│   ├── razorpay_client.py    # Razorpay Orders & Payment Links API integration
│   ├── llm_engine.py         # LLM inference caller (Groq / OpenAI / Gemini)
│   ├── catalog.json          # Agent-readable product catalog with margins & upsells
│   └── agents/               # Scout, Vendor, Judge, Warden, Teller, Scribe agents
├── frontend/
│   ├── index.html            # DealFlow control center dashboard
│   ├── checkout.html         # Hosted Razorpay payment gateway checkout simulator
│   ├── styles.css            # Dark mode glassmorphic UI design system
│   └── app.js                # Live pipeline graph animation & audit log tracer
├── run.py                    # One-click startup script
├── requirements.txt          # Python dependencies
├── .gitignore                # Git ignore configuration
└── README.md                 # Repository documentation
```

---

## 📜 License
Built for **Razorpay AI Buildathon Track 01 (AI Growth & Agentic Commerce)**.
