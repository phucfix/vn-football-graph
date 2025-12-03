// ============================================================================
// Neo4j Data Loading for Vietnam Football Knowledge Graph
// ============================================================================
// This file contains LOAD CSV commands to import data into Neo4j.
//
// IMPORTANT for Neo4j Aura:
// - You cannot use file:/// URLs directly with Aura
// - Options:
//   1. Use the Python script (import_to_neo4j.py) which uploads data directly
//   2. Upload CSVs to a public URL (GitHub, S3, etc.) and modify URLs below
//   3. Use Neo4j Desktop with local files
//
// For local Neo4j: Place CSV files in the Neo4j import directory.
// ============================================================================

// ----------------------------------------------------------------------------
// LOAD REFERENCE DATA (Positions, Nationalities)
// ----------------------------------------------------------------------------

// Load Positions
LOAD CSV WITH HEADERS FROM 'file:///positions_reference.csv' AS row
MERGE (pos:Position {position_id: row.position_id})
SET pos.position_code = row.position_code,
    pos.position_name = row.position_name;

// Load Nationalities
LOAD CSV WITH HEADERS FROM 'file:///nationalities_reference.csv' AS row
MERGE (nat:Nationality {nationality_id: toInteger(row.nationality_id)})
SET nat.nationality_name = row.nationality_name,
    nat.country_code = row.country_code;

// ----------------------------------------------------------------------------
// LOAD ENTITY NODES (Players, Coaches, Clubs, National Teams)
// ----------------------------------------------------------------------------

// Load Players
LOAD CSV WITH HEADERS FROM 'file:///players_clean.csv' AS row
MERGE (p:Player {wiki_id: toInteger(row.wiki_id)})
SET p.name = row.name,
    p.canonical_name = row.canonical_name,
    p.full_name = row.full_name,
    p.date_of_birth = row.date_of_birth,
    p.place_of_birth = row.place_of_birth,
    p.nationality = row.nationality_normalized,
    p.position = row.position_normalized,
    p.height = row.height,
    p.current_club = row.current_club,
    p.wiki_url = row.wiki_url;

// Load Coaches
LOAD CSV WITH HEADERS FROM 'file:///coaches_clean.csv' AS row
MERGE (c:Coach {wiki_id: toInteger(row.wiki_id)})
SET c.name = row.name,
    c.canonical_name = row.canonical_name,
    c.full_name = row.full_name,
    c.date_of_birth = row.date_of_birth,
    c.nationality = row.nationality_normalized,
    c.wiki_url = row.wiki_url;

// Load Clubs
LOAD CSV WITH HEADERS FROM 'file:///clubs_clean.csv' AS row
MERGE (cl:Club {wiki_id: toInteger(row.wiki_id)})
SET cl.name = row.name,
    cl.canonical_name = row.canonical_name,
    cl.full_name = row.full_name,
    cl.founded = toInteger(row.founded),
    cl.ground = row.ground,
    cl.capacity = row.capacity,
    cl.chairman = row.chairman,
    cl.manager = row.manager,
    cl.league = row.league,
    cl.country = row.country,
    cl.wiki_url = row.wiki_url;

// Load National Teams
LOAD CSV WITH HEADERS FROM 'file:///national_teams_clean.csv' AS row
MERGE (nt:NationalTeam {wiki_id: toInteger(row.wiki_id)})
SET nt.name = row.name,
    nt.canonical_name = row.canonical_name,
    nt.country_code = row.country_code,
    nt.level = row.level,
    nt.manager = row.manager,
    nt.confederation = row.confederation,
    nt.wiki_url = row.wiki_url;

// ----------------------------------------------------------------------------
// LOAD LAYER 1 RELATIONSHIPS (Direct from infobox)
// ----------------------------------------------------------------------------

// PLAYED_FOR (Player -> Club)
LOAD CSV WITH HEADERS FROM 'file:///played_for.csv' AS row
MATCH (p:Player {wiki_id: toInteger(row.from_player_id)})
MATCH (cl:Club {wiki_id: toInteger(row.to_club_id)})
MERGE (p)-[r:PLAYED_FOR {
    from_year: toInteger(row.from_year),
    to_year: toInteger(row.to_year)
}]->(cl)
SET r.appearances = toInteger(row.appearances),
    r.goals = toInteger(row.goals);

