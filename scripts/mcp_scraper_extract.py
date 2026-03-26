"""
MCP-based scraper using extract tool (AI-assisted JSON extraction)
More reliable than HTML parsing for structured data
"""
import json
from typing import List, Dict
from mcp_protocol_client import MCPProtocolClient
from utils import log_progress, log_error, load_json, save_json, RAW_COMPANIES_FILE

BRIGHTDATA_TOKEN = "5f30e9a0-5119-4cc7-8c27-b638949d683f"

# JSON schema for extraction
STAFFING_AGENCY_SCHEMA = """
{
  "type": "object",
  "properties": {
    "companies": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "company_name": {"type": "string"},
          "address": {"type": "string"},
          "phone": {"type": "string"},
          "email": {"type": "string"},
          "website": {"type": "string"}
        }
      }
    }
  }
}
"""

EXTRACTION_PROMPT = """
Extract a list of staffing agencies (Zeitarbeit companies) from this page.
For each company, extract:
- Company name
- Address/location
- Phone number
- Email address
- Website URL

Return as JSON with "companies" array.
"""


def scrape_with_extract(url: str, source: str = "Unknown") -> List[Dict]:
    """
    Scrape using MCP extract tool (AI-assisted)
    """
    companies = []
    
    client = MCPProtocolClient(
        ["npx", "@brightdata/mcp"],
        env={
            "API_TOKEN": BRIGHTDATA_TOKEN,
            "GROUPS": "advanced_scraping",
        }
    )
    
    if not client.start():
        log_error(f"Failed to start MCP for {source}", source="mcp_extract")
        return companies
    
    try:
        log_progress(f"Extracting from {source}: {url}")
        
        # Call extract tool with custom schema
        result = client.call_tool(
            "extract",
            url=url,
            extraction_schema=STAFFING_AGENCY_SCHEMA,
            custom_extraction_prompt=EXTRACTION_PROMPT
        )
        
        if not result:
            log_progress(f"  No result from extract tool")
            return companies
        
        # Parse result
        if isinstance(result, dict):
            # Result might be {"json": {...}} or direct
            data = result.get("json") or result
        elif isinstance(result, list):
            data = {"companies": result}
        else:
            log_progress(f"  Unexpected result type: {type(result)}")
            return companies
        
        # Extract companies
        if isinstance(data, dict):
            company_list = data.get("companies", [])
        elif isinstance(data, list):
            company_list = data
        else:
            log_progress(f"  Could not find company list in result")
            return companies
        
        log_progress(f"  Found {len(company_list)} companies")
        
        for company in company_list:
            try:
                if isinstance(company, dict):
                    company_data = {
                        "company_name": company.get("company_name", ""),
                        "address": company.get("address", ""),
                        "phone": company.get("phone", ""),
                        "email": company.get("email", ""),
                        "website": company.get("website", ""),
                        "city": "",  # Can be extracted from address
                        "company_size": "",
                        "contact_person": "",
                        "source": f"{source}-MCP",
                    }
                    
                    if company_data["company_name"]:
                        companies.append(company_data)
                        log_progress(f"    → {company_data['company_name']}")
            except Exception as e:
                continue
    
    finally:
        client.stop()
    
    return companies


def scrape_kompass_extract(city: str, max_pages: int = 2) -> List[Dict]:
    """Scrape Kompass using extract tool"""
    companies = []
    
    log_progress(f"Kompass extract: {city}")
    
    for page_num in range(1, max_pages + 1):
        url = f"https://de.kompass.com/de/search?q=Zeitarbeit {city}&page={page_num}"
        page_companies = scrape_with_extract(url, f"Kompass-page{page_num}")
        companies.extend(page_companies)
        
        if not page_companies:
            break
    
    return companies


def scrape_wlw_extract(city: str) -> List[Dict]:
    """Scrape WLW using extract tool"""
    url = "https://www.wlw.de/de/de/c/branche/50250200"
    return scrape_with_extract(url, "WLW")


def scrape_city_extract(city: str):
    """Scrape city using extract tool"""
    log_progress(f"\n{'='*60}")
    log_progress(f"EXTRACT-BASED SCRAPING: {city}")
    log_progress(f"{'='*60}")
    
    kompass_companies = scrape_kompass_extract(city, max_pages=1)
    wlw_companies = scrape_wlw_extract(city)
    
    all_companies = kompass_companies + wlw_companies
    
    if all_companies:
        existing = load_json(RAW_COMPANIES_FILE)
        all_data = existing + all_companies
        save_json(RAW_COMPANIES_FILE, all_data, append=False)
        
        log_progress(f"\n✓ Extraction complete:")
        log_progress(f"  Kompass: {len(kompass_companies)} companies")
        log_progress(f"  WLW: {len(wlw_companies)} companies")
        log_progress(f"  Total new: {len(all_companies)}")
    else:
        log_progress(f"\n✗ No companies extracted")


if __name__ == "__main__":
    scrape_city_extract("Berlin")
