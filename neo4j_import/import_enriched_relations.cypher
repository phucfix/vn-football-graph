// ============================================
// IMPORT ENRICHED RELATIONS
// Generated from text analysis
// Total: 834 relations
// ============================================

// Sample relations to import (run one by one)


// Relation 1: Nguyễn Minh Quang --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 19838704})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 2: câu lạc bộ bóng đá Sông Lam Nghệ An --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 31345})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 3: câu lạc bộ bóng đá SHB Đà Nẵng --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 78806})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 4: câu lạc bộ bóng đá Sài Gòn --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 445434})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 5: Đặng Phương Nam --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 11629119})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 6: Đặng Phương Nam --[COMPETED_IN]--> Giải bóng đá vô địch quốc gia
MATCH (s:Player {wiki_id: 11629119})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 7: câu lạc bộ bóng đá Đồng Tháp --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 78275})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 8: câu lạc bộ bóng đá Hoàng Anh Gia Lai --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 19834914})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 9: Công an Nhân dân --[COMPETES_IN]--> Giải bóng đá hạng ba quốc gia
MATCH (s:Club {wiki_id: 3232362})
MATCH (o:Competition {wiki_id: 32576})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 10: Hà Nội --[COMPETES_IN]--> Giải bóng đá hạng ba quốc gia
MATCH (s:Club {wiki_id: 845324})
MATCH (o:Competition {wiki_id: 32576})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 11: Hà Nội --[COMPETES_IN]--> giải bóng đá hạng nhì quốc gia
MATCH (s:Club {wiki_id: 845324})
MATCH (o:Competition {wiki_id: 3215922})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 12: Phạm Hoàng Lâm --[PLAYED_FOR]--> Bắc Ninh
MATCH (s:Player {wiki_id: 3281906})
MATCH (o:Club {wiki_id: 14899593})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 13: Hà Nội --[COMPETES_IN]--> Giải bóng đá nữ vô địch quốc gia
MATCH (s:Club {wiki_id: 845324})
MATCH (o:Competition {wiki_id: 3218165})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 14: Nguyễn Đình Bảo --[PLAYED_FOR]--> Câu lạc bộ bóng đá Quảng Nam
MATCH (s:Player {wiki_id: 19605180})
MATCH (o:Club {wiki_id: 502890})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 15: Nguyễn Đình Bảo --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 19605180})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 16: Nguyễn Đình Bảo --[PLAYED_FOR_NATIONAL]--> U-21 Việt Nam
MATCH (s:Player {wiki_id: 19605180})
MATCH (o:NationalTeam {wiki_id: 3391550})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 17: Hà Minh Tuấn --[PLAYED_FOR]--> câu lạc bộ bóng đá SHB Đà Nẵng
MATCH (s:Player {wiki_id: 492247})
MATCH (o:Club {wiki_id: 78806})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 18: Hà Minh Tuấn --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 492247})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 19: Nguyễn Phúc Nguyên Chương --[PLAYED_FOR_NATIONAL]--> đội tuyển Việt Nam
MATCH (s:Player {wiki_id: 507060})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 20: câu lạc bộ bóng đá Thành phố Hồ Chí Minh --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 1407420})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 21: Nguyễn Văn Quyết --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 913135})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 22: Nguyễn Văn Quyết --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 913135})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 23: Hà Nội --[COMPETES_IN]--> V.League 1
MATCH (s:Club {wiki_id: 845324})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 24: Hoàng Vũ Samson --[PLAYED_FOR]--> Hồng Lĩnh Hà Tĩnh
MATCH (s:Player {wiki_id: 814341})
MATCH (o:Club {wiki_id: 14539268})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 25: Hoàng Vũ Samson --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 814341})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 26: Phan Thanh Hùng --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 528091})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 27: câu lạc bộ bóng đá Thành phố Hồ Chí Minh --[COMPETES_IN]--> Cúp bóng đá Thành phố Hồ Chí Minh
MATCH (s:Club {wiki_id: 1407420})
MATCH (o:Competition {wiki_id: 64377})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 28: Đỗ Khải --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 1566400})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 29: Nguyễn Công Nhật --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 15275629})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 30: Nguyễn Công Nhật --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 15275629})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 31: câu lạc bộ bóng đá Huế --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 524030})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 32: Hà Nội --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 845324})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 33: Lê Công Vinh --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 79957})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 34: Nguyễn Tiến Linh --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3680698})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 35: Nguyễn Tiến Linh --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 3680698})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 36: Hồng Lĩnh Hà Tĩnh --[COMPETES_IN]--> V.League 1
MATCH (s:Club {wiki_id: 14539268})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 37: Hồng Lĩnh Hà Tĩnh --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 14539268})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 38: Hoàng Văn Bình --[PLAYED_FOR]--> Câu lạc bộ bóng đá Sông Lam Nghệ An
MATCH (s:Player {wiki_id: 3277265})
MATCH (o:Club {wiki_id: 31345})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 39: Hoàng Văn Bình --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3277265})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 40: Nguyễn Văn Toản --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 15984668})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 41: Nguyễn Văn Toản --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 15984668})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 42: Bùi Tiến Dũng --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3690264})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 43: câu lạc bộ bóng đá Hải Phòng --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 188791})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 44: Ngô Xuân Sơn --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 19779550})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 45: Bắc Ninh --[COMPETES_IN]--> Giải bóng đá Hạng nhì Quốc gia
MATCH (s:Club {wiki_id: 14899593})
MATCH (o:Competition {wiki_id: 3215922})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 46: Đinh Thanh Bình --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 14762430})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 47: Đinh Thanh Bình --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 14762430})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 48: Bắc Ninh --[COMPETES_IN]--> Giải bóng đá Hạng Ba Quốc gia
MATCH (s:Club {wiki_id: 14899593})
MATCH (o:Competition {wiki_id: 32576})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 49: Doãn Ngọc Tân --[PLAYED_FOR]--> Đông Á Thanh Hóa
MATCH (s:Player {wiki_id: 19431704})
MATCH (o:Club {wiki_id: 445930})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 50: Doãn Ngọc Tân --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 19431704})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 51: Doãn Ngọc Tân --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 19431704})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 52: Đông Á Thanh Hóa --[COMPETES_IN]--> V.League 1
MATCH (s:Club {wiki_id: 445930})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 53: Phùng Công Minh --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 19803085})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 54: Xi măng The Vissai Ninh Bình --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 139260})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 55: Xi măng The Vissai Ninh Bình --[COMPETES_IN]--> Cúp bóng đá châu Á 2007
MATCH (s:Club {wiki_id: 139260})
MATCH (o:Competition {wiki_id: 71590})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 56: Hoàng Anh Tuấn --[PLAYED_FOR_NATIONAL]--> đội tuyển Việt Nam 
MATCH (s:Player {wiki_id: 1060502})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 57: Phan Thanh Hùng --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 528091})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 58: Hoàng Anh Tuấn --[COMPETED_IN]--> Giải vô địch bóng đá U-18 Đông Nam Á 2019
MATCH (s:Player {wiki_id: 1060502})
MATCH (o:Competition {wiki_id: 14702044})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 59: a Hoàng --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 12024336})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 60: câu lạc bộ bóng đá Khánh Hòa --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 54973})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 61: Nguyễn Quốc Long --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 16318221})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 62: Cao Sỹ Cường --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 3214444})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 63: Đoàn Việt Cường --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 80098})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 64: Cao Sỹ Cường --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3214444})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 65: Nguyễn Quốc Long --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 16318221})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 66: Đoàn Việt Cường --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 80098})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 67: Huỳnh Kesley Alves --[PLAYED_FOR]--> Định Hướng Phú Nhuận
MATCH (s:Player {wiki_id: 422045})
MATCH (o:Club {wiki_id: 19885859})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 68: Phan Thanh Hưng --[PLAYED_FOR]--> Câu lạc bộ bóng đá Quảng Nam
MATCH (s:Player {wiki_id: 1469801})
MATCH (o:Club {wiki_id: 502890})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 69: Phan Thanh Hưng --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 1469801})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 70: Lê Thụy Hải --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 504902})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 71: Phan Văn Hiếu --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 19543065})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 72: Công an Hà Nội --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 37020})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 73: Nguyễn Thanh Bình --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 19653210})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 74: Nguyễn Thanh Thắng --[PLAYED_FOR]--> Đông Á Thanh Hóa
MATCH (s:Player {wiki_id: 3705942})
MATCH (o:Club {wiki_id: 445930})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 75: Nguyễn Thanh Thắng --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 3705942})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 76: Nguyễn Thanh Nhân --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 19754791})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 77: Nguyễn Thanh Nhân --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 19754791})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 78: Nguyễn Thanh Nhân --[PLAYED_FOR]--> câu lạc bộ bóng đá Cần Thơ
MATCH (s:Player {wiki_id: 19754791})
MATCH (o:Club {wiki_id: 314518})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 79: Nguyễn Thanh Nhân --[PLAYED_FOR]--> câu lạc bộ bóng đá Hoàng Anh Gia Lai
MATCH (s:Player {wiki_id: 19754791})
MATCH (o:Club {wiki_id: 19834914})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 80: Nguyễn Thanh Nhân --[PLAYED_FOR_NATIONAL]--> U-23 Việt Nam
MATCH (s:Player {wiki_id: 19754791})
MATCH (o:NationalTeam {wiki_id: 822084})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 81: Nguyễn Thanh Nhân --[COMPETED_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Player {wiki_id: 19754791})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 82: câu lạc bộ bóng đá Cần Thơ --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 314518})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 83: câu lạc bộ bóng đá Quảng Nam --[COMPETES_IN]--> giải bóng đá vô địch quốc gia
MATCH (s:Club {wiki_id: 502890})
MATCH (o:Competition {wiki_id: 25636})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 84: Đoàn Hải Quân --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 19807477})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 85: Nguyễn Xuân Nam --[PLAYED_FOR]--> Công An Nhân Dân
MATCH (s:Player {wiki_id: 3254500})
MATCH (o:Club {wiki_id: 3232362})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 86: Nguyễn Xuân Nam --[PLAYED_FOR]--> Công an Hà Nội
MATCH (s:Player {wiki_id: 3254500})
MATCH (o:Club {wiki_id: 37020})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 87: Giáp Tuấn Dương --[PLAYED_FOR]--> Công an Hà Nội
MATCH (s:Player {wiki_id: 19799470})
MATCH (o:Club {wiki_id: 37020})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 88: Giáp Tuấn Dương --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 19799470})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 89: Công an Hà Nội --[COMPETES_IN]--> V.League 1
MATCH (s:Club {wiki_id: 37020})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETES_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_club_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 90: Nguyễn Quang Hải --[PLAYED_FOR]--> Công an Hà Nội
MATCH (s:Player {wiki_id: 3521074})
MATCH (o:Club {wiki_id: 37020})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 91: Nguyễn Quang Hải --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3521074})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 92: Nguyễn Quang Hải --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 3521074})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 93: Nguyễn Quang Hải --[PLAYED_FOR]--> Hà Nội
MATCH (s:Player {wiki_id: 3521074})
MATCH (o:Club {wiki_id: 845324})
MERGE (s)-[r:PLAYED_FOR]->(o)
ON CREATE SET r.confidence = 0.75, r.pattern = 'co_occurrence_player_club', r.source = 'enrichment', r.created_at = datetime();


