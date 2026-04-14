#!/usr/bin/env python3
"""
Export lead JSON files to CSV.

Default behavior exports the scored lead pipeline to ~/gdrive so the file is ready
for review/sharing outside the repo.
"""

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

DEFAULT_INPUT = Path("/home/molt/devspace/testhelp24-leads/data/pipeline/all_leads_scored.json")
DEFAULT_FALLBACK_INPUT = Path("/home/molt/devspace/testhelp24-leads/data/enriched_leads.json")
DEFAULT_OUTPUT = Path("/home/molt/gdrive/testhelp24_leads_all_scored.csv")

DEFAULT_COLUMNS = [
    "company_name",
    "city",
    "address",
    "phone",
    "email",
    "additional_emails",
    "website",
    "website_status",
    "contact_person",
    "decision_makers",
    "company_size",
    "quality_score",
    "outreach_priority",
    "lead_stage",
    "status",
    "source",
    "source_type",
    "rating",
    "review_count",
    "google_maps_url",
    "notes",
    "enriched_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export lead JSON data to CSV")
    parser.add_argument("--input", default="", help="Input JSON file")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Output CSV file")
    parser.add_argument("--include-extra-fields", action="store_true", help="Append any extra fields found in records")
    return parser.parse_args()


def choose_input(requested: str) -> Path:
    if requested:
        return Path(requested).expanduser()
    if DEFAULT_INPUT.exists():
        return DEFAULT_INPUT
    return DEFAULT_FALLBACK_INPUT


def load_rows(path: Path) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected a list of records in {path}")
    return data


def stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def collect_columns(rows: Iterable[Dict[str, Any]], include_extra_fields: bool) -> List[str]:
    columns = list(DEFAULT_COLUMNS)
    if include_extra_fields:
        seen = set(columns)
        for row in rows:
            for key in row.keys():
                if key not in seen:
                    seen.add(key)
                    columns.append(key)
    return columns


def export_csv(rows: List[Dict[str, Any]], output_path: Path, columns: List[str]):
    output_path = output_path.expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: stringify(row.get(column, "")) for column in columns})


def main():
    args = parse_args()
    input_path = choose_input(args.input)
    output_path = Path(args.output).expanduser()

    rows = load_rows(input_path)
    columns = collect_columns(rows, args.include_extra_fields)
    export_csv(rows, output_path, columns)

    print("=" * 70)
    print("CSV EXPORT SUMMARY")
    print("=" * 70)
    print(f"Input:  {input_path}")
    print(f"Rows:   {len(rows)}")
    print(f"Output: {output_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
