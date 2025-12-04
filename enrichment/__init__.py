"""
Enrichment Module for Vietnam Football Knowledge Graph

This package provides validation, deduplication, and quality checking
for extracted entities and relations.
"""

from .validation import EnrichmentValidator
from .deduplication import EntityDeduplicator, RelationDeduplicator

__all__ = ["EnrichmentValidator", "EntityDeduplicator", "RelationDeduplicator"]
