import re, time, requests
from typing import Optional
from bs4 import BeautifulSoup

# Strong headers to mimic a real browser
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/127.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}

PRICE_REGEX = re.compile(r"[₹Rs\.]?\s*([0-9][0-9,]*)")

def _clean_price(text: str) -> Optional[int]:
    if not text:
        return None
    m = PRICE_REGEX.search(text)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None

def _get_soup(url: str) -> BeautifulSoup:
    time.sleep(1.0)  # polite delay
    resp = requests.get(url, headers=HEADERS, timeout=25)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")

# ---------- Amazon ----------
def scrape_amazon(url: str) -> Optional[int]:
    soup = _get_soup(url)
    candidates = [
        ("span", {"id": "priceblock_ourprice"}),
        ("span", {"id": "priceblock_dealprice"}),
        ("span", {"id": "priceblock_saleprice"}),
        ("span", {"class": "a-price-whole"}),
        ("span", {"class": "a-offscreen"}),
    ]
    for tag, attrs in candidates:
        el = soup.find(tag, attrs)
        if el:
            price = _clean_price(el.get_text(strip=True))
            if price:
                return price
    container = soup.find("span", class_="a-price")
    if container:
        return _clean_price(container.get_text(strip=True))
    return None

import json
from typing import Optional
from bs4 import BeautifulSoup

def scrape_reliancedigital(url: str) -> Optional[int]:
    """
    Reliance Digital product pages contain a JSON-LD script with "offers": {"price": ...}.
    We'll try that first, then fallback to visible price tags.
    """
    try:
        soup = _get_soup(url)

        # Block detection (Cloudflare / bot protection)
        if "Access Denied" in soup.text or "blocked" in soup.text.lower():
            raise RuntimeError("Reliance Digital blocked this request (403)")

        # --- JSON-LD structured data ---
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string.strip())
            except Exception:
                continue

            # Case: single Product object
            if isinstance(data, dict) and data.get("@type") == "Product":
                offers = data.get("offers")
                if offers and "price" in offers:
                    return int(float(offers["price"]))

            # Case: array of objects
            if isinstance(data, list):
                for obj in data:
                    if obj.get("@type") == "Product" and "offers" in obj:
                        return int(float(obj["offers"]["price"]))

        # --- Fallback: look for visible price elements ---
        selectors = [
            ".pdp__offerPrice",
            ".pdp__finalPrice",
            ".price",  # generic
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                return _clean_price(el.get_text(strip=True))

        return None

    except Exception as e:
        print(f"[error] RelianceDigital scrape failed for {url}: {e}")
        return None
