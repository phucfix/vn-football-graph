"""
Text Preprocessor for Vietnam Football Knowledge Graph Enrichment

This module preprocesses collected text data for NLP processing:
- Vietnamese text normalization
- Sentence segmentation
- Token cleaning
- Output as JSONL for NLP pipeline

Usage:
    python -m data_enrichment.text_preprocessor --process-all
    python -m data_enrichment.text_preprocessor --entity-type player
"""

import argparse
import json
import logging
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

from tqdm import tqdm

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import BASE_DIR, DATA_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

TEXT_SOURCES_DIR = DATA_DIR / "text_sources"
WIKIPEDIA_TEXTS_DIR = TEXT_SOURCES_DIR / "wikipedia"
PROCESSED_TEXTS_DIR = DATA_DIR / "processed_texts"

# Minimum/maximum sentence length
MIN_SENTENCE_LENGTH = 10
MAX_SENTENCE_LENGTH = 500

# Vietnamese sentence ending patterns
SENTENCE_ENDINGS = re.compile(r'[.!?](?:\s|$)')

# Common Vietnamese abbreviations (shouldn't be treated as sentence endings)
ABBREVIATIONS = {
    "tp.", "tp ", "t.p.", "q.", "h.", "tx.", "tt.",  # địa danh
    "ths.", "ts.", "pgs.", "gs.", "cn.", "ks.", "bs.",  # học hàm
    "mr.", "mrs.", "ms.", "dr.", "prof.",  # English
    "st.", "sr.", "jr.", "vs.", "etc.",
    "clb.", "fc.", "afc.", "aff.", "fifa.", "vff.",  # bóng đá
    "hlv.", "đt.", "đtvn.", "u23.", "u22.", "u21.", "u20.", "u19.",
}


