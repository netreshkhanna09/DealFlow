import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "dealflow.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table 1: Negotiations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS negotiations (
            id TEXT PRIMARY KEY,
            user_prompt TEXT NOT NULL,
            status TEXT NOT NULL,
            final_offer JSON,
            final_price REAL,
            razorpay_order_id TEXT,
            razorpay_payment_link TEXT,
            failure_reason TEXT,
            loop_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Table 2: Audit Trail Logs (Every Agent Action)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            negotiation_id TEXT NOT NULL,
            step_index INTEGER NOT NULL,
            agent_name TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            reasoning TEXT,
            payload JSON,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (negotiation_id) REFERENCES negotiations (id)
        )
    """)
    
    # Table 3: Long-term Memory - Past Failed Offers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS past_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            upsell_id TEXT,
            failure_type TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def log_agent_action(negotiation_id: str, step_index: int, agent_name: str, action: str, status: str, reasoning: str, payload: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO audit_logs (negotiation_id, step_index, agent_name, action, status, reasoning, payload)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (negotiation_id, step_index, agent_name, action, status, reasoning, json.dumps(payload)))
    conn.commit()
    conn.close()

def record_past_failure(product_id: str, upsell_id: str, failure_type: str, reason: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO past_failures (product_id, upsell_id, failure_type, reason)
        VALUES (?, ?, ?, ?)
    """, (product_id, upsell_id or "", failure_type, reason))
    conn.commit()
    conn.close()

def get_past_failures_for_product(product_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT upsell_id, failure_type, reason FROM past_failures WHERE product_id = ?", (product_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def save_negotiation_summary(id: str, prompt: str, status: str, final_offer: dict, final_price: float, rzp_order: str, rzp_link: str, failure_reason: str, loop_count: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO negotiations 
        (id, user_prompt, status, final_offer, final_price, razorpay_order_id, razorpay_payment_link, failure_reason, loop_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (id, prompt, status, json.dumps(final_offer or {}), final_price, rzp_order, rzp_link, failure_reason, loop_count))
    conn.commit()
    conn.close()

def fetch_recent_negotiations(limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM negotiations ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        item = dict(r)
        if item["final_offer"]:
            try:
                item["final_offer"] = json.loads(item["final_offer"])
            except:
                pass
        result.append(item)
    return result

def fetch_audit_trail(negotiation_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs WHERE negotiation_id = ? ORDER BY step_index ASC", (negotiation_id,))
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        item = dict(r)
        if item["payload"]:
            try:
                item["payload"] = json.loads(item["payload"])
            except:
                pass
        result.append(item)
    return result

# Initialize on import
init_db()
