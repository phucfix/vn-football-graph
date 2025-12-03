#!/usr/bin/env python3
"""
Stadium Data Cleaner

Cleans stadiums.jsonl to:
- Remove non-stadium records (lists, articles)
- Expand missing data from raw Wikipedia data
- Normalize location, capacity, and other fields
- Extract province from location
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import PARSED_DATA_DIR, PROCESSED_DATA_DIR, RAW_DATA_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StadiumCleaner:
    """Clean and expand stadium data."""
    
    # Keywords that indicate NOT a stadium
    INVALID_KEYWORDS = [
        "danh sách",    # List
        "thể loại",     # Category
        "bản mẫu",      # Template
    ]
    
    # Vietnamese provinces/cities for extraction
    PROVINCES = [
        "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Hải Phòng", "Cần Thơ",
        "An Giang", "Bà Rịa", "Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu",
        "Bắc Ninh", "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước",
        "Bình Thuận", "Cà Mau", "Cao Bằng", "Đắk Lắk", "Đắk Nông",
        "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang",
        "Hà Nam", "Hà Tĩnh", "Hải Dương", "Hậu Giang", "Hòa Bình",
        "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
        "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định",
        "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên",
        "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị",
        "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên",
        "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", "Trà Vinh", "Tuyên Quang",
        "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
        # Alternative names
        "TP. Hồ Chí Minh", "TP.HCM", "Sài Gòn", "Thành phố Hồ Chí Minh",
        "Huế", "Đà Lạt", "Nha Trang", "Vũng Tàu", "Phan Thiết",
        "Quy Nhơn", "Buôn Ma Thuột", "Pleiku", "Vinh", "Hạ Long",
        "Tam Kỳ", "Rạch Giá", "Mỹ Tho", "Biên Hòa", "Thủ Dầu Một",
    ]
    
    # Stadium name to province mapping (for stadiums named after cities)
    STADIUM_PROVINCE_MAP = {
        "Sân vận động Thống Nhất": "Hồ Chí Minh",
        "Sân vận động Hòa Xuân": "Đà Nẵng",
        "Sân vận động Thiên Trường": "Nam Định",
        "Sân vận động Quân khu 7": "Hồ Chí Minh",
        "Sân vận động An Giang": "An Giang",
        "Sân vận động Tiền Giang": "Tiền Giang",
        "Sân vận động Đồng Nai": "Đồng Nai",
        "Sân vận động Việt Trì": "Phú Thọ",
        "Sân vận động Cần Thơ": "Cần Thơ",
        "Sân vận động Cẩm Phả": "Quảng Ninh",
        "Sân vận động Thanh Hóa": "Thanh Hóa",
        "Sân vận động Hà Tĩnh": "Hà Tĩnh",
        "Sân vận động Phan Thiết": "Bình Thuận",
        "Sân vận động Bà Rịa": "Bà Rịa - Vũng Tàu",
        "Sân vận động Hoa Lư": "Hồ Chí Minh",
        "Sân vận động Đà Lạt": "Lâm Đồng",
        "Sân vận động Tây Ninh": "Tây Ninh",
        "Sân vận động Hòa Bình": "Hòa Bình",
        "Sân vận động Vĩnh Long": "Vĩnh Long",
        "Sân vận động Ninh Bình": "Ninh Bình",
        "Sân vận động Ninh Thuận": "Ninh Thuận",
        "Sân vận động Kon Tum": "Kon Tum",
        "Sân vận động Tam Kỳ": "Quảng Nam",
        "Sân vận động Long An": "Long An",
        "Sân vận động Hoài Đức": "Hà Nội",
        "Sân vận động Bình Dương": "Bình Dương",
        "Sân vận động Quốc gia Mỹ Đình": "Hà Nội",
        "Sân vận động Cột Cờ": "Hà Nội",
        "Sân vận động Thái Nguyên": "Thái Nguyên",
        "Sân vận động Quy Nhơn": "Bình Định",
        "Sân vận động Rạch Giá": "Kiên Giang",
        "Sân vận động Hàng Đẫy": "Hà Nội",
        "Sân vận động Lạch Tray": "Hải Phòng",
        "Sân vận động Gò Đậu": "Bình Dương",
        "Sân vận động 19 tháng 8": "Khánh Hòa",
        "Sân vận động Chi Lăng": "Đà Nẵng",
        "Sân vận động Pleiku": "Gia Lai",
        "Sân vận động Vinh": "Nghệ An",
        # New stadiums
        "Sân vận động Tự Do": "Thừa Thiên Huế",
        "Sân vận động Cao Lãnh": "Đồng Tháp",
        "Sân vận động Buôn Ma Thuột": "Đắk Lắk",
        "Sân vận động Bình Phước": "Bình Phước",
    }
    
    # Known stadium capacities (from various sources)
    KNOWN_CAPACITIES = {
        "Sân vận động Thống Nhất": 15000,
        "Sân vận động Hòa Xuân": 20500,
        "Sân vận động Quốc gia Mỹ Đình": 40192,
        "Sân vận động Hàng Đẫy": 22500,
        "Sân vận động Lạch Tray": 30000,
        "Sân vận động Cần Thơ": 50000,
        "Sân vận động Thanh Hóa": 15000,
        "Sân vận động Gò Đậu": 18250,
        "Sân vận động Pleiku": 12000,
        "Sân vận động Vinh": 18000,
        "Sân vận động Hà Tĩnh": 18000,
        "Sân vận động Long An": 20000,
        "Sân vận động Quân khu 7": 15000,
        "Sân vận động Tiền Giang": 10000,
        "Sân vận động Việt Trì": 20000,
        "Sân vận động Cột Cờ": 20000,
        "Sân vận động Hoa Lư": 6000,
        "Sân vận động An Giang": 15000,
        # New stadiums
        "Sân vận động Chi Lăng": 30000,
        "Sân vận động Tự Do": 25000,
        "Sân vận động Cao Lãnh": 15000,
        "Sân vận động Buôn Ma Thuột": 25000,
        "Sân vận động 19 tháng 8": 30000,
        "Sân vận động Bình Phước": 10000,
        "Sân vận động Ninh Bình": 22000,
        "Sân vận động Ninh Thuận": 10000,
        "Sân vận động Kon Tum": 8000,
        "Sân vận động Phan Thiết": 12000,
        "Sân vận động Bà Rịa": 15000,
        "Sân vận động Đà Lạt": 8000,
        "Sân vận động Quy Nhơn": 20000,
        "Sân vận động Hoài Đức": 5000,
    }
    
    def __init__(self):
        self.stats = {
            "total_loaded": 0,
            "valid_stadiums": 0,
            "removed_invalid": 0,
            "expanded_location": 0,
            "expanded_capacity": 0,
        }
    
    def load_data(self) -> List[Dict]:
        """Load stadiums from JSONL file."""
        input_file = PARSED_DATA_DIR / "stadiums.jsonl"
        
        if not input_file.exists():
            logger.error(f"File not found: {input_file}")
            return []
        
        records = []
        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse line: {e}")
        
        self.stats["total_loaded"] = len(records)
        logger.info(f"Loaded {len(records)} records from {input_file}")
        return records
    
    def is_valid_stadium(self, record: Dict) -> bool:
        """Check if a record is a valid stadium."""
        name = record.get("name", "").lower()
        wiki_title = record.get("wiki_title", "").lower()
        
        # Check for invalid keywords
        for keyword in self.INVALID_KEYWORDS:
            if keyword in name or keyword in wiki_title:
                self.stats["removed_invalid"] += 1
                logger.debug(f"Removed invalid: {record.get('name')}")
                return False
        
        # Must have "sân" in name (stadium in Vietnamese)
        if "sân" not in name:
            self.stats["removed_invalid"] += 1
            logger.debug(f"Removed (no 'sân'): {record.get('name')}")
            return False
        
        return True
    
    def extract_province(self, location: Optional[str], name: str) -> Optional[str]:
        """Extract province from location string or stadium name."""
        # First try from predefined map
        if name in self.STADIUM_PROVINCE_MAP:
            return self.STADIUM_PROVINCE_MAP[name]
        
        # Try to extract from location
        if location:
            for province in self.PROVINCES:
                if province.lower() in location.lower():
                    # Normalize some province names
                    if province in ["TP. Hồ Chí Minh", "TP.HCM", "Sài Gòn", "Thành phố Hồ Chí Minh"]:
                        return "Hồ Chí Minh"
                    if province == "Huế":
                        return "Thừa Thiên Huế"
                    if province == "Đà Lạt":
                        return "Lâm Đồng"
                    if province == "Nha Trang":
                        return "Khánh Hòa"
                    if province == "Vũng Tàu":
                        return "Bà Rịa - Vũng Tàu"
                    if province == "Phan Thiết":
                        return "Bình Thuận"
                    if province == "Quy Nhơn":
                        return "Bình Định"
                    if province == "Buôn Ma Thuột":
                        return "Đắk Lắk"
                    if province == "Pleiku":
                        return "Gia Lai"
                    if province == "Vinh":
                        return "Nghệ An"
                    if province == "Hạ Long":
                        return "Quảng Ninh"
                    if province == "Tam Kỳ":
                        return "Quảng Nam"
                    if province == "Rạch Giá":
                        return "Kiên Giang"
                    if province == "Mỹ Tho":
                        return "Tiền Giang"
                    if province == "Biên Hòa":
                        return "Đồng Nai"
                    if province == "Thủ Dầu Một":
                        return "Bình Dương"
                    return province
        
        # Try to extract province from stadium name
        name_lower = name.lower()
        for province in self.PROVINCES:
            if province.lower() in name_lower:
                return province
        
        return None
    
    def parse_capacity(self, capacity_str: any) -> Optional[int]:
        """Parse capacity from various formats."""
        if capacity_str is None:
            return None
        
        if isinstance(capacity_str, (int, float)):
            return int(capacity_str)
        
        if isinstance(capacity_str, str):
            # Remove non-numeric characters except comma and dot
            cleaned = re.sub(r"[^\d,.]", "", capacity_str)
            if cleaned:
                try:
                    # Handle European format (dot as thousands separator)
                    cleaned = cleaned.replace(".", "").replace(",", "")
                    return int(cleaned)
                except ValueError:
                    pass
        
        return None
    
    def clean_location(self, location: Optional[str]) -> Optional[str]:
        """Clean location string."""
        if not location:
            return None
        
        # Remove wiki markup
        location = re.sub(r"\{\{[^}]+\}\}", "", location)
        location = re.sub(r"\[\[([^\]|]+)\|?[^\]]*\]\]", r"\1", location)
        
        # Fix common errors
        # Tam Kỳ is in Quảng Nam, not Đà Nẵng
        if "Tam Kỳ" in location and "Đà Nẵng" in location:
            location = location.replace("Đà Nẵng", "Quảng Nam")
        
        # Thiên Trường is in Nam Định, not Ninh Bình
        if "Nam Định" in location and "Ninh Bình" in location:
            location = location.replace(", Ninh Bình", "")
        
        # Rạch Giá is in Kiên Giang, not An Giang
        if "Rạch Giá" in location and "An Giang" in location:
            location = location.replace("An Giang", "Kiên Giang")
        
        # Hòa Bình stadium location fix
        if "Hòa Bình" in location and "Phú Thọ" in location:
            location = location.replace("Phú Thọ", "Hòa Bình")
        
        return location.strip()
    
    def clean_record(self, record: Dict) -> Dict:
        """Clean a stadium record."""
        cleaned = record.copy()
        
        # Clean name
        name = cleaned.get("name", "")
        name = re.sub(r"\{\{[^}]+\}\}", "", name).strip()
        cleaned["name"] = name
        
        # Clean and fix location
        location = self.clean_location(cleaned.get("location"))
        if location != cleaned.get("location"):
            cleaned["location"] = location
        
        # Extract province
        province = self.extract_province(location, name)
        if province:
            cleaned["province"] = province
            if not location:
                self.stats["expanded_location"] += 1
        
        # Parse and expand capacity
        capacity = self.parse_capacity(cleaned.get("capacity"))
        if capacity is None and name in self.KNOWN_CAPACITIES:
            capacity = self.KNOWN_CAPACITIES[name]
            self.stats["expanded_capacity"] += 1
        cleaned["capacity"] = capacity
        
        # Clean surface
        surface = cleaned.get("surface")
        if surface:
            surface_lower = str(surface).lower()
            if "cỏ tự nhiên" in surface_lower or surface_lower == "cỏ":
                cleaned["surface_type"] = "Natural Grass"
            elif "cỏ nhân tạo" in surface_lower:
                cleaned["surface_type"] = "Artificial Turf"
            elif "hybrid" in surface_lower:
                cleaned["surface_type"] = "Hybrid"
            else:
                cleaned["surface_type"] = "Grass"
        else:
            cleaned["surface_type"] = None
        
        # Parse opened year
        opened = cleaned.get("opened")
        if opened:
            if isinstance(opened, (int, float)):
                cleaned["opened_year"] = int(opened)
            elif isinstance(opened, str):
                year_match = re.search(r"(\d{4})", str(opened))
                if year_match:
                    cleaned["opened_year"] = int(year_match.group(1))
                else:
                    cleaned["opened_year"] = None
        else:
            cleaned["opened_year"] = None
        
        # Extract canonical name
        cleaned["canonical_name"] = name
        
        return cleaned
    
    def clean(self) -> List[Dict]:
        """Clean stadium data."""
        records = self.load_data()
        
        if not records:
            return []
        
        cleaned_records = []
        
        for record in records:
            if self.is_valid_stadium(record):
                cleaned = self.clean_record(record)
                cleaned_records.append(cleaned)
                self.stats["valid_stadiums"] += 1
        
        logger.info(f"Cleaned to {len(cleaned_records)} valid stadiums")
        return cleaned_records
    
    def save(self, records: List[Dict], update_main: bool = True):
        """Save cleaned stadium data."""
        import pandas as pd
        
        # Save to JSONL
        output_jsonl = PARSED_DATA_DIR / "stadiums_clean.jsonl"
        with open(output_jsonl, "w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(records)} records to {output_jsonl}")
        
        # Select columns for CSV
        csv_columns = [
            "wiki_id", "name", "canonical_name", "location", "province",
            "capacity", "surface_type", "opened_year",
            "wiki_title", "wiki_url"
        ]
        
        df = pd.DataFrame(records)
        
        # Ensure all columns exist
        for col in csv_columns:
            if col not in df.columns:
                df[col] = None
        
        df = df[csv_columns]
        
        output_csv = PROCESSED_DATA_DIR / "stadiums_vn_clean.csv"
        df.to_csv(output_csv, index=False, encoding="utf-8")
        logger.info(f"Saved {len(df)} records to {output_csv}")
        
        if update_main:
            main_csv = PROCESSED_DATA_DIR / "stadiums_clean.csv"
            df.to_csv(main_csv, index=False, encoding="utf-8")
            logger.info(f"Updated main file: {main_csv}")
    
    def print_stats(self):
        """Print cleaning statistics."""
        print("\n" + "=" * 60)
        print("STADIUM CLEANING STATISTICS")
        print("=" * 60)
        print(f"Total records loaded:      {self.stats['total_loaded']}")
        print(f"Valid stadiums:            {self.stats['valid_stadiums']}")
        print(f"Removed (invalid):         {self.stats['removed_invalid']}")
        print(f"Expanded location:         {self.stats['expanded_location']}")
        print(f"Expanded capacity:         {self.stats['expanded_capacity']}")
        print("=" * 60)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean stadium data")
    parser.add_argument(
        "--update-main",
        action="store_true",
        help="Update the main stadiums_clean.csv file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without saving"
    )
    
    args = parser.parse_args()
    
    cleaner = StadiumCleaner()
    records = cleaner.clean()
    
    if args.dry_run:
        print("\n=== Valid Stadiums ===")
        for r in records:
            cap = r.get('capacity', 'N/A')
            prov = r.get('province', 'Unknown')
            print(f"  - {r.get('name')} | {prov} | Capacity: {cap}")
    else:
        cleaner.save(records, update_main=args.update_main)
    
    cleaner.print_stats()


if __name__ == "__main__":
    main()
