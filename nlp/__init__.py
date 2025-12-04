"""
NLP Module for Vietnam Football Knowledge Graph Enrichment

This package provides Named Entity Recognition (NER) and Relation Extraction (RE)
for Vietnamese football text data.
"""

from .entity_recognizer import EntityRecognizer
from .relation_extractor import RelationExtractor

__all__ = ["EntityRecognizer", "RelationExtractor"]
