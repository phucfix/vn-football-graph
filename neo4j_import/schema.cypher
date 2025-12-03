// ============================================================================
// Neo4j Schema for Vietnam Football Knowledge Graph
// ============================================================================
// This file contains constraints and indexes for the knowledge graph.
// Run this BEFORE loading data.
//
// For Neo4j Aura: Use the Neo4j Browser or Cypher Shell to execute.
// ============================================================================

// ----------------------------------------------------------------------------
// DROP EXISTING DATA (for development/reset)
// WARNING: This will delete ALL data in the database!
// Uncomment and run manually if needed.
// ----------------------------------------------------------------------------

// MATCH (n) DETACH DELETE n;

// ----------------------------------------------------------------------------
// CREATE CONSTRAINTS
// Constraints ensure uniqueness and create implicit indexes.
// ----------------------------------------------------------------------------

// Player constraint - wiki_id must be unique
CREATE CONSTRAINT player_wiki_id_unique IF NOT EXISTS
FOR (p:Player) REQUIRE p.wiki_id IS UNIQUE;

// Coach constraint
CREATE CONSTRAINT coach_wiki_id_unique IF NOT EXISTS
FOR (c:Coach) REQUIRE c.wiki_id IS UNIQUE;

// Club constraint
CREATE CONSTRAINT club_wiki_id_unique IF NOT EXISTS
FOR (cl:Club) REQUIRE cl.wiki_id IS UNIQUE;

// National Team constraint
CREATE CONSTRAINT national_team_wiki_id_unique IF NOT EXISTS
FOR (nt:NationalTeam) REQUIRE nt.wiki_id IS UNIQUE;

// Position constraint
CREATE CONSTRAINT position_id_unique IF NOT EXISTS
FOR (pos:Position) REQUIRE pos.position_id IS UNIQUE;

// Nationality constraint
CREATE CONSTRAINT nationality_id_unique IF NOT EXISTS
FOR (nat:Nationality) REQUIRE nat.nationality_id IS UNIQUE;

// ----------------------------------------------------------------------------
// CREATE INDEXES
// Additional indexes for common query patterns.
// ----------------------------------------------------------------------------

// Player indexes
CREATE INDEX player_name_index IF NOT EXISTS
FOR (p:Player) ON (p.name);

CREATE INDEX player_canonical_name_index IF NOT EXISTS
FOR (p:Player) ON (p.canonical_name);

CREATE INDEX player_nationality_index IF NOT EXISTS
FOR (p:Player) ON (p.nationality);

CREATE INDEX player_position_index IF NOT EXISTS
FOR (p:Player) ON (p.position);

// Coach indexes
CREATE INDEX coach_name_index IF NOT EXISTS
FOR (c:Coach) ON (c.name);

CREATE INDEX coach_canonical_name_index IF NOT EXISTS
FOR (c:Coach) ON (c.canonical_name);

// Club indexes
CREATE INDEX club_name_index IF NOT EXISTS
FOR (cl:Club) ON (cl.name);

CREATE INDEX club_canonical_name_index IF NOT EXISTS
FOR (cl:Club) ON (cl.canonical_name);

// National Team indexes
CREATE INDEX national_team_name_index IF NOT EXISTS
FOR (nt:NationalTeam) ON (nt.name);

CREATE INDEX national_team_level_index IF NOT EXISTS
FOR (nt:NationalTeam) ON (nt.level);

// Position index
CREATE INDEX position_code_index IF NOT EXISTS
FOR (pos:Position) ON (pos.position_code);

// Nationality index
CREATE INDEX nationality_name_index IF NOT EXISTS
FOR (nat:Nationality) ON (nat.nationality_name);

// ----------------------------------------------------------------------------
// FULL-TEXT INDEXES (optional, for advanced search)
// ----------------------------------------------------------------------------

// Full-text search on player names
// CREATE FULLTEXT INDEX player_fulltext IF NOT EXISTS
// FOR (p:Player) ON EACH [p.name, p.full_name, p.canonical_name];

// Full-text search on club names
// CREATE FULLTEXT INDEX club_fulltext IF NOT EXISTS
// FOR (cl:Club) ON EACH [cl.name, cl.full_name, cl.canonical_name];
