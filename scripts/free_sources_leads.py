#!/usr/bin/env python3
"""
Free lead generation from public German sources.
Uses canonical schema so bootstrap leads flow cleanly into the main pipeline.
"""

import os
import json
from datetime import datetime

from schema import make_lead_record

MAJOR_STAFFING_COMPANIES = {
    "Adecco": {
        "website": "https://www.adecco.de",
        "note": "Multiple locations across Germany"
    },
    "Randstad": {
        "website": "https://www.randstad.de",
        "note": "Major player, many branches"
    },
    "Manpower": {
        "website": "https://www.manpower.de",
        "note": "Global player, German operations"
    },
    "Kelly Services": {
        "website": "https://www.kellyservices.de",
        "note": "Global staffing provider"
    },
    "Michael Page": {
        "website": "https://www.michaelpage.de",
        "note": "Professional recruitment"
    },
    "Heidrick & Struggles": {
        "website": "https://www.heidrick.com",
        "note": "Executive search"
    },
    "PageGroup": {
        "website": "https://www.pagegroup.de",
        "note": "Professional staffing"
    },
    "Recruitment Matters": {
        "website": "https://www.recruitment-matters.de",
        "note": "German-focused recruiter"
    }
}

DIRECTORIES = {
    "DIHK-IHK": {
        "url": "https://www.dihk.de",
        "note": "German Chamber of Commerce - has member databases"
    },
    "Bundesinstitut für Berufsbildung": {
        "url": "https://www.bibb.de",
        "note": "Federal Institute for Vocational Education"
    },
    "ZAV (Zentrale Auslands- und Fachvermittlung)": {
        "url": "https://www.arbeitsagentur.de/vor-ort/zav",
        "note": "German Employment Agency list"
    }
}

LISTING_SITES = [
    {
        "name": "Yellow Pages Germany (Das Telefonbuch)",
        "url": "https://www.dastelefonbuch.de",
        "search": "search?kw=Zeitarbeit"
    },
    {
        "name": "Gelbseiten",
        "url": "https://www.gelbseiten.de",
        "search": "search/Zeitarbeit"
    },
    {
        "name": "Bundesverband der Personalvermittler",
        "url": "https://www.bvd-personalvermittlung.de",
        "note": "Member directory of staffing associations"
    }
]

TARGET_CITIES = [
    {"name": "Berlin", "population": 3645000, "priority": 1},
    {"name": "Munich", "population": 1484000, "priority": 1},
    {"name": "Hamburg", "population": 1852000, "priority": 1},
    {"name": "Cologne", "population": 1087000, "priority": 2},
    {"name": "Frankfurt", "population": 753000, "priority": 2},
    {"name": "Stuttgart", "population": 623000, "priority": 2},
    {"name": "Düsseldorf", "population": 621000, "priority": 2},
    {"name": "Dortmund", "population": 587000, "priority": 2},
    {"name": "Essen", "population": 582000, "priority": 2},
    {"name": "Leipzig", "population": 597000, "priority": 3},
    {"name": "Dresden", "population": 563000, "priority": 3},
    {"name": "Hanover", "population": 535000, "priority": 3},
    {"name": "Nuremberg", "population": 518000, "priority": 3},
    {"name": "Duisburg", "population": 501000, "priority": 3},
    {"name": "Bochum", "population": 364000, "priority": 3},
    {"name": "Wuppertal", "population": 355000, "priority": 3},
    {"name": "Bielefeld", "population": 338000, "priority": 3},
    {"name": "Bonn", "population": 331000, "priority": 3},
    {"name": "Mannheim", "population": 309000, "priority": 3},
    {"name": "Karlsruhe", "population": 308000, "priority": 3},
    {"name": "Augsburg", "population": 301000, "priority": 3},
    {"name": "Wiesbaden", "population": 278000, "priority": 3},
    {"name": "Gelsenkirchen", "population": 260000, "priority": 3},
    {"name": "Potsdam", "population": 187000, "priority": 3},
    {"name": "Bremen", "population": 569000, "priority": 2}
]


