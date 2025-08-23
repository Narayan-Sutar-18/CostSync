import os
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from scraper import run_scraper 

app = Flask(__name__)

# --- MongoDB setup ---
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
col = db[MONGO_COLLECTION]

# --- API security key ---
API_SECRET = os.getenv("API_SECRET", "changeme")  # set this in Render/Relay

# --- Routes ---
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/prices")
def api_prices():
    docs = col.find().sort("scraped_at", -1).limit(50)
    out = []
    for d in docs:
        out.append({
            "product": d["product"],
            "site": d["site"],
            "price": d["price"],
            "url": d["url"],
            "time": d["scraped_at"]
        })
    return jsonify(out)

@app.route("/api/history")
def api_history():
    product = request.args.get("product")
    limit = int(request.args.get("limit", 200))
    q = {"product": product} if product else {}
    docs = col.find(q).sort("scraped_at", -1).limit(limit)
    out = []
    for d in docs:
        out.append({
            "product": d["product"],
            "site": d["site"],
            "price": d["price"],
            "url": d["url"],
            "time": d["scraped_at"]
        })
    return jsonify(out)

# 🚀 NEW: Secure scraper trigger but allow local/dashboard refresh
@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    provided_key = request.headers.get("X-API-KEY")

    # Case 1: Relay or external caller must provide correct key
    if provided_key is not None and provided_key != API_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Case 2: Browser/dashboard calls without API key → allowed
    try:
        run_scraper()   # run your scraper synchronously
        return jsonify({"status": "ok", "message": "Scraper run complete"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
