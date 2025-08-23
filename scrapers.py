import re, time, requests, json
from typing import Optional
from bs4 import BeautifulSoup

# Regex to clean price values
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

# Improved _get_soup with stronger headers & retry logic
def _get_soup(url: str, retries: int = 3) -> BeautifulSoup:
    delay = 1.0
    last_exception = None

    for attempt in range(retries):
        try:
            resp = requests.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/127.0.0.0 Safari/537.36"
                    ),
                    "Accept": (
                        "text/html,application/xhtml+xml,application/xml;q=0.9,"
                        "image/avif,image/webp,*/*;q=0.8"
                    ),
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Referer": "https://www.snapdeal.com/",
                    "Upgrade-Insecure-Requests": "1",
                    "DNT": "1",
                    "Connection": "keep-alive",
                },
                timeout=25,
            )
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "html.parser")
        except requests.RequestException as e:
            last_exception = e
            time.sleep(delay)
            delay *= 2  # exponential backoff

    raise last_exception

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

# ---------- Snapdeal ----------
def scrape_snapdeal(url: str) -> Optional[int]:
    soup = _get_soup(url)
    candidates = [
        ("span", {"class": "payBlkBig"}),
        ("span", {"class": "pdp-final-price"}),
        ("span", {"class": "pdp-price"}),
        ("span", {"class": "sd-price "}),
    ]
    for tag, attrs in candidates:
        el = soup.find(tag, attrs)
        if el:
            price = _clean_price(el.get_text(strip=True))
            if price:
                return price

    meta_price = soup.find("meta", {"itemprop": "price"})
    if meta_price and meta_price.get("content"):
        return _clean_price(meta_price["content"])

    script = soup.find("script", type="application/ld+json")
    if script:
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and "offers" in data:
                return _clean_price(data["offers"].get("price"))
        except (json.JSONDecodeError, TypeError):
            pass

    return None