def generate_lead_template(company_name: str, city: str = "", website: str = "", notes: str = "") -> dict:
    return make_lead_record(
        company_name=company_name,
        source="Bootstrap",
        source_type="seed",
        city=city,
        location=city,
        website=website,
        phone="",
        email="",
        address="",
        company_size="",
        contact_person="",
        notes=notes,
        lead_stage="seeded",
        status="to_enrich",
        source_metadata={"strategy": "volume_first"},
    )


def generate_bootstrap_leads() -> list:
    leads = []
    for company, info in MAJOR_STAFFING_COMPANIES.items():
        for city in TARGET_CITIES:
            leads.append(
                generate_lead_template(
                    company_name=company,
                    city=city["name"],
                    website=info.get("website", ""),
                    notes=f"{info.get('note')} - Branch in {city['name']}"
                )
            )
    return leads


def generate_research_tasks() -> dict:
    return {
        "title": "Lead Research & Enrichment Tasks",
        "strategy": "volume_first",
        "generated_at": datetime.now().isoformat(),
        "tasks": [
            {
                "priority": 1,
                "task": "Extract company directory from DIHK member database",
                "url": "https://www.dihk.de",
                "target": "Find Zeitarbeit members by region"
            },
            {
                "priority": 1,
                "task": "Extract from Yellow Pages (Das Telefonbuch) API or scrape",
                "url": "https://www.dastelefonbuch.de",
                "keywords": ["Zeitarbeit", "Personalvermittlung"]
            },
            {
                "priority": 1,
                "task": "Extract from Gelbseiten directory",
                "url": "https://www.gelbseiten.de",
                "keywords": ["Zeitarbeit", "Personalvermittlung"]
            },
            {
                "priority": 2,
                "task": "LinkedIn search for staffing companies + HR leads",
                "note": "Manual search (free tier: search by company, location, title)",
                "fields": ["company_name", "founder", "ceo", "head_of_sales"]
            },
            {
                "priority": 2,
                "task": "Google search operator extraction",
                "example": 'site:.de "Zeitarbeit" "kontakt@" OR "info@"',
                "note": "Find contact forms and emails"
            },
            {
                "priority": 3,
                "task": "Chamber of Commerce regional branches",
                "note": "IHK has member lists by industry classification"
            }
        ]
    }


def main():
    print("=" * 70)
    print("🔍 German Staffing Leads - Free Source Research")
    print("=" * 70)
    print()

    print("📋 Generating bootstrap leads from major companies...")
    bootstrap_leads = generate_bootstrap_leads()
    print(f"   ✓ Created {len(bootstrap_leads)} lead records (major companies × cities)")
    print()

    output_file = "/home/molt/devspace/testhelp24-leads/data/bootstrap_leads.json"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(bootstrap_leads, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved bootstrap leads to {output_file}")
    print()

    print("🎯 Generating research tasks for enrichment...")
    research_tasks = generate_research_tasks()

    tasks_file = "/home/molt/devspace/testhelp24-leads/data/research_tasks.json"
    with open(tasks_file, "w", encoding="utf-8") as f:
        json.dump(research_tasks, f, ensure_ascii=False, indent=2)
    print(f"✓ Saved research tasks to {tasks_file}")
    print()

    print("📚 Recommended directories to check:")
    print("-" * 70)
    for dir_name, dir_info in DIRECTORIES.items():
        print(f"  • {dir_name}")
        print(f"    {dir_info.get('url')}")
        print(f"    Note: {dir_info.get('note')}")
        print()

    print("🔗 Listing sites with directory search:")
    print("-" * 70)
    for site in LISTING_SITES:
        print(f"  • {site.get('name')}")
        print(f"    {site.get('url')}")
        if site.get('search'):
            print(f"    Search: {site.get('search')}")
        print()

    print("=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"✓ Bootstrap leads: {len(bootstrap_leads)}")
    print(f"✓ Major companies tracked: {len(MAJOR_STAFFING_COMPANIES)}")
    print(f"✓ Target cities: {len(TARGET_CITIES)}")
    print(f"✓ Research tasks: {len(research_tasks['tasks'])}")
    print()
    print("Next steps:")
    print("1. Run collect_volume_sources.py or run_volume_pipeline.py")
    print("2. Enrich bootstrap and scraped leads")
    print("3. Discover decision-makers as a second pass")
    print("4. Use scored tiers for outreach")
    print()


if __name__ == "__main__":
    main()
