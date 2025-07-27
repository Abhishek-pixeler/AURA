import requests # type: ignore
from urllib.parse import quote as url_quote
import re
from flask import jsonify, Request # type: ignore
from google.adk.agents import Agent  # type: ignore
from google.adk.tools import google_search  # type: ignore

root_agent = Agent(
    name="tool_agent",
    model="gemini-2.0-flash",
    description="Tool agent",
    instruction="""
    "You are a helpful assistant that analyzes stocks and presents a very short, clear summary.",
    "Use the `google_search` tool to gather the latest and most reliable information about a stock (e.g. ITC, Vedantha lmt. etc).",
    "Refer to trusted financial sources like Google Finance, Screener.in, MoneyControl, or Investopedia.",
    "Your response must be a short note — no more than 6–7 lines.",
    "Only highlight the strongest points about the company: fundamentals, growth potential, recent positive/negative news.",
    "At the end of your response, ask: 'Would you like to know more?' and offer an option to continue.",
    "Always end with this disclaimer: 'Note: Investment in securities are subject to market risks, please carry out your due diligence before investing.'"
    """,
    tools=[google_search],
)


def extract_between_tags(text, tag, class_name=None):
    """Extract content of the first occurrence of a tag with optional class."""
    pattern = f'<{tag}[^>]*'
    if class_name:
        pattern +=   f'class="[^"]*{class_name}[^"]*"[^>]*'
    pattern += f'>(.*?)</{tag}>'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return re.sub('<[^<]+?>', '', match.group(1)).strip()
    return None

def get_moneycontrol_stock_data(company_url):
    """
    Scrapes key stock data from a Moneycontrol stock page without BeautifulSoup.
    Uses regex to extract content.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Bot/1.0)"
    }
    try:
        response = requests.get(company_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"error": "Failed to fetch data"}
    except Exception as e:
        return {"error": str(e)}

    html = response.text
    data = {}

    # --Fetch Current Price
    data["current_price"] = extract_between_tags(html, "div", "inprice1")

    # Fetch P/E Ratio
    pe_match = re.search(r'P\/E[^<]*</div>\s*<div[^>]*class="PA7 b_12"[^>]*>([^<]+)</div>', html)
    if pe_match:
        data["pe_ratio"] = pe_match.group(1).strip()

    #-- Dividend Yield
    dy_match = re.search(r'Dividend Yield[^<]*</div>\s*<div[^>]*class="PA7 b_12"[^>]*>([^<]+)</div>', html)
    if dy_match:
        data["dividend_yield"] = dy_match.group(1).strip()

    return data

def stock_scraper(request: Request):
    """
    Google Cloud Function HTTP entry point.
    Expects JSON payload with {"url": "<moneycontrol_stock_url>"}
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    url = None
    if request_json and "url" in request_json:
        url = request_json["url"]
    elif request_args and "url" in request_args:
        url = request_args["url"]
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    data = get_moneycontrol_stock_data(url)
    return jsonify(data)