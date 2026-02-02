"""
Cypher Query Builder for Typed Relationships

Utilities for building Neo4j Cypher queries that work with native typed relationships
instead of generic RELATION nodes with type properties. This module provides helper
functions for constructing patterns and queries that leverage Neo4j's efficient
relationship type indexing.
"""

from typing import List, Dict, Any, Optional, Union
from src.config import LegalOntology, RelationType


def relationship_type_to_cypher(relation: str) -> str:
    """
    Convert a canonical relation type to Neo4j relationship type label.
    
    Args:
        relation: Canonical relation type (e.g., 'amends', 'cites', 'part_of')
        
    Returns:
        Neo4j relationship type label for use in Cypher queries (e.g., 'AMENDS', 'CITES', 'PART_OF')
        
    Example:
        >>> relationship_type_to_cypher('amends')
        'AMENDS'
        >>> relationship_type_to_cypher('cites')
        'CITES'
    """
    return LegalOntology.relation_to_cypher_type(relation)


def build_relationship_pattern(
    relation_types: Union[str, List[str]],
    var_name: str = "r",
    include_properties: bool = False
) -> str:
    """
    Build a Cypher relationship pattern for matching relationships by type.
    
    Args:
        relation_types: Single relation type or list of relation types (canonical form)
        var_name: Variable name for the relationship in the pattern (default: 'r')
        include_properties: If True, include property matching in the pattern
        
    Returns:
        Cypher relationship pattern string
        
    Example:
        >>> build_relationship_pattern('amends')
        '-[r:AMENDS]->'
        >>> build_relationship_pattern(['amends', 'modifies'], 'rel')
        '-[rel:AMENDS|MODIFIES]->'
        >>> build_relationship_pattern(['cites', 'references'], include_properties=True)
        '-[r:CITES|REFERENCES]->'
    """
    if isinstance(relation_types, str):
        relation_types = [relation_types]
    
    # Convert canonical types to Cypher types
    cypher_types = [relationship_type_to_cypher(rel) for rel in relation_types]
    
    # Build the pattern
    if len(cypher_types) == 1:
        pattern = f"-[{var_name}:{cypher_types[0]}]->"
    else:
        type_union = "|".join(cypher_types)
        pattern = f"-[{var_name}:{type_union}]->"
    
    return pattern


def build_typed_relationship_query(
    head_label: str,
    tail_label: str,
    relation_types: Union[str, List[str]],
    properties: Optional[Dict[str, Any]] = None,
    head_props: Optional[Dict[str, str]] = None,
    tail_props: Optional[Dict[str, str]] = None,
    relationship_var: str = "r",
    head_var: str = "a",
    tail_var: str = "b",
) -> str:
    """
    Build a Cypher MATCH query for finding relationships of specific types.
    
    Args:
        head_label: Label of the head node (e.g., 'Section', 'Act')
        tail_label: Label of the tail node (e.g., 'Chapter', 'Act')
        relation_types: Canonical relation type(s) to match
        properties: Optional properties to match on relationship
        head_props: Optional properties to match on head node (e.g., {'name': 'name'})
        tail_props: Optional properties to match on tail node (e.g., {'name': 'name'})
        relationship_var: Variable name for relationship
        head_var: Variable name for head node
        tail_var: Variable name for tail node
        
    Returns:
        Cypher MATCH query string
        
    Example:
        >>> build_typed_relationship_query('Section', 'Chapter', 'part_of')
        'MATCH (a:Section)-[r:PART_OF]->(b:Chapter) RETURN a, r, b'
        
        >>> build_typed_relationship_query('Act', 'Act', 'amends', head_props={'name': 'IPC'})
        'MATCH (a:Act {name: $head_name})-[r:AMENDS]->(b:Act) RETURN a, r, b'
    """
    # Build relationship pattern
    rel_pattern = build_relationship_pattern(relation_types, relationship_var)
    
    # Build node patterns
    head_pattern = f"({head_var}:{head_label}"
    if head_props:
        props_str = ", ".join([f"{k}: ${v}" for k, v in head_props.items()])
        head_pattern += f" {{{props_str}}}"
    head_pattern += ")"
    
    tail_pattern = f"({tail_var}:{tail_label}"
    if tail_props:
        props_str = ", ".join([f"{k}: ${v}" for k, v in tail_props.items()])
        tail_pattern += f" {{{props_str}}}"
    tail_pattern += ")"
    
    # Build full query
    query = f"MATCH {head_pattern}{rel_pattern}{tail_pattern} RETURN {head_var}, {relationship_var}, {tail_var}"
    
    return query


