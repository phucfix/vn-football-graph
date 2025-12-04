"""
Data Enrichment Module for Vietnam Football Knowledge Graph

This package provides text collection and preprocessing for NLP-based
knowledge graph enrichment.
"""

from .text_collector import TextCollector
from .text_preprocessor import TextPreprocessor

__all__ = ["TextCollector", "TextPreprocessor"]
