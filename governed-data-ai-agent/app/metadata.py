from __future__ import annotations

import os
from typing import Dict, List

from .models import MetadataEnrichment


PII_PATTERNS = {
    "email": ["PII", "Contact"],
    "phone": ["PII", "Contact"],
    "ssn": ["PII", "HighlySensitive"],
    "name": ["PII"],
    "address": ["PII", "Location"],
    "account": ["Financial"],
    "card": ["Financial", "HighlySensitive"],
    "device": ["DeviceIdentifier"],
    "customer": ["CustomerData"],
}


def deterministic_enrichment(columns: List[str], domain: str) -> MetadataEnrichment:
    classifications: Dict[str, List[str]] = {}
    rationale: List[str] = []
    sensitivity = "internal"

    for col in columns:
        tags: List[str] = []
        lower = col.lower()
        for pattern, mapped_tags in PII_PATTERNS.items():
            if pattern in lower:
                tags.extend(mapped_tags)
        if tags:
            tags = sorted(set(tags))
            classifications[col] = tags
            rationale.append(f"{col}: matched governed naming pattern -> {', '.join(tags)}")
            if "HighlySensitive" in tags:
                sensitivity = "restricted"
            elif "PII" in tags and sensitivity != "restricted":
                sensitivity = "confidential"

    description = (
        f"Governed {domain} data product evaluated for metadata enrichment, data quality, "
        "anomaly detection, lineage, access control, and AI governance readiness."
    )
    return MetadataEnrichment(
        classifications=classifications,
        suggested_description=description,
        sensitivity=sensitivity,
        rationale=rationale or ["No sensitive naming patterns detected."],
    )


def enrich_metadata(columns: List[str], domain: str) -> MetadataEnrichment:
    """Deterministic by default; designed so Azure OpenAI can be plugged in safely.

    In production, set AZURE_OPENAI_ENABLED=true and replace this boundary with a model
    call that returns structured JSON. Keep policy enforcement outside the LLM.
    """
    _ = os.getenv("AZURE_OPENAI_ENABLED", "false").lower() == "true"
    return deterministic_enrichment(columns, domain)
