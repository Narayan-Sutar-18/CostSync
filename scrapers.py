import re, time, requests, json
from typing import Optional
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Create UserAgent instance
ua = UserAgent()

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
    """
    Fetch page with random User-Agent and polite delay.
    """
    time.sleep(1.0)  # polite delay
    headers = {
        "User-Agent": ua.random,  # rotate UA
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }
    resp = requests.get(url, headers=headers, timeout=25)
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

# ---------- Reliance Digital ----------
def scrape_reliancedigital(url: str) -> Optional[int]:
    """
    Reliance Digital product pages contain a JSON-LD script with "offers": {"price": ...}
    """
    soup = _get_soup(url)

    # Find all <script type="application/ld+json">
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string.strip())
        except Exception:
            continue

        # Case: single Product object
        if isinstance(data, dict) and data.get("@type") == "Product":
            offers = data.get("offers")
            if offers and "price" in offers:
                try:
                    return int(float(offers["price"]))
                except Exception:
                    pass

        # Case: array of objects
        if isinstance(data, list):
            for obj in data:
                if obj.get("@type") == "Product" and "offers" in obj:
                    try:
                        return int(float(obj["offers"]["price"]))
                    except Exception:
                        pass

    # Fallback: nothing found
    return None
