"""
Company Lookup: finds a shop/company's address and candidate contact email(s)
so the consumer doesn't have to type them in manually.

This module ONLY searches and returns information — it never sends anything.
Sending still requires the separate, explicitly-confirmed delivery_node step.

Search is done via Tavily's official remote MCP server (a real third-party
MCP integration, not scraping): https://mcp.tavily.com/mcp/
  - tavily-search: finds candidate pages (official site + a dedicated contact/
    support query, since the official homepage often doesn't list an email or
    address directly, but the "Contact Us" page usually does)
  - tavily-extract: pulls structured content (incl. emails/address text) from
    several of those pages at once (advanced depth, for fuller content)

Tavily's MCP server is accessed asynchronously (langchain-mcp-adapters'
MultiServerMCPClient uses async/await). Since the rest of this LangGraph app
is synchronous, this module wraps the async Tavily calls with asyncio.run()
so the calling node (a plain sync function) doesn't need to change.

Address resolution: we first try to lift an address straight out of the
extracted page text (companies almost always print their real registered/
head-office address on their contact page — far more accurate than a
geocoder guessing from a business name). Nominatim (free, no API key) is
used only as a fallback, and to turn whatever address text we have into
lat/lng for the map link.

Results are always presented to the user as candidates to review/edit —
never auto-filled and sent. This keeps the human-in-the-loop guarantee that
the delivery node already enforces.
"""

import asyncio
import re
import requests

from config import DEFAULT_CITY, TAVILY_API_KEY

_HEADERS = {"User-Agent": "HaqDar-ConsumerRightsApp/1.0 (student capstone project)"}

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


_NON_EMAIL_SUFFIXES = (
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".css", ".js", ".pdf",
)


_EMAIL_DOMAIN_BLOCKLIST = (
    "sentry.io", "wixpress.com", "godaddy.com", "schema.org", "w3.org",
    "example.com", "yourdomain.com", "domain.com", "godaddy.io", "cloudflare.com",
    "google.com", "googleapis.com", "gstatic.com",
)


_LOW_VALUE_DOMAINS = (
    "facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com",
    "youtube.com", "tiktok.com", "pinterest.com", "wikipedia.org", "wikimedia.org",
    "yelp.com", "yellowpages.com",
)


_CONTACT_URL_HINTS = (
    "contact", "support", "help", "about", "customer-service", "customer_service",
    "reach-us", "reach_us", "get-in-touch", "feedback", "complaint",
)


def _prioritize_contact_urls(urls: list) -> list:
    """Contact/support/help pages are far more likely to list a public email
    than a homepage or product listing page — extract those first."""
    contact_like = [u for u in urls if any(h in u.lower() for h in _CONTACT_URL_HINTS)]
    others = [u for u in urls if u not in contact_like]
    return contact_like + others


_ADDRESS_HINTS = (
    "road", "street", "block", "phase", "industrial", "estate", "avenue",
    "sector", "plot", "s.i.t.e", "site area", "korangi", "gulshan", "dha",
    "shahrah", "shara-e", "shahra-e", "north nazimabad", "f.b. area", "f.b area",
    "gulberg", "model town", "chowk", "bazar", "bazaar",
    "colony", "township", "housing society", "main ", "near ", "opposite ",
)

# Islamabad/Lahore-style sector codes (e.g. "F-7", "G-11", "E-11/2") need a real
# regex, not bare substring hints — plain "f-"/"e-"/"g-"/"i-" checks (the old
# approach) also match inside random hex/UUID strings and filenames, which is
# what let a scraped image URL get mistaken for an address in the first place.
_SECTOR_CODE_RE = re.compile(r"\b[a-iA-I]-\d{1,3}(?:/\d{1,2})?\b")

# Anything that looks like a URL, a markdown link/image, or a filename with an
# image/asset extension is definitely not a street address — reject these
# candidate chunks outright before scoring, regardless of hint-word overlap.
_NON_ADDRESS_RE = re.compile(
    r"https?://|www\.|!\[.*?\]\(|\[.*?\]\(|\.(?:png|jpe?g|gif|svg|webp|ico|css|js|pdf)\b",
    re.IGNORECASE,
)

_PK_CITIES = (
    "karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "multan",
    "peshawar", "quetta", "hyderabad", "sialkot", "gujranwala", "sukkur",
)

_TAVILY_MCP_URL = f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"


def _is_low_value_url(url: str) -> bool:
    url_l = url.lower()
    return any(domain in url_l for domain in _LOW_VALUE_DOMAINS)


