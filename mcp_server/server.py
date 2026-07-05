"""
Minimal MCP server exposing HaqDar's authority-lookup as an MCP tool.

Run with: python mcp_server/server.py
The LangGraph agent calls this via an MCP client (see agents/authority_router.py
for the direct-call fallback used when running without the MCP layer).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from agents.authority_router import lookup_authority, find_forum_location
from agents.delivery_node import send_email_notice
from agents.company_lookup import search_company_contact
from rag.retriever import retrieve_sections
from config import DEFAULT_CITY

mcp = FastMCP("haqdar-tools")


@mcp.tool()
def lookup_authority_tool(issue_type: str) -> dict:
    """
    Look up which authority/forum a consumer should file with, given a
    classified issue type: defective_product, defective_service,
    unfair_deceptive_practice, or pricing_receipt_disclosure.
    Returns forum name, filing process, and any pre-requisites (e.g. notice period).
    """
    return lookup_authority(issue_type)


@mcp.tool()
def search_consumer_law(query: str, top_k: int = 4) -> list[dict]:
    """
    Search the Sindh Consumer Protection Act 2014 + Rules 2017 for sections
    relevant to a consumer's complaint description.
    """
    return retrieve_sections(query, top_k=top_k)


@mcp.tool()
def locate_forum_tool(issue_type: str, city: str = DEFAULT_CITY) -> dict:
    """
    Finds the physical address and map link for the consumer forum handling
    a given issue type: defective_product, defective_service,
    unfair_deceptive_practice, or pricing_receipt_disclosure. Uses OpenStreetMap
    Nominatim (free, no API key required). Returns {"found": False, ...} if
    no match is found.
    """
    return find_forum_location(issue_type, city)


@mcp.tool()
def search_company_tool(company_name: str, city: str = DEFAULT_CITY) -> dict:
    """
    Searches for a company/shop's likely website, contact email(s), and
    physical address, given just its name. This is a best-effort lookup for
    the consumer to REVIEW — it never sends anything and never picks an
    email automatically. The consumer must confirm the details before
    send_notice_tool is called.
    """
    return search_company_contact(company_name, city)


@mcp.tool()
def send_notice_tool(shop_email: str, letter_text: str, shop_name: str = "") -> dict:
    """
    Sends the drafted consumer complaint letter to the shop/company via
    email (Gmail SMTP). ONLY call this after explicit confirmation from the
    consumer that they want the letter sent — never send unprompted.
    shop_email should be a valid email address. shop_name (optional) is used
    in the email subject line so the recipient sees at a glance what it concerns.
    """
    return send_email_notice(shop_email, letter_text, shop_name)


if __name__ == "__main__":
    mcp.run(transport="stdio")