// Relation 94: Hoàng Anh Tuấn --[COMPETED_IN]--> V.League 1
MATCH (s:Player {wiki_id: 1060502})
MATCH (o:Competition {wiki_id: 13078574})
MERGE (s)-[r:COMPETED_IN]->(o)
ON CREATE SET r.confidence = 0.7, r.pattern = 'co_occurrence_player_competition', r.source = 'enrichment', r.created_at = datetime();


// Relation 95: Hà Đức Chinh --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3510715})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 96: Nguyễn Hữu Thắng --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 522693})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 97: Lương Xuân Trường --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3254295})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 98: Nguyễn Công Phượng --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 3140580})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 99: Dương Thị Vân --[PLAYED_FOR_NATIONAL]--> nữ Việt Nam
MATCH (s:Player {wiki_id: 17132747})
MATCH (o:NationalTeam {wiki_id: 76837})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();


// Relation 100: Dương Thị Vân --[PLAYED_FOR_NATIONAL]--> Việt Nam
MATCH (s:Player {wiki_id: 17132747})
MATCH (o:NationalTeam {wiki_id: 21785})
MERGE (s)-[r:PLAYED_FOR_NATIONAL]->(o)
ON CREATE SET r.confidence = 0.8, r.pattern = 'co_occurrence_player_national', r.source = 'enrichment', r.created_at = datetime();