def _clean_emails(raw_text: str, preferred_domain: str = "") -> list:
    """Extract plausible email addresses from raw page text, filtering out
    asset filenames and known non-contact domains. If we know the company's
    own website domain, emails on that domain are sorted first."""
    found = set(_EMAIL_RE.findall(raw_text))

    cleaned = []
    for email in found:
        email_l = email.lower()
        if any(email_l.endswith(suf) for suf in _NON_EMAIL_SUFFIXES):
            continue
        if any(domain in email_l for domain in _EMAIL_DOMAIN_BLOCKLIST):
            continue
        cleaned.append(email)

    if preferred_domain:
        preferred_domain_l = preferred_domain.lower()
        cleaned.sort(key=lambda e: 0 if preferred_domain_l in e.lower() else 1)

    return cleaned


def _extract_address_snippet(raw_text: str) -> str:
    """Best-effort: find a line/sentence in the extracted page text that reads
    like a real Pakistani street address, rather than trusting a geocoder to
    guess one from just the company name."""
    if not raw_text:
        return ""

    candidates = re.split(r"[\n\r|\u2022]+|(?<=[.!?])\s{2,}", raw_text)

    scored = []
    for chunk in candidates:
        chunk = chunk.strip(" -\t")
        if not (15 <= len(chunk) <= 220):
            continue
        if _NON_ADDRESS_RE.search(chunk):
            continue
        chunk_l = chunk.lower()
        has_city = any(city in chunk_l for city in _PK_CITIES)
        hint_hits = sum(1 for hint in _ADDRESS_HINTS if hint in chunk_l)
        if _SECTOR_CODE_RE.search(chunk):
            hint_hits += 1
        if has_city and hint_hits >= 1:
            scored.append((hint_hits + 2, chunk))
        elif hint_hits >= 2:
            scored.append((hint_hits, chunk))

    if not scored:
        return ""

    scored.sort(key=lambda pair: -pair[0])
    return scored[0][1]


def _parse_mcp_tool_result(raw_result):
    """
    langchain-mcp-adapters wraps a tool's actual JSON payload inside MCP
    content blocks — the result comes back as a LIST of blocks like
    [{"type": "text", "text": "<json string>"}], not as the parsed JSON
    directly. This was the actual bug causing zero results to ever be found:
    the old code checked `isinstance(search_result, dict)` / treated list
    items as already being result dicts with a "url" key, but each item is
    really {"type": "text", "text": "..."} — so r.get("url") was always None
    and every result got silently skipped.

    This helper unwraps that shape and returns the parsed inner JSON (dict),
    falling back gracefully for any other shape we might encounter.
    """
    import json

    if isinstance(raw_result, dict):
        return raw_result

    if isinstance(raw_result, str):
        try:
            return json.loads(raw_result)
        except (json.JSONDecodeError, TypeError):
            return {}

    if isinstance(raw_result, list):
        for block in raw_result:
            if isinstance(block, dict) and block.get("type") == "text" and "text" in block:
                try:
                    return json.loads(block["text"])
                except (json.JSONDecodeError, TypeError):
                    continue
            elif isinstance(block, dict) and "url" in block:
                
                return {"results": raw_result}
        return {}

    return {}


async def _tavily_search_and_extract(company_name: str, city: str) -> dict:
    """
    Async call into Tavily's real remote MCP server via langchain-mcp-adapters.

    Runs two searches (general official-site search, plus a dedicated
    "contact us" search — the homepage rarely has the email/address, the
    contact page usually does), then extracts several of the top, non-social
    pages in one batched tavily-extract call.

    Returns {"website": str|None, "raw_text": str}.
    """
    from langchain_mcp_adapters.client import MultiServerMCPClient

    client = MultiServerMCPClient(
        {
            "tavily": {
                "transport": "streamable_http",
                "url": _TAVILY_MCP_URL,
            }
        }
    )
    tools = await client.get_tools()
    tool_map = {t.name: t for t in tools}

    search_tool = tool_map.get("tavily_search") or tool_map.get("tavily-search")
    extract_tool = tool_map.get("tavily_extract") or tool_map.get("tavily-extract")

    if not search_tool:
        return {"website": None, "raw_text": ""}

    queries = [
        f"{company_name} {city} Pakistan official website",
        f"{company_name} Pakistan contact us email address head office",
        f"{company_name} Pakistan customer support email",
        f"{company_name} Pakistan help center contact page",
    ]

    urls_in_order = []
    seen_urls = set()
    for query in queries:
        search_result = await search_tool.ainvoke(
            {"query": query, "search_depth": "advanced", "max_results": 8}
        )
        parsed = _parse_mcp_tool_result(search_result)
        results = parsed.get("results", []) if isinstance(parsed, dict) else []

        for r in results:
            if not isinstance(r, dict):
                continue
            url = r.get("url")
            if not url or url in seen_urls:
                continue
            if _is_low_value_url(url):
                continue
            seen_urls.add(url)
            urls_in_order.append(url)

    website = urls_in_order[0] if urls_in_order else None

    raw_text = ""
    if urls_in_order and extract_tool:
        # Prioritize contact/support/help pages — they're far more likely to
        # list a public email than the homepage — and pull more pages overall
        # (was capped at 4; widened to 8) so a miss on one page doesn't sink
        # the whole lookup.
        extract_urls = _prioritize_contact_urls(urls_in_order)[:8]
        extract_result = await extract_tool.ainvoke(
            {"urls": extract_urls, "extract_depth": "advanced"}
        )
        parsed_extract = _parse_mcp_tool_result(extract_result)
        pages = parsed_extract.get("results", []) if isinstance(parsed_extract, dict) else []
        raw_text = "\n".join(
            p.get("raw_content", "") for p in pages if isinstance(p, dict) and p.get("raw_content")
        )

    return {"website": website, "raw_text": raw_text}