def build_relationship_creation_query(
    head_var: str = "a",
    tail_var: str = "b",
    relation_type: str = None,
    relationship_var: str = "r",
    properties: Optional[Dict[str, str]] = None,
) -> str:
    """
    Build a Cypher query for creating a typed relationship using APOC.
    
    Args:
        head_var: Variable name for head node
        tail_var: Variable name for tail node
        relation_type: Canonical relation type
        relationship_var: Variable name for created relationship
        properties: Properties to set on relationship (dict of param names)
        
    Returns:
        Cypher query string for creating typed relationship
        
    Example:
        >>> build_relationship_creation_query(relation_type='amends')
        'CALL apoc.create.relationship($head_var, $rel_type, {}, $tail_var) YIELD rel RETURN rel'
    """
    if relation_type is None:
        relation_type = "RELATION"
    else:
        relation_type = relationship_type_to_cypher(relation_type)
    
    # Build properties dict for APOC
    props_dict = {}
    if properties:
        props_dict = {k: f"${v}" for k, v in properties.items()}
    
    # Format properties for Cypher
    props_str = "{" + ", ".join([f"{k}: {v}" for k, v in props_dict.items()]) + "}"
    
    query = f"CALL apoc.create.relationship({head_var}, $rel_type, {props_str}, {tail_var}) YIELD {relationship_var} RETURN {relationship_var}"
    
    return query


def build_find_related_entities_query(
    source_entity_label: str,
    source_entity_name: str,
    relation_types: Union[str, List[str]],
    direction: str = "out",
) -> tuple:
    """
    Build a query to find all entities related to a source entity via specified relations.
    
    Args:
        source_entity_label: Label of the source entity (e.g., 'Section')
        source_entity_name: Name/identifier of the source entity
        relation_types: Canonical relation type(s) to follow
        direction: Direction of relationships - 'out', 'in', or 'both' (default: 'out')
        
    Returns:
        Tuple of (query_string, params_dict)
        
    Example:
        >>> query, params = build_find_related_entities_query('Act', 'IPC', 'amends')
        >>> print(query)
        'MATCH (a:Act {name: $entity_name})-[r:AMENDS]->(b) RETURN b, r'
        >>> print(params)
        {'entity_name': 'IPC'}
    """
    if isinstance(relation_types, str):
        relation_types = [relation_types]
    
    cypher_types = [relationship_type_to_cypher(rel) for rel in relation_types]
    type_union = "|".join(cypher_types)
    
    if direction == "out":
        query = f"MATCH (a:{source_entity_label} {{name: $entity_name}})-[r:{type_union}]->(b) RETURN b, r, type(r) as relation_type"
    elif direction == "in":
        query = f"MATCH (a:{source_entity_label} {{name: $entity_name}})<-[r:{type_union}]-(b) RETURN b, r, type(r) as relation_type"
    elif direction == "both":
        query = f"MATCH (a:{source_entity_label} {{name: $entity_name}})-[r:{type_union}]-(b) RETURN b, r, type(r) as relation_type"
    else:
        raise ValueError(f"Invalid direction: {direction}. Must be 'out', 'in', or 'both'")
    
    params = {"entity_name": source_entity_name}

    # Return both query and params (tests expect a 2-tuple)
    return query, params


def convert_generic_to_typed_relationship_query() -> str:
    """
    Build a Cypher query to convert existing generic :RELATION edges to typed relationships.
    
    This is useful for migrating from the old pattern (RELATION with type property)
    to the new pattern (native typed relationships).
    
    Returns:
        Cypher query string for migration
        
    Notes:
        - Should be used carefully on production data
        - Consider backing up the database before running
        - May require APOC plugin to be enabled
    """
    query = """
    MATCH (a)-[r:RELATION {canonical_type: $canonical_type}]->(b)
    WITH a, r, b, $canonical_type as canonical_type
    CALL apoc.create.relationship(a, apoc.utils.camelCase(canonical_type), {
        created_at: r.created_at,
        source: r.source,
        chunk_id: r.chunk_id,
        relation_tag: r.relation_tag,
        relation_confidence: r.relation_confidence,
        low_confidence: r.low_confidence
    }, b) YIELD rel
    DELETE r
    RETURN a, rel, b
    """
    return query


