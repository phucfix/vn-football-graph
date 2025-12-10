"""
Entity Name Mapping for Vietnam Football Chatbot

Maps common short names/nicknames to full canonical names in the database
"""

# Player name mappings
PLAYER_NAME_MAP = {
    # Công Phượng
    "công phượng": "Nguyễn Công Phượng",
    "cong phuong": "Nguyễn Công Phượng",
    
    # Quang Hải
    "quang hải": "Nguyễn Quang Hải",
    "quang hai": "Nguyễn Quang Hải",
    
    # Văn Toàn
    "văn toàn": "Nguyễn Văn Toàn",
    "van toan": "Nguyễn Văn Toàn",
    
    # Văn Hậu
    "văn hậu": "Đoàn Văn Hậu",
    "van hau": "Đoàn Văn Hậu",
    
    # Tuấn Anh
    "tuấn anh": "Lương Xuân Trường",  # FIXME: Need to verify this mapping
    "tuan anh": "Lương Xuân Trường",
    
    # Tiến Linh
    "tiến linh": "Nguyễn Tiến Linh",
    "tien linh": "Nguyễn Tiến Linh",
    
    # Đức Chinh
    "đức chinh": "Hà Đức Chinh",
    "duc chinh": "Hà Đức Chinh",
    
    # Hùng Dũng
    "hùng dũng": "Đỗ Hùng Dũng",
    "hung dung": "Đỗ Hùng Dũng",
    
    # Xuân Trường
    "xuân trường": "Lương Xuân Trường",
    "xuan truong": "Lương Xuân Trường",
    
    # Văn Quyết
    "văn quyết": "Nguyễn Văn Quyết",
    "van quyet": "Nguyễn Văn Quyết",
}

# Club name mappings
CLUB_NAME_MAP = {
    # HAGL - Database has TWO entities!
    "hagl": "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
    "hoàng anh gia lai": "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
    "hoang anh gia lai": "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
    "gia lai": "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
    "câu lạc bộ hoàng anh gia lai": "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
    "clb hagl": "Câu lạc bộ bóng đá Hoàng Anh Gia Lai",
    # HAGL Academy (alternative)
    "học viện hagl": "Học viện Bóng đáHoàng Anh Gia Lai",
    "hagl academy": "Học viện Bóng đáHoàng Anh Gia Lai",
    
    # Hà Nội FC
    "hà nội fc": "Hà Nội",
    "ha noi fc": "Hà Nội",
    "clb hà nội": "Hà Nội",
    "hà nội": "Hà Nội",
    "hanoi fc": "Hà Nội",
    
    # Viettel
    "viettel": "Câu lạc bộ bóng đá Thể Công – Viettel",
    "the cong viettel": "Câu lạc bộ bóng đá Thể Công – Viettel",
    "thể công": "Câu lạc bộ bóng đá Thể Công – Viettel",
    
    # Other clubs
    "nam định": "Câu lạc bộ bóng đá Thép Xanh Nam Định",
    "thép xanh nam định": "Câu lạc bộ bóng đá Thép Xanh Nam Định",
    
    "slna": "Câu lạc bộ bóng đá Sông Lam Nghệ An",
    "sông lam nghệ an": "Câu lạc bộ bóng đá Sông Lam Nghệ An",
    "song lam nghe an": "Câu lạc bộ bóng đá Sông Lam Nghệ An",
    
    "bình dương": "Câu lạc bộ bóng đá Bình Dương",
    "binh duong": "Câu lạc bộ bóng đá Bình Dương",
    
    "đà nẵng": "Câu lạc bộ bóng đá SHB Đà Nẵng",
    "da nang": "Câu lạc bộ bóng đá SHB Đà Nẵng",
    "shb đà nẵng": "Câu lạc bộ bóng đá SHB Đà Nẵng",
}

# Coach name mappings
COACH_NAME_MAP = {
    "park hang-seo": "Park Hang-seo",
    "park hang seo": "Park Hang-seo",
    "hlv park": "Park Hang-seo",
}

# Province mappings (if needed)
PROVINCE_NAME_MAP = {
    "tp.hcm": "Thành phố Hồ Chí Minh",
    "tp hcm": "Thành phố Hồ Chí Minh",
    "sài gòn": "Thành phố Hồ Chí Minh",
    "hà nội": "Hà Nội",
    "ha noi": "Hà Nội",
    "nghệ an": "Nghệ An",
    "nghe an": "Nghệ An",
    "gia lai": "Gia Lai",
}

# Stadium mappings
STADIUM_NAME_MAP = {
    "mỹ đình": "Sân vận động Quốc gia Mỹ Đình",
    "my dinh": "Sân vận động Quốc gia Mỹ Đình",
    "sân mỹ đình": "Sân vận động Quốc gia Mỹ Đình",
    "svđ mỹ đình": "Sân vận động Quốc gia Mỹ Đình",
}


def normalize_entity_name(name: str, entity_type: str = "auto") -> str:
    """
    Normalize entity name to canonical form in database.
    
    Args:
        name: Original name from user query
        entity_type: "player", "club", "coach", "province", "stadium" or "auto"
    
    Returns:
        Canonical name for database lookup
    """
    name_lower = name.lower().strip()
    
    # Try specific type first
    if entity_type == "player" and name_lower in PLAYER_NAME_MAP:
        return PLAYER_NAME_MAP[name_lower]
    elif entity_type == "club" and name_lower in CLUB_NAME_MAP:
        return CLUB_NAME_MAP[name_lower]
    elif entity_type == "coach" and name_lower in COACH_NAME_MAP:
        return COACH_NAME_MAP[name_lower]
    elif entity_type == "province" and name_lower in PROVINCE_NAME_MAP:
        return PROVINCE_NAME_MAP[name_lower]
    elif entity_type == "stadium" and name_lower in STADIUM_NAME_MAP:
        return STADIUM_NAME_MAP[name_lower]
    
    # Auto-detect: try all mappings
    if entity_type == "auto":
        if name_lower in PLAYER_NAME_MAP:
            return PLAYER_NAME_MAP[name_lower]
        if name_lower in CLUB_NAME_MAP:
            return CLUB_NAME_MAP[name_lower]
        if name_lower in COACH_NAME_MAP:
            return COACH_NAME_MAP[name_lower]
        if name_lower in STADIUM_NAME_MAP:
            return STADIUM_NAME_MAP[name_lower]
        if name_lower in PROVINCE_NAME_MAP:
            return PROVINCE_NAME_MAP[name_lower]
    
    # Return original if no mapping found
    return name


def get_all_variations(canonical_name: str) -> list:
    """
    Get all known variations of a canonical name.
    
    Args:
        canonical_name: The canonical name in database
    
    Returns:
        List of all variations including the canonical name
    """
    variations = [canonical_name]
    
    # Check player names
    for short, full in PLAYER_NAME_MAP.items():
        if full == canonical_name:
            variations.append(short)
    
    # Check club names
    for short, full in CLUB_NAME_MAP.items():
        if full == canonical_name:
            variations.append(short)
    
    # Check coach names
    for short, full in COACH_NAME_MAP.items():
        if full == canonical_name:
            variations.append(short)
    
    return list(set(variations))
