#!/usr/bin/env python3
"""
Canonical lead schema helpers.

This module defines the project-wide record shape used across collectors,
pipeline, enrichment, and prioritization.
"""

from typing import Any, Dict, Iterable

CANONICAL_LEAD_FIELDS = [
    "company_name",
    "address",
    "city",
    "location",
    "phone",
    "email",
    "additional_emails",
    "website",
    "website_status",
    "company_size",
    "contact_person",
    "decision_makers",
    "lead_stage",
    "status",
    "enriched_at",
    "source",
    "source_type",
    "source_metadata",
    "notes",
    "rating",
    "review_count",
    "google_maps_url",
]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def coalesce(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


ALIAS_MAP = {
    "name": "company_name",
    "formatted_phone_number": "phone",
    "decision_maker": "contact_person",
}


def normalize_lead(lead: Dict[str, Any], source: str | None = None, source_type: str | None = None) -> Dict[str, Any]:
    """Normalize any source record into the canonical lead shape."""
    raw = dict(lead or {})

    for alias, canonical in ALIAS_MAP.items():
        if alias in raw and canonical not in raw:
            raw[canonical] = raw[alias]

    normalized: Dict[str, Any] = {
        "company_name": coalesce(raw.get("company_name"), raw.get("name")),
        "address": clean_text(raw.get("address")),
        "city": coalesce(raw.get("city"), raw.get("location")),
        "location": coalesce(raw.get("location"), raw.get("city")),
        "phone": coalesce(raw.get("phone"), raw.get("formatted_phone_number")),
        "email": clean_text(raw.get("email")),
        "additional_emails": raw.get("additional_emails") or [],
        "website": clean_text(raw.get("website")),
        "website_status": clean_text(raw.get("website_status")),
        "company_size": clean_text(raw.get("company_size")),
        "contact_person": coalesce(raw.get("contact_person"), raw.get("decision_maker")),
        "decision_makers": raw.get("decision_makers") or [],
        "lead_stage": clean_text(raw.get("lead_stage")) or clean_text(raw.get("status")) or "collected",
        "status": clean_text(raw.get("status")) or clean_text(raw.get("lead_stage")) or "collected",
        "enriched_at": clean_text(raw.get("enriched_at")),
        "source": clean_text(raw.get("source")) or clean_text(source) or "unknown",
        "source_type": clean_text(raw.get("source_type")) or clean_text(source_type) or "unknown",
        "source_metadata": raw.get("source_metadata") or {},
        "notes": clean_text(raw.get("notes")),
        "rating": raw.get("rating", ""),
        "review_count": raw.get("review_count", 0),
        "google_maps_url": clean_text(raw.get("google_maps_url")),
    }

    for key, value in raw.items():
        if key not in normalized:
            normalized[key] = value

    if normalized["email"] and normalized["email"] in normalized["additional_emails"]:
        normalized["additional_emails"] = [e for e in normalized["additional_emails"] if e != normalized["email"]]

    if not isinstance(normalized["additional_emails"], list):
        normalized["additional_emails"] = [normalized["additional_emails"]]

    if not isinstance(normalized["decision_makers"], list):
        normalized["decision_makers"] = [normalized["decision_makers"]]

    return normalized


def make_lead_record(*, company_name: str, source: str, source_type: str, **fields: Any) -> Dict[str, Any]:
    """Create a canonical lead record."""
    payload = dict(fields)
    payload["company_name"] = company_name
    payload["source"] = source
    payload["source_type"] = source_type
    return normalize_lead(payload)


def count_contact_channels(lead: Dict[str, Any]) -> int:
    """Return how many direct contact channels a lead currently has."""
    normalized = normalize_lead(lead)
    return sum(
        1 for value in [normalized.get("email"), normalized.get("phone"), normalized.get("website")]
        if clean_text(value)
    )


def merge_unique_strings(values: Iterable[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        text = clean_text(value)
        if text and text not in unique:
            unique.append(text)
    return unique