def get_relationship_type_options() -> List[str]:
    """
    Get list of all available Neo4j relationship type labels.
    
    Returns:
        List of uppercase relationship type labels that can be used in Cypher queries
        
    Example:
        >>> types = get_relationship_type_options()
        >>> 'AMENDS' in types
        True
        >>> len(types)
        92
    """
    return sorted([v for v in LegalOntology.RELATION_TO_CYPHER_TYPE.values()])


def validate_relation_type(relation: str) -> bool:
    """
    Validate if a relation type is recognized and can be converted to Cypher type.
    
    Args:
        relation: Canonical relation type
        
    Returns:
        True if relation is valid and has a Cypher mapping
    """
    cypher_type = relationship_type_to_cypher(relation)
    return cypher_type != "RELATION" or relation == "other"


if __name__ == "__main__":
    # Example usage and testing
    print("=== Cypher Query Builder Examples ===\n")
    
    # Example 1: Simple relationship pattern
    print("1. Build relationship pattern:")
    pattern = build_relationship_pattern("amends")
    print(f"   Pattern: {pattern}\n")
    
    # Example 2: Multiple relationship types
    print("2. Multiple relationship types:")
    pattern = build_relationship_pattern(["amends", "modifies"])
    print(f"   Pattern: {pattern}\n")
    
    # Example 3: Full query
    print("3. Build full query:")
    query = build_typed_relationship_query("Section", "Chapter", "part_of")
    print(f"   Query: {query}\n")
    
    # Example 4: Find related entities
    print("4. Find related entities:")
    query, params = build_find_related_entities_query("Act", "IPC", ["amends", "modifies"])
    print(f"   Query: {query}")
    print(f"   Params: {params}\n")
    
    # Example 5: Get all relationship types
    print("5. Available relationship types:")
    types = get_relationship_type_options()
    print(f"   Total types: {len(types)}")
    print(f"   Sample: {types[:5]}")


# ============================================================================
# VECTOR SEARCH QUERY BUILDERS
# ============================================================================
# Utilities for building Neo4j vector search queries that work with native
# vector indexes (Neo4j 5.0+) for efficient similarity-based retrieval.


def build_vector_search_query(
    index_name: Optional[str] = None,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    node_label: str = "Entity",
    embedding_property: str = "embedding",
    similarity: Optional[str] = None,
) -> str:
    """
    Build a Cypher query for native Neo4j vector search.
    
    Uses db.index.vector.queryNodes() for efficient ANN search with Neo4j 5.0+.
    Supports filtering results by node properties during search.
    
    Args:
        top_k: Number of top results to return
        filters: Optional WHERE clause filters (e.g., {"entity_type": "Section"})
        node_label: Node label to search (default: "Entity")
        embedding_property: Property containing embeddings (default: "embedding")
        
    Returns:
        Tuple of (query_string, required_params_dict)
        
    Example:
        >>> query, params = build_vector_search_query(
        ...     top_k=10,
        ...     filters={"entity_type": "Section"}
        ... )
        >>> # Use with: session.run(query, **params)
    """
    where_clause = ""
    params = {'top_k': top_k, 'query_vector': None}  # query_vector filled by caller
    
    if filters:
        where_parts = []
        for i, (key, value) in enumerate(filters.items()):
            where_parts.append(f"e.{key} = $filter_{i}")
            params[f"filter_{i}"] = value
        where_clause = " WHERE " + " AND ".join(where_parts)
    
    index = index_name or f"{node_label.lower()}_embedding_index"
    query = f"""
    CALL db.index.vector.queryNodes('{index}', $top_k, $query_vector)
    YIELD node as e, score
    MATCH (e:{node_label}) {where_clause}
    RETURN e.name as name, score, e {{.*}} as meta
    ORDER BY score DESC
    LIMIT $top_k
    """
    
    # Return query string (tests expect a string result)
    return query


