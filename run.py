import uvicorn
import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

if __name__ == "__main__":
    print("\n" + "="*70)
    print("[DealFlow] Razorpay Agentic Commerce Platform")
    print("Track 01: AI Growth & Agentic Commerce")
    print("Control Center: http://127.0.0.1:8000")
    print("="*70 + "\n")
    
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False, log_level="info")
