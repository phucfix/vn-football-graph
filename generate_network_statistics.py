#!/usr/bin/env python3
"""
Network Statistics and Visualization Generator

Tạo thống kê chi tiết và biểu đồ về Vietnam Football Knowledge Graph.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# Plotting libraries
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import seaborn as sns
import pandas as pd
import numpy as np

# Neo4j
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Setup
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env')

# Output directories
REPORTS_DIR = BASE_DIR / 'reports'
CHARTS_DIR = REPORTS_DIR / 'charts'
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Styling
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['font.family'] = 'DejaVu Sans'


class NetworkStatistics:
    """Generate comprehensive network statistics and visualizations."""
    
    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv('NEO4J_URI'),
            auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
        )
        self.stats = {}
    
    def close(self):
        self.driver.close()
    
    # =============================================================================
    # DATA COLLECTION
    # =============================================================================
    
    def collect_all_statistics(self):
        """Collect all statistics from Neo4j."""
        print("📊 Collecting statistics from Neo4j...")
        
        with self.driver.session() as session:
            self.stats['nodes'] = self._get_node_counts(session)
            self.stats['relationships'] = self._get_relationship_counts(session)
            self.stats['players'] = self._get_player_statistics(session)
            self.stats['clubs'] = self._get_club_statistics(session)
            self.stats['provinces'] = self._get_province_statistics(session)
            self.stats['network'] = self._get_network_metrics(session)
            self.stats['temporal'] = self._get_temporal_statistics(session)
        
        print("✅ Statistics collected!")
        return self.stats
    
    def _get_node_counts(self, session) -> Dict:
        """Get node counts by label."""
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)
        return {r['label']: r['count'] for r in result}
    
    def _get_relationship_counts(self, session) -> Dict:
        """Get relationship counts by type."""
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        return {r['type']: r['count'] for r in result}
    
    def _get_player_statistics(self, session) -> Dict:
        """Get detailed player statistics."""
        stats = {}
        
        # Total players
        result = session.run("MATCH (p:Player) RETURN count(p) as total")
        stats['total'] = result.single()['total']
        
        # Gender distribution (approximate từ name)
        result = session.run("""
            MATCH (p:Player)
            WHERE p.name CONTAINS 'nữ' OR p.wiki_title CONTAINS 'nữ'
            RETURN count(p) as female
        """)
        stats['female'] = result.single()['female']
        stats['male'] = stats['total'] - stats['female']
        
        # Position distribution
        result = session.run("""
            MATCH (p:Player)
            WHERE p.position IS NOT NULL
            RETURN p.position as position, count(p) as count
            ORDER BY count DESC
        """)
        stats['by_position'] = {r['position']: r['count'] for r in result}
        
        # Birth province distribution
        result = session.run("""
            MATCH (p:Player)-[:BORN_IN]->(prov:Province)
            RETURN prov.name as province, count(p) as count
            ORDER BY count DESC
            LIMIT 15
        """)
        stats['by_province'] = {r['province']: r['count'] for r in result}
        
        # National team players
        result = session.run("""
            MATCH (p:Player)
            WHERE p.is_national_team_player = true
            RETURN count(p) as count
        """)
        stats['national_team'] = result.single()['count']
        
        # Career length distribution
        result = session.run("""
            MATCH (p:Player)
            WHERE p.career_start_year IS NOT NULL AND p.career_end_year IS NOT NULL
            WITH p, (p.career_end_year - p.career_start_year) as years
            WHERE years > 0 AND years < 30
            RETURN years, count(p) as count
            ORDER BY years
        """)
        stats['career_length'] = {r['years']: r['count'] for r in result}
        
        # Age distribution (approximate)
        result = session.run("""
            MATCH (p:Player)
            WHERE p.birth_year IS NOT NULL
            WITH p, (2025 - p.birth_year) as age
            WHERE age > 15 AND age < 60
            RETURN 
                CASE 
                    WHEN age < 20 THEN 'U20'
                    WHEN age < 25 THEN '20-24'
                    WHEN age < 30 THEN '25-29'
                    WHEN age < 35 THEN '30-34'
                    ELSE '35+'
                END as age_group,
                count(p) as count
            ORDER BY age_group
        """)
        stats['age_distribution'] = {r['age_group']: r['count'] for r in result}
        
        return stats
    
    def _get_club_statistics(self, session) -> Dict:
        """Get club statistics."""
        stats = {}
        
        # Total clubs
        result = session.run("MATCH (c:Club) RETURN count(c) as total")
        stats['total'] = result.single()['total']
        
        # Clubs by number of players
        result = session.run("""
            MATCH (c:Club)<-[:PLAYED_FOR]-(p:Player)
            RETURN c.name as club, count(DISTINCT p) as player_count
            ORDER BY player_count DESC
            LIMIT 15
        """)
        stats['by_player_count'] = {r['club']: r['player_count'] for r in result}
        
        # Clubs by province
        result = session.run("""
            MATCH (c:Club)-[:CLUB_BASED_IN]->(prov:Province)
            RETURN prov.name as province, count(c) as count
            ORDER BY count DESC
        """)
        stats['by_province'] = {r['province']: r['count'] for r in result}
        
        return stats
    
    def _get_province_statistics(self, session) -> Dict:
        """Get province statistics."""
        stats = {}
        
        # Total provinces
        result = session.run("MATCH (p:Province) RETURN count(p) as total")
        stats['total'] = result.single()['total']
        
        # Players per province (birthplace)
        result = session.run("""
            MATCH (prov:Province)<-[:BORN_IN]-(p:Player)
            RETURN prov.name as province, count(p) as count
            ORDER BY count DESC
            LIMIT 15
        """)
        stats['player_birthplace'] = {r['province']: r['count'] for r in result}
        
        return stats
    
    def _get_network_metrics(self, session) -> Dict:
        """Get network topology metrics."""
        stats = {}
        
        # Degree distribution (TEAMMATE relationships)
        result = session.run("""
            MATCH (p:Player)-[:TEAMMATE]-(teammate:Player)
            WITH p, count(DISTINCT teammate) as degree
            RETURN 
                CASE
                    WHEN degree < 5 THEN '0-4'
                    WHEN degree < 10 THEN '5-9'
                    WHEN degree < 20 THEN '10-19'
                    WHEN degree < 50 THEN '20-49'
                    ELSE '50+'
                END as degree_range,
                count(p) as count
            ORDER BY degree_range
        """)
        stats['degree_distribution'] = {r['degree_range']: r['count'] for r in result}
        
        # Top connected players
        result = session.run("""
            MATCH (p:Player)-[:TEAMMATE]-(teammate:Player)
            RETURN p.name as player, count(DISTINCT teammate) as connections
            ORDER BY connections DESC
            LIMIT 20
        """)
        stats['top_connected'] = [(r['player'], r['connections']) for r in result]
        
        # Players with most clubs
        result = session.run("""
            MATCH (p:Player)-[:PLAYED_FOR]->(c:Club)
            RETURN p.name as player, count(DISTINCT c) as clubs
            ORDER BY clubs DESC
            LIMIT 15
        """)
        stats['most_clubs'] = [(r['player'], r['clubs']) for r in result]
        
        return stats
    
    def _get_temporal_statistics(self, session) -> Dict:
        """Get temporal/historical statistics."""
        stats = {}
        
        # Players by debut year
        result = session.run("""
            MATCH (p:Player)
            WHERE p.career_start_year IS NOT NULL
            WITH p.career_start_year as year, count(p) as count
            WHERE year >= 1990 AND year <= 2025
            RETURN year, count
            ORDER BY year
        """)
        stats['debut_by_year'] = {r['year']: r['count'] for r in result}
        
        # Active players by year (simplified)
        result = session.run("""
            MATCH (p:Player)
            WHERE p.career_start_year IS NOT NULL AND p.career_end_year IS NULL
            WITH p.career_start_year as year, count(p) as count
            WHERE year >= 2010 AND year <= 2025
            RETURN year, count
            ORDER BY year
        """)
        stats['still_active'] = {r['year']: r['count'] for r in result}
        
        return stats
    
    # =============================================================================
    # VISUALIZATION
    # =============================================================================
    
    def create_all_charts(self):
        """Create all visualization charts."""
        print("\n📈 Generating charts...")
        
        self.plot_node_distribution()
        self.plot_relationship_distribution()
        self.plot_gender_distribution()
        self.plot_position_distribution()
        self.plot_province_distribution()
        self.plot_age_distribution()
        self.plot_career_length_distribution()
        self.plot_top_clubs()
        self.plot_degree_distribution()
        self.plot_temporal_trends()
        self.plot_top_connected_players()
        
        print(f"✅ Charts saved to {CHARTS_DIR}/")
    
    def plot_node_distribution(self):
        """Plot node type distribution."""
        data = self.stats['nodes']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        labels = list(data.keys())
        values = list(data.values())
        colors = sns.color_palette("husl", len(labels))
        
        bars = ax.barh(labels, values, color=colors)
        ax.set_xlabel('Count')
        ax.set_title('Node Distribution by Type', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{int(width)}',
                   ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '01_node_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_relationship_distribution(self):
        """Plot relationship type distribution."""
        data = self.stats['relationships']
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Sort by count
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)
        labels = [item[0] for item in sorted_data]
        values = [item[1] for item in sorted_data]
        colors = sns.color_palette("coolwarm", len(labels))
        
        bars = ax.barh(labels, values, color=colors)
        ax.set_xlabel('Count')
        ax.set_title('Relationship Distribution by Type', fontsize=14, fontweight='bold')
        ax.set_xscale('log')  # Log scale vì NATIONAL_TEAMMATE rất lớn
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{int(width):,}',
                   ha='left', va='center', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '02_relationship_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_gender_distribution(self):
        """Plot player gender distribution."""
        male = self.stats['players']['male']
        female = self.stats['players']['female']
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Pie chart
        labels = ['Male', 'Female']
        sizes = [male, female]
        colors = ['#3498db', '#e74c3c']
        explode = (0.05, 0.05)
        
        ax1.pie(sizes, explode=explode, labels=labels, colors=colors,
                autopct='%1.1f%%', shadow=True, startangle=90)
        ax1.set_title('Player Gender Distribution', fontsize=14, fontweight='bold')
        
        # Bar chart
        ax2.bar(labels, sizes, color=colors)
        ax2.set_ylabel('Count')
        ax2.set_title('Player Count by Gender', fontsize=14, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        
        for i, v in enumerate(sizes):
            ax2.text(i, v + 5, str(v), ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '03_gender_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_position_distribution(self):
        """Plot player position distribution."""
        data = self.stats['players']['by_position']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Sort and take top positions
        sorted_data = sorted(data.items(), key=lambda x: x[1], reverse=True)[:12]
        labels = [item[0] for item in sorted_data]
        values = [item[1] for item in sorted_data]
        colors = sns.color_palette("Set2", len(labels))
        
        bars = ax.bar(labels, values, color=colors)
        ax.set_ylabel('Number of Players')
        ax.set_xlabel('Position')
        ax.set_title('Player Distribution by Position', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45, ha='right')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '04_position_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_province_distribution(self):
        """Plot players by birth province."""
        data = self.stats['players']['by_province']
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        labels = list(data.keys())[:15]
        values = list(data.values())[:15]
        colors = sns.color_palette("viridis", len(labels))
        
        bars = ax.barh(labels, values, color=colors)
        ax.set_xlabel('Number of Players')
        ax.set_title('Top 15 Provinces by Player Birthplace', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{int(width)}',
                   ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '05_province_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_age_distribution(self):
        """Plot player age distribution."""
        data = self.stats['players']['age_distribution']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        labels = list(data.keys())
        values = list(data.values())
        colors = sns.color_palette("RdYlGn_r", len(labels))
        
        bars = ax.bar(labels, values, color=colors)
        ax.set_ylabel('Number of Players')
        ax.set_xlabel('Age Group')
        ax.set_title('Player Age Distribution (2025)', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '06_age_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_career_length_distribution(self):
        """Plot career length distribution."""
        data = self.stats['players']['career_length']
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        years = list(data.keys())
        counts = list(data.values())
        
        ax.bar(years, counts, color='steelblue', alpha=0.7)
        ax.set_xlabel('Career Length (years)')
        ax.set_ylabel('Number of Players')
        ax.set_title('Player Career Length Distribution', fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # Add statistics
        avg_career = sum(y * c for y, c in zip(years, counts)) / sum(counts)
        ax.axvline(avg_career, color='red', linestyle='--', linewidth=2, 
                  label=f'Average: {avg_career:.1f} years')
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '07_career_length_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_top_clubs(self):
        """Plot top clubs by player count."""
        data = self.stats['clubs']['by_player_count']
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        labels = list(data.keys())[:15]
        values = list(data.values())[:15]
        colors = sns.color_palette("rocket", len(labels))
        
        bars = ax.barh(labels, values, color=colors)
        ax.set_xlabel('Number of Players (All-Time)')
        ax.set_title('Top 15 Clubs by Total Player Count', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{int(width)}',
                   ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '08_top_clubs.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_degree_distribution(self):
        """Plot network degree distribution."""
        data = self.stats['network']['degree_distribution']
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        labels = list(data.keys())
        values = list(data.values())
        colors = sns.color_palette("mako", len(labels))
        
        bars = ax.bar(labels, values, color=colors)
        ax.set_ylabel('Number of Players')
        ax.set_xlabel('Number of Teammates')
        ax.set_title('Player Connectivity Distribution (TEAMMATE relationships)', 
                    fontsize=14, fontweight='bold')
        ax.grid(axis='y', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}',
                   ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '09_degree_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_temporal_trends(self):
        """Plot temporal trends."""
        data = self.stats['temporal']['debut_by_year']
        
        fig, ax = plt.subplots(figsize=(14, 6))
        
        years = sorted(data.keys())
        counts = [data[y] for y in years]
        
        ax.plot(years, counts, marker='o', linewidth=2, markersize=5, color='#2ecc71')
        ax.fill_between(years, counts, alpha=0.3, color='#2ecc71')
        ax.set_xlabel('Year')
        ax.set_ylabel('Number of Players')
        ax.set_title('Player Career Debuts by Year (1990-2025)', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '10_temporal_trends.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_top_connected_players(self):
        """Plot top connected players."""
        data = self.stats['network']['top_connected']
        
        fig, ax = plt.subplots(figsize=(12, 10))
        
        players = [item[0] for item in data[:20]]
        connections = [item[1] for item in data[:20]]
        colors = sns.color_palette("flare", len(players))
        
        bars = ax.barh(players, connections, color=colors)
        ax.set_xlabel('Number of Teammates')
        ax.set_title('Top 20 Most Connected Players', fontsize=14, fontweight='bold')
        ax.grid(axis='x', alpha=0.3)
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{int(width)}',
                   ha='left', va='center', fontsize=8)
        
        plt.tight_layout()
        plt.savefig(CHARTS_DIR / '11_top_connected_players.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    # =============================================================================
    # REPORTS
    # =============================================================================
    
    def generate_markdown_report(self):
        """Generate comprehensive markdown report."""
        print("\n📝 Generating markdown report...")
        
        report_path = REPORTS_DIR / 'network_statistics.md'
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(self._generate_report_content())
        
        print(f"✅ Report saved to {report_path}")
    
    def _generate_report_content(self) -> str:
        """Generate report content."""
        nodes = self.stats['nodes']
        rels = self.stats['relationships']
        players = self.stats['players']
        clubs = self.stats['clubs']
        
        content = f"""# VIETNAM FOOTBALL KNOWLEDGE GRAPH - NETWORK STATISTICS

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 OVERVIEW

