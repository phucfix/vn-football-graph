# VIETNAM FOOTBALL KNOWLEDGE GRAPH - NETWORK STATISTICS

**Generated:** 2025-12-09 10:59:11

---

## 📊 OVERVIEW

### Graph Size
- **Total Nodes:** 1,060
- **Total Relationships:** 36,184
- **Graph Density:** 3.2204%

---

## 🎯 NODE STATISTICS

### Node Distribution
- **Player:** 526
- **Competition:** 272
- **Club:** 78
- **Province:** 67
- **Coach:** 63
- **Stadium:** 41
- **NationalTeam:** 13

---

## 🔗 RELATIONSHIP STATISTICS

### Relationship Distribution
- **NATIONAL_TEAMMATE:** 24,498
- **TEAMMATE:** 8,104
- **PLAYED_FOR:** 1,060
- **PLAYED_FOR_NATIONAL:** 683
- **PLAYED_SAME_CLUBS:** 519
- **BORN_IN:** 433
- **FROM_PROVINCE:** 415
- **SAME_PROVINCE:** 130
- **COACHED:** 95
- **UNDER_COACH:** 53
- **HOME_STADIUM:** 51
- **BASED_IN:** 51
- **COMPETES_IN:** 51
- **LOCATED_IN:** 41

---

## ⚽ PLAYER STATISTICS

### Overview
- **Total Players:** 526
- **Male Players:** 526 (100.0%)
- **Female Players:** 0 (0.0%)
- **National Team Players:** 392 (74.5%)

### Top 5 Positions
1. **MF:** 143 players
1. **DF:** 104 players
1. **FW:** 65 players
1. **GK:** 65 players
1. **CB:** 54 players

### Top 5 Birth Provinces
1. **Nghệ An:** 60 players
2. **Hà Nội:** 46 players
3. **Thanh Hóa:** 38 players
4. **Thừa Thiên – Huế:** 25 players
5. **Thái Bình:** 23 players

---

## 🏟️ CLUB STATISTICS

### Overview
- **Total Clubs:** 78

### Top 5 Clubs by Player Count
1. **Hà Nội:** 102 players (all-time)
2. **Học viện Bóng đáHoàng Anh Gia Lai:** 66 players (all-time)
3. **Câu lạc bộ bóng đá Công an Thành phố Hồ Chí Minh:** 64 players (all-time)
4. **Đông Á Thanh Hóa:** 62 players (all-time)
5. **Câu lạc bộ bóng đá Thép Xanh Nam Định:** 58 players (all-time)

---

## 📈 CHARTS

All visualization charts are saved in `reports/charts/`:

1. **01_node_distribution.png** - Node types distribution
2. **02_relationship_distribution.png** - Relationship types distribution
3. **03_gender_distribution.png** - Player gender breakdown
4. **04_position_distribution.png** - Player positions
5. **05_province_distribution.png** - Players by birth province
6. **06_age_distribution.png** - Player age groups
7. **07_career_length_distribution.png** - Career lengths
8. **08_top_clubs.png** - Top clubs by players
9. **09_degree_distribution.png** - Network connectivity
10. **10_temporal_trends.png** - Historical trends
11. **11_top_connected_players.png** - Most connected players

---

## 📌 KEY INSIGHTS

### Network Characteristics
- **Average Teammates per Player:** {sum(self.stats['network']['degree_distribution'].values()) / players['total']:.1f}
- **Most Connected Players:** See chart #11

### Geographic Distribution
- Players come from **{len(players['by_province'])}** different provinces
- Top province contributes **{list(players['by_province'].values())[0]}** players

### Career Patterns
- Career length data available for players with complete records
- See chart #7 for distribution

---

**End of Report**