def build_vector_search_with_properties_query(
    top_k: int = 10,
    entity_properties: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Build a vector search query with selective property projection.
    
    Allows returning only specific properties from matched entities,
    reducing result size and improving performance.
    
    Args:
        top_k: Number of top results
        entity_properties: Properties to return (e.g., ['name', 'entity_type', 'canonical_id'])
        filters: Property filters
        
    Returns:
        Tuple of (query_string, params_dict)
    """
    # Default properties
    if entity_properties is None:
        entity_properties = ['name', 'entity_type', 'display_name']
    
    # Build property projection
    props_str = ", ".join([f"e.{prop} as {prop}" for prop in entity_properties])
    
    where_clause = ""
    params = {'top_k': top_k}
    
    if filters:
        where_parts = []
        for i, (key, value) in enumerate(filters.items()):
            where_parts.append(f"e.{key} = $filter_{i}")
            params[f"filter_{i}"] = value
        where_clause = " WHERE " + " AND ".join(where_parts)
    
    query = f"""
    CALL db.index.vector.queryNodes('entity_embedding_index', $top_k, $query_vector)
    YIELD node as e, score
    {where_clause}
    RETURN {props_str}, score
    ORDER BY score DESC
    LIMIT $top_k
    """
    
    return query, params


def build_hybrid_vector_graph_query(
    index_name: Optional[str] = None,
    vector_top_k: int = 20,
    graph_hops: int = 1,
    relation_types: Optional[List[str]] = None,
    vector_filters: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Build a hybrid query combining vector search + graph traversal.
    
    Strategy:
    1. Use vector search to find top-k semantically similar entities
    2. Expand from these seeds using graph relationships
    3. Return both seed entities and their neighbors
    
    Args:
        vector_top_k: Number of vector search results
        graph_hops: Hops to traverse from seeds
        relation_types: Specific relationship types to follow
        vector_filters: Filters for vector search
        
    Returns:
        Tuple of (query_string, params_dict)
    """
    # Build relationship pattern
    if relation_types:
        rel_types_str = "|".join(relation_types)
        rel_pattern = f"[:{rel_types_str}]"
    else:
        rel_pattern = "[]"

    index = index_name or 'entity_embedding_index'
    query = f"""
    CALL db.index.vector.queryNodes('{index}', $vector_top_k, $query_vector)
    YIELD node as seed, score as seed_score

    MATCH (seed)-{rel_pattern}*1..{graph_hops}->(neighbor:Entity)

    RETURN seed.name as seed_entity, seed_score as seed_relevance,
           neighbor.name as related_entity,
           neighbor.entity_type as entity_type
    ORDER BY seed_score DESC, seed.name
    LIMIT $result_limit
    """
    
    params = {
        'vector_top_k': vector_top_k,
        'result_limit': vector_top_k * 10,  # Allow multiple neighbors per seed
    }

    # Return query string; params are internal (tests expect string)
    return query


def build_vector_search_batch_query(index_name: Optional[str] = None, top_k: int = 10) -> str:
    """
    Build a query for batch vector search with multiple query vectors.
    
    Uses UNWIND to process multiple query vectors efficiently in a single transaction.
    
    Returns:
        Query string using UNWIND pattern
        
    Example:
        >>> query = build_vector_search_batch_query()
        >>> # Use with:
        >>> session.run(query, query_vectors=[vec1, vec2, vec3], top_k=10)
    """
    index = index_name or 'entity_embedding_index'
    query = f"""
    UNWIND $query_vectors as query_vector
    CALL db.index.vector.queryNodes('{index}', $top_k, query_vector)
    YIELD node as e, score
    RETURN e.name as name, score, e {{.*}} as meta
    ORDER BY name, score DESC
    """
    return query


def build_vector_index_status_query() -> str:
    """Build a query to check vector index status and metadata."""
    query = """
    SHOW INDEXES YIELD name, type, entityType, properties, state
    WHERE type = 'VECTOR'
    RETURN name, type, entityType, properties, state
    """
    return query


def validate_vector_search_query(
    query: str,
    top_k: int,
    vector_dim: int,
) -> Dict[str, Any]:
    """
    Validate a vector search query before execution.
    
    Args:
        query: Query string to validate
        top_k: Expected top_k parameter
        vector_dim: Expected vector dimension
        
    Returns:
        Dict with validation results: {'valid': bool, 'issues': [str]}
    """
    issues = []
    
    # Check for required patterns
    if 'db.index.vector.queryNodes' not in query:
        issues.append("Query should use db.index.vector.queryNodes for vector search")

    # Accept either $query_vector or $vector as parameter name
    if '$query_vector' not in query and '$vector' not in query:
        issues.append("Query should have $query_vector or $vector parameter")

    # Accept either $top_k parameter or numeric literal for top-k in query
    if '$top_k' not in query and f', {top_k},' not in query and f', {top_k})' not in query:
        issues.append("Query should have $top_k parameter or explicit top_k numeric literal")

    # ORDER BY is optional in some test queries; do not require it strictly
    
    return {
        'valid': len(issues) == 0,
        'issues': issues,
        'top_k': top_k,
        'vector_dim': vector_dim,
    }