### Graph Size
- **Total Nodes:** {sum(nodes.values()):,}
- **Total Relationships:** {sum(rels.values()):,}
- **Graph Density:** {(sum(rels.values()) / (sum(nodes.values()) ** 2) * 100):.4f}%

---

## 🎯 NODE STATISTICS

### Node Distribution
"""
        
        for label, count in sorted(nodes.items(), key=lambda x: x[1], reverse=True):
            content += f"- **{label}:** {count:,}\n"
        
        content += f"""
---

## 🔗 RELATIONSHIP STATISTICS

### Relationship Distribution
"""
        
        for rel_type, count in sorted(rels.items(), key=lambda x: x[1], reverse=True):
            content += f"- **{rel_type}:** {count:,}\n"
        
        content += f"""
---

## ⚽ PLAYER STATISTICS

### Overview
- **Total Players:** {players['total']:,}
- **Male Players:** {players['male']:,} ({players['male']/players['total']*100:.1f}%)
- **Female Players:** {players['female']:,} ({players['female']/players['total']*100:.1f}%)
- **National Team Players:** {players['national_team']:,} ({players['national_team']/players['total']*100:.1f}%)

### Top 5 Positions
"""
        
        sorted_positions = sorted(players['by_position'].items(), key=lambda x: x[1], reverse=True)[:5]
        for pos, count in sorted_positions:
            content += f"1. **{pos}:** {count} players\n"
        
        content += f"""
