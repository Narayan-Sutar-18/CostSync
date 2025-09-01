import os
from flask import Flask, jsonify, render_template, request, redirect, url_for
from pymongo import MongoClient
from scraper import run_scraper 

app = Flask(__name__)

# --- MongoDB setup ---
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "prices")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
col = db[MONGO_COLLECTION]          # prices collection
user_choice_col = db["user_choice"] # thresholds + emails

# --- API security key ---
API_SECRET = os.getenv("API_SECRET", "changeme")  # set this securely

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
            "product": d.get("product"),
            "site": d.get("site"),
            "price": d.get("price"),
            "url": d.get("url"),
            "time": d.get("scraped_at")
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
            "product": d.get("product"),
            "site": d.get("site"),
            "price": d.get("price"),
            "url": d.get("url"),
            "time": d.get("scraped_at")
        })
    return jsonify(out)


# 🚀 Secure scraper trigger
@app.route("/api/refresh", methods=["POST"])
def api_refresh():
    provided_key = request.headers.get("X-API-KEY")

    # External caller must provide correct key
    if provided_key is not None and provided_key != API_SECRET:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # Browser/dashboard call without API key → allowed
    try:
        run_scraper()
        return jsonify({"status": "ok", "message": "Scraper run complete"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# 🔹 Form to capture threshold + email
@app.route("/user-choice", methods=["GET", "POST"])
def user_choice():
    if request.method == "POST":
        name = request.form.get("name")
        threshold = int(request.form.get("threshold"))
        amazon = request.form.get("amazon")
        reliance = request.form.get("reliance")
        snapdeal = request.form.get("snapdeal")
        email = request.form.get("email")

        doc = {
            "name": name,
            "threshold": threshold,
            "urls": {
                "Amazon": amazon,
                "RelianceDigital": reliance,
                "Snapdeal": snapdeal
            },
            "email_id": email
        }

        user_choice_col.insert_one(doc)

        # ✅ Redirect back to dashboard after saving
        return redirect(url_for("dashboard"))

    # GET → show the form (card UI in index.html)
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
