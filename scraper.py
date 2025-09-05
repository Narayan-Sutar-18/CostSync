import json, os, smtplib, sys, logging
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Optional
from dotenv import load_dotenv
from pymongo import MongoClient, DESCENDING
from scrapers import scrape_amazon, scrape_snapdeal,scrape_reliance_digital

# Load env
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "price_monitor")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "prices")

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# DB setup
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
col = db[MONGO_COLLECTION]

SCRAPER_MAP = {
    "Amazon": scrape_amazon,
    "Snapdeal": scrape_snapdeal,
    # "Croma": scrape_croma,
    "RelianceDigital": scrape_reliance_digital,
    # "TataCliq": scrape_tatacliq,
    # "ShoppersStop": scrape_shoppersstop
}


def send_email_alert(product: str, site: str, price: int, url: str, threshold: int) -> None:
    if not (EMAIL_USER and EMAIL_PASS and EMAIL_TO):
        logging.warning("Email not configured; skipping")
        return
    body = (f"Price drop alert!\n\n{product} on {site} is now ₹{price} (threshold ₹{threshold}).\n"
            f"Link: {url}\nTime: {datetime.now(timezone.utc).isoformat()}Z")
    msg = MIMEText(body)
    msg["Subject"] = f"Price Alert: {product} @ {site} → ₹{price}"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            if EMAIL_USE_TLS:
                server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        logging.info(f"Email sent for {product} on {site} at ₹{price}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

def _last_price(product: str, site: str) -> Optional[int]:
    doc = col.find_one({"product": product, "site": site}, sort=[("scraped_at", DESCENDING)], projection={"price": 1})
    return doc["price"] if doc else None

# def run_scraper() -> int:
#     try:
#         with open("config.json", "r", encoding="utf-8") as f:
#             config = json.load(f)
#     except Exception as e:
#         logging.error(f"Could not read config.json: {e}")
#         return 1

#     errors = 0
#     for item in config.get("products", []):
#         name = item["name"]
#         threshold = item.get("threshold")
#         urls = item.get("urls", {})

#         for site, url in urls.items():
#             scraper = SCRAPER_MAP.get(site)
#             if not scraper:
#                 logging.warning(f"No scraper implemented for {site}")
#                 continue

#             try:
#                 price = scraper(url)
#             except Exception as e:
#                 logging.error(f"{site} scrape failed for {name}: {e}")
#                 errors += 1
#                 continue

#             if price is None:
#                 logging.warning(f"{site} returned no price for {name}")
#                 continue

#             doc = {
#                 "product": name,
#                 "site": site,
#                 "price": price,
#                 "url": url,
#                 "scraped_at": datetime.now(timezone.utc)
#             }
#             col.insert_one(doc)
#             logging.info(f"{name} | {site} → ₹{price}")

#             if threshold is not None:
#                 last = _last_price(name, site)
#                 if last is not None and last >= threshold and price < threshold:
#                     send_email_alert(name, site, price, url, threshold)

#     return 0 if errors == 0 else 1

def run_scraper() -> int:
    errors = 0

    # Pull from DB instead of config.json
    items = list(db["user_choice"].find())

    for item in items:
        name = item["name"]
        threshold = item.get("threshold")
        urls = item.get("urls", {})

        for site, url in urls.items():
            if not url:
                continue  # skip empty URLs
            scraper = SCRAPER_MAP.get(site)
            if not scraper:
                logging.warning(f"No scraper implemented for {site}")
                continue

            try:
                price = scraper(url)
            except Exception as e:
                logging.error(f"{site} scrape failed for {name}: {e}")
                errors += 1
                continue

            if price is None:
                logging.warning(f"{site} returned no price for {name}")
                continue

            doc = {
                "product": name,
                "site": site,
                "price": price,
                "url": url,
                "scraped_at": datetime.now(timezone.utc)
            }
            col.insert_one(doc)
            logging.info(f"{name} | {site} → ₹{price}")

            if threshold is not None:
                last = _last_price(name, site)
                if last is not None and last >= threshold and price < threshold:
                    send_email_alert(name, site, price, url, threshold)

    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(run_scraper())