// PLAYED_FOR_NATIONAL (Player -> NationalTeam)
LOAD CSV WITH HEADERS FROM 'file:///played_for_national.csv' AS row
MATCH (p:Player {wiki_id: toInteger(row.from_player_id)})
MATCH (nt:NationalTeam {wiki_id: toInteger(row.to_team_id)})
MERGE (p)-[r:PLAYED_FOR_NATIONAL {
    from_year: toInteger(row.from_year),
    to_year: toInteger(row.to_year)
}]->(nt)
SET r.appearances = toInteger(row.appearances),
    r.goals = toInteger(row.goals);

// COACHED (Coach -> Club)
LOAD CSV WITH HEADERS FROM 'file:///coached.csv' AS row
MATCH (c:Coach {wiki_id: toInteger(row.from_coach_id)})
MATCH (cl:Club {wiki_id: toInteger(row.to_club_id)})
MERGE (c)-[r:COACHED {
    from_year: toInteger(row.from_year),
    to_year: toInteger(row.to_year)
}]->(cl)
SET r.role = row.role;

// COACHED_NATIONAL (Coach -> NationalTeam)
LOAD CSV WITH HEADERS FROM 'file:///coached_national.csv' AS row
MATCH (c:Coach {wiki_id: toInteger(row.from_coach_id)})
MATCH (nt:NationalTeam {wiki_id: toInteger(row.to_team_id)})
MERGE (c)-[r:COACHED_NATIONAL {
    from_year: toInteger(row.from_year),
    to_year: toInteger(row.to_year)
}]->(nt)
SET r.role = row.role;

// ----------------------------------------------------------------------------
// LOAD LAYER 2 RELATIONSHIPS (Derived)
// ----------------------------------------------------------------------------

// TEAMMATE (Player <-> Player at same club)
LOAD CSV WITH HEADERS FROM 'file:///teammate.csv' AS row
MATCH (p1:Player {wiki_id: toInteger(row.player1_id)})
MATCH (p2:Player {wiki_id: toInteger(row.player2_id)})
MERGE (p1)-[r:TEAMMATE {
    club_name: row.club_name,
    from_year: toInteger(row.from_year),
    to_year: toInteger(row.to_year)
}]-(p2);

// NATIONAL_TEAMMATE (Player <-> Player at same national team)
LOAD CSV WITH HEADERS FROM 'file:///national_teammate.csv' AS row
MATCH (p1:Player {wiki_id: toInteger(row.player1_id)})
MATCH (p2:Player {wiki_id: toInteger(row.player2_id)})
MERGE (p1)-[r:NATIONAL_TEAMMATE {
    team_name: row.team_name,
    from_year: toInteger(row.from_year),
    to_year: toInteger(row.to_year)
}]-(p2);

// UNDER_COACH (Player was coached by Coach at club)
LOAD CSV WITH HEADERS FROM 'file:///under_coach.csv' AS row
MATCH (p:Player {wiki_id: toInteger(row.player_id)})
MATCH (c:Coach {wiki_id: toInteger(row.coach_id)})
MERGE (p)-[r:UNDER_COACH {
    club_name: row.club_name,
    from_year: toInteger(row.from_year),
    to_year: toInteger(row.to_year)
}]->(c);

// ----------------------------------------------------------------------------
// LOAD LAYER 3 RELATIONSHIPS (Semantic)
// ----------------------------------------------------------------------------

// HAS_POSITION (Player -> Position)
LOAD CSV WITH HEADERS FROM 'file:///has_position.csv' AS row
MATCH (p:Player {wiki_id: toInteger(row.player_id)})
MATCH (pos:Position {position_id: row.position_id})
MERGE (p)-[:HAS_POSITION]->(pos);

// HAS_NATIONALITY (Player/Coach -> Nationality)
// For Players
LOAD CSV WITH HEADERS FROM 'file:///has_nationality.csv' AS row
WITH row WHERE row.entity_type = 'player'
MATCH (p:Player {wiki_id: toInteger(row.entity_id)})
MATCH (nat:Nationality {nationality_name: row.nationality_name})
MERGE (p)-[:HAS_NATIONALITY]->(nat);

// For Coaches
LOAD CSV WITH HEADERS FROM 'file:///has_nationality.csv' AS row
WITH row WHERE row.entity_type = 'coach'
MATCH (c:Coach {wiki_id: toInteger(row.entity_id)})
MATCH (nat:Nationality {nationality_name: row.nationality_name})
MERGE (c)-[:HAS_NATIONALITY]->(nat);