def _search_company_via_tavily(company_name: str, city: str) -> dict:
    """
    Sync wrapper around the async Tavily MCP call, so the LangGraph node
    calling this stays a plain synchronous function.
    """
    if not TAVILY_API_KEY:
        return {"website": None, "raw_text": "", "error": "Tavily API key not configured (set TAVILY_API_KEY in .env)."}

    try:
        return asyncio.run(_tavily_search_and_extract(company_name, city))
    except Exception as e:
        return {"website": None, "raw_text": "", "error": str(e)}


def _geocode(query: str) -> dict:
    """Geocode a free-text query (address text, or as a last resort the
    company name) via Nominatim (free, no API key)."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}

    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=6)
        resp.raise_for_status()
        results = resp.json()
    except Exception as e:
        return {"found": False, "reason": str(e)}

    if not results:
        return {"found": False, "reason": "no matching address found"}

    place = results[0]
    return {
        "found": True,
        "address": place.get("display_name"),
        "lat": float(place["lat"]),
        "lng": float(place["lon"]),
    }


def _find_address(company_name: str, city: str, page_text: str) -> dict:
    """
    Resolve a company's address, preferring text pulled straight from its own
    website (much more accurate than geocoding a business name) and falling
    back to Nominatim only if nothing usable was found on the page.
    """
    snippet = _extract_address_snippet(page_text)
    if snippet:
        
        geo = _geocode(snippet)
        return {
            "found": True,
            "address": snippet,
            "source": "company_website",
            "lat": geo.get("lat"),
            "lng": geo.get("lng"),
        }

    
    geo = _geocode(f"{company_name}, {city}, Pakistan")
    if geo.get("found"):
        geo["source"] = "geocoder"
        return geo

    geo = _geocode(f"{company_name}, Pakistan")
    if geo.get("found"):
        geo["source"] = "geocoder"
        return geo

    return {"found": False, "reason": "no address found on company pages or via geocoding"}


def search_company_contact(company_name: str, city: str = DEFAULT_CITY) -> dict:
    """
    Core lookup function. Wrapped as an MCP tool (search_company_tool) in
    mcp_server/server.py.

    Returns candidate contact emails and an address for the given company
    name, for the CONSUMER to review and confirm — this function never sends
    anything and never picks an email automatically on the user's behalf.
    """
    if not company_name.strip():
        return {"error": "company_name is required"}

    tavily_result = _search_company_via_tavily(company_name, city)
    website = tavily_result.get("website")
    raw_text = tavily_result.get("raw_text", "")

    preferred_domain = ""
    if website:
        match = re.search(r"https?://(?:www\.)?([^/]+)", website)
        if match:
            preferred_domain = match.group(1)

    candidate_emails = _clean_emails(raw_text, preferred_domain=preferred_domain)
    address = _find_address(company_name, city, raw_text)

    result = {
        "company_name": company_name,
        "website": website,
        "candidate_emails": candidate_emails,
        "address": address,
        "note": (
            "These are best-effort search results. Please verify the email "
            "and address are correct before sending — HaqDar will not send "
            "anything until you confirm."
        ),
    }

    if tavily_result.get("error"):
        result["search_error"] = tavily_result["error"]

    return result
