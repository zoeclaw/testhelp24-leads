"""
Kompass.de directory scraper for staffing agencies.
Outputs canonical lead records compatible with the volume-first pipeline.
"""

import time
from typing import Dict, List
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

from schema import make_lead_record
from utils import RAW_COMPANIES_FILE, load_json, log_error, log_progress, save_json

KOMPASS_BASE = "https://www.kompass.de"
KOMPASS_SEARCH = f"{KOMPASS_BASE}/de/search"


def search_kompass(city: str, max_pages: int = 5) -> List[Dict]:
    companies = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            params = {
                "q": f"Zeitarbeit {city}",
                "sector": "",
            }
            url = f"{KOMPASS_SEARCH}?{urlencode(params)}"

            log_progress(f"Scraping Kompass: {city}", source="kompass")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(2)

            for page_num in range(1, max_pages + 1):
                try:
                    listings = page.locator("div[data-testid='company-result']")
                    count = listings.count()

                    if count == 0:
                        log_progress(f"No more results on page {page_num}", source="kompass")
                        break

                    log_progress(f"Found {count} companies on page {page_num}", source="kompass")

                    for i in range(count):
                        try:
                            listing = listings.nth(i)
                            company_name = listing.locator("a[data-testid='company-name']").inner_text() if listing.locator("a[data-testid='company-name']").count() > 0 else ""
                            address = listing.locator("span[data-testid='address']").inner_text() if listing.locator("span[data-testid='address']").count() > 0 else ""
                            phone = listing.locator("span[data-testid='phone']").inner_text() if listing.locator("span[data-testid='phone']").count() > 0 else ""

                            if not company_name:
                                continue

                            company_data = make_lead_record(
                                company_name=company_name,
                                address=address,
                                city=city,
                                location=city,
                                phone=phone,
                                email="",
                                website="",
                                company_size="",
                                contact_person="",
                                source="Kompass",
                                source_type="directory",
                                lead_stage="collected",
                                status="collected",
                                source_metadata={
                                    "city": city,
                                    "page": page_num,
                                    "listing_index": i,
                                },
                            )
                            companies.append(company_data)

                        except Exception as e:
                            log_error(f"Failed to extract listing {i}", source="kompass", exception=e)
                            continue

                    next_button = page.locator("a[aria-label*='next']")
                    if next_button.count() > 0:
                        next_button.click()
                        time.sleep(2)
                    else:
                        log_progress(f"No next page button found, stopping at page {page_num}", source="kompass")
                        break

                except Exception as e:
                    log_error(f"Error on page {page_num}", source="kompass", exception=e)
                    break

            browser.close()

    except Exception as e:
        log_error(f"Kompass scraper failed for {city}", source="kompass", exception=e)

    return companies


def scrape_city(city: str):
    log_progress(f"Starting Kompass POC for {city}", source="kompass")

    companies = search_kompass(city, max_pages=3)

    if companies:
        existing = load_json(RAW_COMPANIES_FILE)
        all_companies = existing + companies
        save_json(RAW_COMPANIES_FILE, all_companies, append=False)
        log_progress(f"POC complete: {len(companies)} new companies from Kompass ({city})", source="kompass")
    else:
        log_progress(f"No companies found for {city}", source="kompass")


if __name__ == "__main__":
    scrape_city("Berlin")
