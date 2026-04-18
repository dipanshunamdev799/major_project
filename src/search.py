import concurrent.futures
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

from src.config import GOOGLE_API_KEY, GOOGLE_CSE_ID
from src.llm import extract_entities

# Authorized domains from requirements
ALLOWED_DOMAINS = [
    "moneycontrol.com", "economictimes.indiatimes.com", "livemint.com",
    "business-standard.com", "financialexpress.com", "businesstoday.in",
    "ndtvprofit.com", "nseindia.com", "bseindia.com", "pulse.zerodha.com",
    "screener.in", "trendlyne.com", "bloomberg.com", "reuters.com",
    "cnbc.com", "investing.com", "tradingview.com", "marketwatch.com",
    "thebalancemoney.com", "finance.yahoo.com"
]

def search_financial_news(query: str, num_results: int = 5) -> list:
    """Search Google Custom Search API."""
    if not GOOGLE_API_KEY or not GOOGLE_CSE_ID:
        print("Missing Google API credentials")
        return []

    url = "https://www.googleapis.com/customsearch/v1"
    try:
        response = requests.get(
            url,
            params={
                "q": query,
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_CSE_ID,
                "num": min(num_results, 10),
            },
            timeout=15,
        )
        if response.status_code == 200:
            items = response.json().get("items", [])
            filtered_items = []
            for item in items:
                domain = urlparse(item.get("link", "")).netloc.lower()
                if any(allowed in domain for allowed in ALLOWED_DOMAINS):
                    filtered_items.append(item)
            return filtered_items
        print(f"Google API Error: {response.status_code} | {response.text}")
        return []
    except Exception as e:
        print(f"Search error: {e}")
        return []

def fetch_article_content(url: str, session: requests.Session = None) -> str:
    """Fetches the full text content of an article."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36"
        )
    }
    
    domain = urlparse(url).netloc.lower()
    is_allowed = any(allowed in domain for allowed in ALLOWED_DOMAINS)
    if not is_allowed:
        print(f"Skipping unauthorized domain: {domain}")
        return ""
        
    try:
        req_func = session.get if session else requests.get
        response = req_func(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "lxml")
            for junk in soup(["script", "style", "header", "footer", "nav", "aside"]):
                junk.extract()
            text = soup.get_text(separator="\n", strip=True)
            return text.strip()
    except Exception as e:
        print(f"Fetch error for {url}: {e}")
    return ""

def search_and_extract(query: str) -> list:
    """Full pipeline: Search -> Fetch -> Extract entities."""
    results = search_financial_news(query)
    extracted_data = []
    seen_urls = set()

    # Pre-filter URLs
    urls_to_process = []
    for res in results:
        url = res.get("link")
        title = res.get("title", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            urls_to_process.append((url, title))

    if not urls_to_process:
        return extracted_data

    # Process task for ThreadPoolExecutor
    def process_task(item, session):
        url, title = item
        content = fetch_article_content(url, session)
        if content and len(content) > 200:
            truncated_content = content[:15000]
            entities_rel = extract_entities(truncated_content)
            return {
                "url": url,
                "title": title,
                "content": content,
                "graph_data": entities_rel
            }
        return None

    # Use ThreadPoolExecutor to fetch and process in parallel
    with requests.Session() as session:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(process_task, item, session) for item in urls_to_process]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        extracted_data.append(result)
                except Exception as e:
                    print(f"Error processing URL: {e}")
            
    return extracted_data