class TextPreprocessor:
    """
    Preprocesses Vietnamese text for NLP pipeline.
    
    Features:
    - Unicode normalization (NFC form)
    - Vietnamese-specific text cleaning
    - Sentence segmentation with abbreviation handling
    - Outputs JSONL format with metadata
    """
    
    def __init__(
        self,
        min_sentence_length: int = MIN_SENTENCE_LENGTH,
        max_sentence_length: int = MAX_SENTENCE_LENGTH,
    ):
        """
        Initialize the preprocessor.
        
        Args:
            min_sentence_length: Minimum characters per sentence
            max_sentence_length: Maximum characters per sentence
        """
        self.min_sentence_length = min_sentence_length
        self.max_sentence_length = max_sentence_length
        
        # Try to import Vietnamese NLP tools
        self._init_tokenizer()
        
        # Ensure output directory exists
        PROCESSED_TEXTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _init_tokenizer(self) -> None:
        """Initialize Vietnamese tokenizer (underthesea or fallback)."""
        self.tokenizer = None
        self.tokenizer_type = "regex"
        
        try:
            from underthesea import sent_tokenize
            self.tokenizer = sent_tokenize
            self.tokenizer_type = "underthesea"
            logger.info("Using underthesea for sentence tokenization")
        except ImportError:
            logger.warning(
                "underthesea not installed. Using regex-based tokenization. "
                "Install with: pip install underthesea"
            )
    
    def normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode text to NFC form.
        
        Handles Vietnamese characters with combining diacritics.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        # Normalize to NFC (composed form)
        text = unicodedata.normalize('NFC', text)
        
        # Fix common Vietnamese character issues
        # Some sources use decomposed forms or wrong characters
        replacements = {
            '\u0065\u0309': 'ẻ',  # e + hook above
            '\u0065\u0301': 'é',  # e + acute
            '\u0065\u0300': 'è',  # e + grave
            '\u0065\u0303': 'ẽ',  # e + tilde
            '\u0065\u0323': 'ẹ',  # e + dot below
            # Add more as needed
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by removing noise and normalizing whitespace.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Normalize unicode first
        text = self.normalize_unicode(text)
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'www\.\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+\.\S+', '', text)
        
        # Remove wiki markup leftovers
        text = re.sub(r'\[\[|\]\]', '', text)
        text = re.sub(r'\{\{|\}\}', '', text)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
        
        # Remove special characters but keep Vietnamese punctuation
        # Keep: letters, numbers, spaces, basic punctuation
        text = re.sub(r'[^\w\s.,;:!?\-–—\'\"()\[\]%°/]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n', text)
        
        # Remove leading/trailing whitespace from lines
        text = '\n'.join(line.strip() for line in text.split('\n'))
        
        return text.strip()
    
    def _is_abbreviation_ending(self, text: str, pos: int) -> bool:
        """
        Check if a period at position `pos` is part of an abbreviation.
        
        Args:
            text: Full text
            pos: Position of the period
            
        Returns:
            True if this period is part of an abbreviation
        """
        # Get the word before the period
        start = text.rfind(' ', 0, pos) + 1
        word = text[start:pos+1].lower()
        
        # Check against known abbreviations
        for abbrev in ABBREVIATIONS:
            if word.endswith(abbrev) or word == abbrev:
                return True
        
        # Check if followed by a lowercase letter (likely abbreviation)
        if pos + 2 < len(text) and text[pos+1] == ' ' and text[pos+2].islower():
            return True
        
        return False
    
    def segment_sentences_regex(self, text: str) -> List[str]:
        """
        Segment text into sentences using regex (fallback method).
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        sentences = []
        current_sentence = []
        
        # Split by potential sentence boundaries
        parts = re.split(r'([.!?]+)', text)
        
        for i, part in enumerate(parts):
            if not part:
                continue
            
            if re.match(r'^[.!?]+$', part):
                # This is punctuation
                if current_sentence:
                    current_sentence.append(part)
                    sentence = ''.join(current_sentence).strip()
                    
                    # Check if it's a real sentence ending
                    full_text = text[:text.find(sentence) + len(sentence)] if sentence in text else text
                    pos = len(full_text) - 1
                    
                    if not self._is_abbreviation_ending(text, pos) and len(sentence) >= self.min_sentence_length:
                        sentences.append(sentence)
                        current_sentence = []
                    # else: continue accumulating
            else:
                current_sentence.append(part)
        
        # Don't forget the last sentence
        if current_sentence:
            sentence = ''.join(current_sentence).strip()
            if len(sentence) >= self.min_sentence_length:
                sentences.append(sentence)
        
        return sentences
    
    def segment_sentences(self, text: str) -> List[str]:
        """
        Segment text into sentences.
        
        Uses underthesea if available, otherwise regex-based segmentation.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        if self.tokenizer_type == "underthesea" and self.tokenizer:
            try:
                sentences = self.tokenizer(text)
            except Exception as e:
                logger.warning(f"underthesea tokenization failed: {e}, falling back to regex")
                sentences = self.segment_sentences_regex(text)
        else:
            sentences = self.segment_sentences_regex(text)
        
        # Filter and clean sentences
        filtered = []
        for sent in sentences:
            sent = sent.strip()
            
            # Skip too short or too long
            if len(sent) < self.min_sentence_length:
                continue
            if len(sent) > self.max_sentence_length:
                # Try to split long sentences
                parts = re.split(r'[,;]', sent)
                for part in parts:
                    part = part.strip()
                    if self.min_sentence_length <= len(part) <= self.max_sentence_length:
                        filtered.append(part)
                continue
            
            filtered.append(sent)
        
        return filtered
    
    def process_text_file(
        self,
        file_path: Path,
    ) -> Optional[Dict]:
        """
        Process a single text file into sentences.
        
        Args:
            file_path: Path to text file
            
        Returns:
            Dict with processed data, or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract metadata from first line
            lines = content.split('\n', 2)
            metadata_match = re.match(r'<!-- METADATA: ({.*}) -->', lines[0])
            
            if metadata_match:
                metadata = json.loads(metadata_match.group(1))
                text = lines[2] if len(lines) > 2 else ""
            else:
                metadata = {
                    "wiki_id": None,
                    "entity_type": "unknown",
                    "page_title": file_path.stem,
                }
                text = content
            
            # Clean and segment
            cleaned_text = self.clean_text(text)
            sentences = self.segment_sentences(cleaned_text)
            
            if not sentences:
                return None
            
            return {
                "wiki_id": metadata.get("wiki_id"),
                "entity_type": metadata.get("entity_type", "unknown"),
                "page_title": metadata.get("page_title", ""),
                "source_file": str(file_path),
                "sentence_count": len(sentences),
                "sentences": sentences,
                "processed_at": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None
    
    def process_all_texts(
        self,
        entity_type: Optional[str] = None,
        output_file: Optional[Path] = None,
    ) -> Dict[str, int]:
        """
        Process all collected text files into sentences.
        
        Args:
            entity_type: Filter by entity type
            output_file: Output JSONL file path
            
        Returns:
            Statistics dict
        """
        stats = {
            "total_files": 0,
            "processed": 0,
            "total_sentences": 0,
            "errors": 0,
        }
        
        # Find all text files
        pattern = f"{entity_type}_*.txt" if entity_type else "*.txt"
        files = list(WIKIPEDIA_TEXTS_DIR.glob(pattern))
        stats["total_files"] = len(files)
        
        if not files:
            logger.warning(f"No text files found in {WIKIPEDIA_TEXTS_DIR}")
            return stats
        
        # Determine output file
        if output_file is None:
            suffix = f"_{entity_type}" if entity_type else ""
            output_file = PROCESSED_TEXTS_DIR / f"wikipedia{suffix}_sentences.jsonl"
        
        logger.info(f"Processing {len(files)} files...")
        
        with open(output_file, 'w', encoding='utf-8') as out_f:
            for file_path in tqdm(files, desc="Processing texts"):
                result = self.process_text_file(file_path)
                
                if result:
                    # Write each sentence as a separate record
                    for idx, sentence in enumerate(result["sentences"]):
                        record = {
                            "sentence_id": f"{result['wiki_id']}_{idx}",
                            "wiki_id": result["wiki_id"],
                            "entity_type": result["entity_type"],
                            "page_title": result["page_title"],
                            "sentence": sentence,
                            "sentence_idx": idx,
                        }
                        out_f.write(json.dumps(record, ensure_ascii=False) + '\n')
                    
                    stats["processed"] += 1
                    stats["total_sentences"] += result["sentence_count"]
                else:
                    stats["errors"] += 1
        
        logger.info(
            f"Processing complete: {stats['processed']} files, "
            f"{stats['total_sentences']} sentences"
        )
        
        return stats
    
    def preview_sentences(
        self,
        file_path: Path,
        max_sentences: int = 10,
    ) -> List[str]:
        """
        Preview sentences from a text file.
        
        Args:
            file_path: Path to text file
            max_sentences: Maximum sentences to return
            
        Returns:
            List of sentences
        """
        result = self.process_text_file(file_path)
        if result:
            return result["sentences"][:max_sentences]
        return []


def main():
    """CLI entry point for text preprocessor."""
    parser = argparse.ArgumentParser(
        description="Preprocess text data for Vietnam Football KG enrichment"
    )
    
    parser.add_argument(
        "--process-all",
        action="store_true",
        help="Process all collected text files",
    )
    parser.add_argument(
        "--entity-type",
        type=str,
        choices=["player", "coach", "club", "national_team", "stadium", "competition"],
        help="Filter by entity type",
    )
    parser.add_argument(
        "--preview",
        type=str,
        metavar="FILE",
        help="Preview sentences from a specific file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSONL file path",
    )
    
    args = parser.parse_args()
    
    preprocessor = TextPreprocessor()
    
    if args.preview:
        file_path = Path(args.preview)
        if not file_path.exists():
            # Try in wikipedia texts dir
            file_path = WIKIPEDIA_TEXTS_DIR / args.preview
        
        if not file_path.exists():
            print(f"File not found: {args.preview}")
            return
        
        print(f"\n=== Preview: {file_path.name} ===\n")
        sentences = preprocessor.preview_sentences(file_path, max_sentences=15)
        for i, sent in enumerate(sentences, 1):
            print(f"{i}. {sent}\n")
        return
    
    if args.process_all:
        print("\n=== Processing All Text Files ===")
        output_file = Path(args.output) if args.output else None
        stats = preprocessor.process_all_texts(
            entity_type=args.entity_type,
            output_file=output_file,
        )
        print(f"\nProcessing complete:")
        print(f"  Files processed: {stats['processed']}")
        print(f"  Total sentences: {stats['total_sentences']}")
        print(f"  Errors: {stats['errors']}")
        return
    
    # Default: show help
    parser.print_help()


if __name__ == "__main__":
    main()
