import re, time, requests, json, random
from typing import Optional
from bs4 import BeautifulSoup
import urllib.parse

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

# Enhanced headers with rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

def _get_headers(url: str) -> dict:
    """Generate realistic headers based on the target site"""
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    
    base_headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }
    
    # Site-specific headers
    if "snapdeal" in domain:
        base_headers.update({
            "Referer": "https://www.snapdeal.com/",
            "Origin": "https://www.snapdeal.com",
        })
    elif "tatacliq" in domain:
        base_headers.update({
            "Referer": "https://www.tatacliq.com/",
            "Origin": "https://www.tatacliq.com",
        })
    elif "shoppersstop" in domain:
        base_headers.update({
            "Referer": "https://www.shoppersstop.com/",
            "Origin": "https://www.shoppersstop.com",
        })
    elif "amazon" in domain:
        base_headers.update({
            "Referer": "https://www.amazon.in/",
        })
    
    return base_headers

def _get_soup(url: str, retries: int = 3) -> BeautifulSoup:
    """Enhanced request function with better anti-detection"""
    delay = random.uniform(2, 5)  # Random initial delay
    last_exception = None

    # Create a session for cookie persistence
    session = requests.Session()
    
    for attempt in range(retries):
        try:
            headers = _get_headers(url)
            
            # Add random delay between requests
            if attempt > 0:
                time.sleep(delay)
            
            resp = session.get(
                url,
                headers=headers,
                timeout=30,
                allow_redirects=True,
                verify=True
            )
            
            # Check for common anti-bot responses
            if resp.status_code == 403:
                print(f"403 Forbidden - attempt {attempt + 1}")
                if "blocked" in resp.text.lower() or "captcha" in resp.text.lower():
                    raise requests.exceptions.HTTPError("Blocked by anti-bot system")
            
            resp.raise_for_status()
            
            # Add small delay to mimic human behavior
            time.sleep(random.uniform(1, 3))
            
            return BeautifulSoup(resp.text, "html.parser")
            
        except requests.RequestException as e:
            last_exception = e
            print(f"Request failed (attempt {attempt + 1}): {e}")
            delay *= random.uniform(1.5, 2.5)  # Exponential backoff with jitter
            
            if attempt < retries - 1:
                time.sleep(delay)

    raise last_exception

# ---------- Amazon ----------
def scrape_amazon(url: str) -> Optional[int]:
    try:
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
    except Exception as e:
        print(f"Amazon scraping failed: {e}")
    return None

# ---------- Snapdeal ----------
def scrape_snapdeal(url: str) -> Optional[int]:
    try:
        # Add extra delay for Snapdeal
        time.sleep(random.uniform(2, 4))
        
        soup = _get_soup(url)
        candidates = [
            ("span", {"class": "payBlkBig"}),
            ("span", {"class": "pdp-final-price"}),
            ("span", {"class": "pdp-price"}),
            ("span", {"class": "sd-price"}),
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
    except Exception as e:
        print(f"Snapdeal scraping failed: {e}")
    return None

def scrape_tatacliq(url: str) -> Optional[int]:
    try:
        time.sleep(random.uniform(1, 3))
        
        soup = _get_soup(url)
        candidates = [
            ("span", {"class": "ProductDescription__price"}),
            ("span", {"class": "Price__discounted"}),
            ("span", {"class": "Price__actual"}),
            ("h3", {}),
        ]
        for tag, attrs in candidates:
            el = soup.find(tag, attrs)
            if el:
                price = _clean_price(el.get_text(strip=True))
                if price:
                    return price

        script = soup.find("script", type="application/ld+json")
        if script:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "offers" in data:
                    return _clean_price(data["offers"].get("price"))
            except (json.JSONDecodeError, TypeError):
                pass
    except Exception as e:
        print(f"TataCliq scraping failed: {e}")
    return None

def scrape_shoppersstop(url: str) -> Optional[int]:
    try:
        time.sleep(random.uniform(1, 3))
        
        soup = _get_soup(url)

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and "offers" in data:
                    price = data["offers"].get("price")
                    if price:
                        return _clean_price(str(price))
            except (json.JSONDecodeError, TypeError):
                continue

        candidates = [
            ("span", {"class": "offer-price"}),
            ("span", {"class": "product-price"}),
            ("span", {"class": "price"}),
        ]
        for tag, attrs in candidates:
            el = soup.find(tag, attrs)
            if el:
                price = _clean_price(el.get_text(strip=True))
                if price:
                    return price
    except Exception as e:
        print(f"Shoppers Stop scraping failed: {e}")
    return None

# Utility function to test scrapers
def test_scraper(url: str):
    """Test function to debug scraping issues"""
    try:
        headers = _get_headers(url)
        resp = requests.get(url, headers=headers, timeout=30)
        print(f"Status: {resp.status_code}")
        print(f"Headers: {dict(resp.headers)}")
        if resp.status_code != 200:
            print(f"Response text (first 500 chars): {resp.text[:500]}")
    except Exception as e:
        print(f"Test failed: {e}")