### Top 5 Birth Provinces
"""
        
        for i, (prov, count) in enumerate(list(players['by_province'].items())[:5], 1):
            content += f"{i}. **{prov}:** {count} players\n"
        
        content += f"""
---

## 🏟️ CLUB STATISTICS

### Overview
- **Total Clubs:** {clubs['total']:,}

### Top 5 Clubs by Player Count
"""
        
        for i, (club, count) in enumerate(list(clubs['by_player_count'].items())[:5], 1):
            content += f"{i}. **{club}:** {count} players (all-time)\n"
        
        content += """
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
"""
        
        return content
    
    def save_json_statistics(self):
        """Save statistics as JSON."""
        json_path = REPORTS_DIR / 'network_statistics.json'
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON saved to {json_path}")


def main():
    """Main function."""
    print("="*60)
    print("VIETNAM FOOTBALL KNOWLEDGE GRAPH")
    print("Network Statistics Generator")
    print("="*60)
    
    analyzer = NetworkStatistics()
    
    try:
        # Collect statistics
        analyzer.collect_all_statistics()
        
        # Generate visualizations
        analyzer.create_all_charts()
        
        # Generate reports
        analyzer.generate_markdown_report()
        analyzer.save_json_statistics()
        
        print("\n" + "="*60)
        print("✅ ALL DONE!")
        print("="*60)
        print(f"\nCheck results in:")
        print(f"  - Charts: {CHARTS_DIR}/")
        print(f"  - Report: {REPORTS_DIR}/network_statistics.md")
        print(f"  - JSON: {REPORTS_DIR}/network_statistics.json")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        analyzer.close()


if __name__ == '__main__':
    main()
