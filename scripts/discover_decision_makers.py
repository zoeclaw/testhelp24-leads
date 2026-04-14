#!/usr/bin/env python3
"""
Second-pass decision-maker discovery.

Heuristically scans company websites for likely decision-makers after company
capture/enrichment has already happened.
"""

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from typing import List
from urllib.parse import urljoin

import requests

from schema import clean_text, merge_unique_strings, normalize_lead

DEFAULT_INPUT = "/home/molt/devspace/testhelp24-leads/data/enriched_leads.json"
DEFAULT_OUTPUT = "/home/molt/devspace/testhelp24-leads/data/enriched_leads.json"

PAGES_TO_SCAN = ["", "kontakt", "contact", "team", "ueber-uns", "about", "impressum", "management"]
TARGET_TITLES = [
    "geschäftsführer", "geschaeftsfuehrer", "niederlassungsleiter", "branch manager",
    "standortleiter", "regionalleiter", "inhaber", "owner", "managing director",
    "ceo", "geschäftsleitung", "leitung", "head of recruiting", "recruiting manager",
    "personalberater", "vertriebsleiter", "hr manager", "operations manager"
]

NAME_PATTERN = re.compile(r"\b([A-ZÄÖÜ][a-zäöüß]+(?:\s+[A-ZÄÖÜ][a-zäöüß]+){1,2})\b")
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")


@dataclass
class Candidate:
    name: str
    title: str
    source_url: str


class DecisionMakerDiscoverer:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def _candidate_urls(self, website: str) -> List[str]:
        base = website if website.endswith("/") else website + "/"
        urls = []
        for suffix in PAGES_TO_SCAN:
            url = website if not suffix else urljoin(base, suffix)
            if url not in urls:
                urls.append(url)
        return urls

    def _find_candidates(self, html: str, source_url: str) -> List[Candidate]:
        lowered = html.lower()
        candidates: List[Candidate] = []
        for title in TARGET_TITLES:
            for match in re.finditer(title, lowered):
                start = max(0, match.start() - 120)
                end = min(len(html), match.end() + 120)
                window = html[start:end]
                name_match = NAME_PATTERN.search(window)
                if name_match:
                    candidates.append(Candidate(name=name_match.group(1), title=title, source_url=source_url))
        return candidates

    def enrich_lead(self, lead: dict) -> dict:
        lead = normalize_lead(lead)
        website = clean_text(lead.get("website"))
        if not website:
            return lead
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"
            lead["website"] = website

        decision_makers = list(lead.get("decision_makers") or [])
        discovered_emails = list(lead.get("additional_emails") or [])

        for url in self._candidate_urls(website):
            try:
                response = self.session.get(url, timeout=6)
                response.raise_for_status()
                html = response.text
            except requests.RequestException:
                continue

            for candidate in self._find_candidates(html, url):
                entry = {
                    "name": candidate.name,
                    "title": candidate.title,
                    "source_url": candidate.source_url,
                }
                if entry not in decision_makers:
                    decision_makers.append(entry)

            for email in EMAIL_PATTERN.findall(html):
                if email != lead.get("email"):
                    discovered_emails.append(email)

        if decision_makers:
            lead["decision_makers"] = decision_makers[:5]
            primary = decision_makers[0]
            if not lead.get("contact_person"):
                lead["contact_person"] = f"{primary['name']} ({primary['title']})"
            lead["lead_stage"] = "decision_maker_enriched"
            lead["status"] = "decision_maker_enriched"
        lead["additional_emails"] = merge_unique_strings(discovered_emails)[:5]
        return lead


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover decision-makers from websites")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=0, help="Limit number of leads processed (0 = all)")
    parser.add_argument("--pause-ms", type=int, default=200)
    return parser.parse_args()


def main():
    args = parse_args()
    if not os.path.exists(args.input):
        raise SystemExit(f"Input file not found: {args.input}")

    with open(args.input, "r", encoding="utf-8") as f:
        leads = json.load(f)

    discoverer = DecisionMakerDiscoverer()
    enriched = []
    total = len(leads) if args.limit <= 0 else min(args.limit, len(leads))

    for index, lead in enumerate(leads[:total], start=1):
        if index % 10 == 0:
            print(f"Progress: {index}/{total}")
        enriched.append(discoverer.enrich_lead(lead))
        time.sleep(max(args.pause_ms, 0) / 1000)

    if total < len(leads):
        enriched.extend(leads[total:])

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)

    found = len([lead for lead in enriched if lead.get("decision_makers")])
    print("=" * 70)
    print("DECISION-MAKER ENRICHMENT SUMMARY")
    print("=" * 70)
    print(f"Processed leads: {total}")
    print(f"Leads with decision-makers: {found}")
    print(f"Output file: {args.output}")
    print("=" * 70)


if __name__ == "__main__":
    main()
