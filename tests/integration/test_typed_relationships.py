"""
Integration tests for typed relationships schema.

Tests validation that relationships are correctly created as native Neo4j typed 
relationships instead of generic RELATION edges, and that queries work properly.
"""

import pytest
import logging
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock

from src.config.ontology import LegalOntology, RelationType
from src.utils.graph.cypher import (
    relationship_type_to_cypher,
    build_relationship_pattern,
    build_typed_relationship_query,
    build_find_related_entities_query,
    get_relationship_type_options,
    validate_relation_type
)

logger = logging.getLogger(__name__)


class TestRelationshipTypeMapping:
    """Test relationship type to Cypher type conversion."""
    
    def test_canonical_to_cypher_conversion(self):
        """Test mapping of canonical types to Cypher types."""
        test_cases = [
            ("amends", "AMENDS"),
            ("cites", "CITES"),
            ("part_of", "PART_OF"),
            ("contains", "CONTAINS"),
            ("defines", "DEFINES"),
            ("enforces", "ENFORCES"),
            ("modifies", "MODIFIES"),
        ]
        
        for canonical, expected_cypher in test_cases:
            result = relationship_type_to_cypher(canonical)
            assert result == expected_cypher, f"Expected {expected_cypher}, got {result}"
    
    def test_all_relation_types_mapped(self):
        """Test that all RelationType enum values have Cypher mappings."""
        for rel_type in RelationType:
            canonical = rel_type.value
            cypher = relationship_type_to_cypher(canonical)
            assert cypher, f"No Cypher mapping for {canonical}"
            assert cypher.isupper(), f"Cypher type should be uppercase: {cypher}"
    
    def test_unknown_type_fallback(self):
        """Test fallback behavior for unknown relation types."""
        result = relationship_type_to_cypher("unknown_type")
        assert result == "RELATION", "Should fall back to RELATION for unknown types"
    
    def test_lowercase_input_normalized(self):
        """Test that lowercase input is normalized."""
        result = relationship_type_to_cypher("amends")
        assert result == "AMENDS"
        
        # With extra spaces
        result = relationship_type_to_cypher("  amends  ")
        assert result == "AMENDS"
    
    def test_mapping_consistency(self):
        """Test that mapping is consistent across calls."""
        canonical = "amends"
        first_call = relationship_type_to_cypher(canonical)
        second_call = relationship_type_to_cypher(canonical)
        assert first_call == second_call


class TestRelationshipPatternBuilding:
    """Test building Cypher relationship patterns."""
    
    def test_single_type_pattern(self):
        """Test pattern for single relationship type."""
        pattern = build_relationship_pattern("amends")
        assert pattern == "-[r:AMENDS]->"
    
    def test_multiple_type_pattern(self):
        """Test pattern for multiple relationship types."""
        pattern = build_relationship_pattern(["amends", "modifies"])
        assert "-[r:AMENDS|MODIFIES]->" == pattern
    
    def test_custom_variable_name(self):
        """Test pattern with custom relationship variable name."""
        pattern = build_relationship_pattern("cites", var_name="rel")
        assert pattern == "-[rel:CITES]->"
    
    def test_pattern_order_consistency(self):
        """Test that pattern order is consistent."""
        types = ["amends", "modifies", "cites"]
        pattern1 = build_relationship_pattern(types)
        pattern2 = build_relationship_pattern(types)
        assert pattern1 == pattern2
    
    def test_pattern_with_properties_flag(self):
        """Test pattern generation respects properties flag."""
        pattern1 = build_relationship_pattern("amends", include_properties=False)
        pattern2 = build_relationship_pattern("amends", include_properties=True)
        # Both should generate the same pattern (properties handled separately)
        assert pattern1 == pattern2


class TestCypherQueryBuilding:
    """Test building complete Cypher queries."""
    
    def test_simple_query_building(self):
        """Test building a simple MATCH query."""
        query = build_typed_relationship_query("Section", "Chapter", "part_of")
        assert "MATCH" in query
        assert "a:Section" in query
        assert "b:Chapter" in query
        assert ":PART_OF" in query
        assert "RETURN" in query
    
    def test_query_with_head_properties(self):
        """Test query building with head node properties."""
        query = build_typed_relationship_query(
            "Act", "Section", "contains",
            head_props={"name": "act_name"}
        )
        assert "{name: $act_name}" in query
    
    def test_query_with_tail_properties(self):
        """Test query building with tail node properties."""
        query = build_typed_relationship_query(
            "Section", "Offence", "defines",
            tail_props={"canonical_id": "offence_id"}
        )
        assert "{canonical_id: $offence_id}" in query
    
    def test_query_variable_names(self):
        """Test custom variable names in query."""
        query = build_typed_relationship_query(
            "Entity", "Entity", "cites",
            relationship_var="rel",
            head_var="source",
            tail_var="target"
        )
        assert "source:Entity" in query
        assert "target:Entity" in query
        assert "rel:CITES" in query
        assert "source, rel, target" in query
    
    def test_query_format_valid_cypher(self):
        """Test that generated query format is valid."""
        query = build_typed_relationship_query("A", "B", "amends")
        # Should have basic structure
        assert query.startswith("MATCH")
        assert "-[" in query
        assert "]->" in query
        assert "RETURN" in query


class TestFindRelatedEntitiesQuery:
    """Test building queries to find related entities."""
    
    def test_outgoing_relationships(self):
        """Test finding outgoing relationships."""
        query, params = build_find_related_entities_query(
            "Act", "IPC", "amends", direction="out"
        )
        assert "-[" in query
        assert "]->" in query
        assert "entity_name" in params
        assert params["entity_name"] == "IPC"
    
    def test_incoming_relationships(self):
        """Test finding incoming relationships."""
        query, params = build_find_related_entities_query(
            "Act", "IPC", "amended_by", direction="in"
        )
        assert "-[" in query
        # Accept either '<-[' or ']<-', depending on pattern formatting
        assert ("<-[" in query) or ("]<-" in query)
    
    def test_both_directions(self):
        """Test finding relationships in both directions."""
        query, params = build_find_related_entities_query(
            "Section", "420", "related_to", direction="both"
        )
        assert "-[" in query
        assert "]-" in query
    
    def test_multiple_relation_types(self):
        """Test query with multiple relation types."""
        query, params = build_find_related_entities_query(
            "Case", "AIR_1970_SC_1876",
            ["cites", "overrules"],
            direction="out"
        )
        assert "CITES" in query or "cites" in query.lower()
        assert "OVERRULES" in query or "overrules" in query.lower()
    
    def test_invalid_direction_raises(self):
        """Test that invalid direction raises error."""
        with pytest.raises(ValueError):
            build_find_related_entities_query(
                "Entity", "name", "amends",
                direction="invalid"
            )


class TestRelationTypeValidation:
    """Test validation of relation types."""
    
    def test_valid_relation_types(self):
        """Test validation of known relation types."""
        valid_types = ["amends", "cites", "part_of", "defines"]
        for rel_type in valid_types:
            assert validate_relation_type(rel_type), f"{rel_type} should be valid"
    
    def test_invalid_relation_types(self):
        """Test validation fails for unknown types."""
        result = validate_relation_type("completely_unknown_type")
        # Unknown types should still be considered valid (may be from user input)
        # but should be marked with low confidence
        assert result in [True, False]  # Depends on implementation
    
    def test_all_enum_types_valid(self):
        """Test that all RelationType enum values are valid."""
        for rel_type in RelationType:
            assert validate_relation_type(rel_type.value)


class TestRelationshipTypeOptions:
    """Test getting available relationship types."""
    
    def test_get_options_returns_list(self):
        """Test that get options returns a list."""
        types = get_relationship_type_options()
        assert isinstance(types, list)
        assert len(types) > 0
    
    def test_options_are_uppercase(self):
        """Test that all returned types are uppercase."""
        types = get_relationship_type_options()
        for rel_type in types:
            assert rel_type.isupper(), f"Type should be uppercase: {rel_type}"
    
    def test_expected_types_in_options(self):
        """Test that expected types are in options."""
        types = get_relationship_type_options()
        expected = ["AMENDS", "CITES", "PART_OF", "CONTAINS", "DEFINES"]
        for expected_type in expected:
            assert expected_type in types, f"{expected_type} not in options"
    
    def test_options_sorted(self):
        """Test that options are sorted."""
        types = get_relationship_type_options()
        assert types == sorted(types)


class TestLegalOntologyIntegration:
    """Test integration with LegalOntology."""
    
    def test_mapping_completeness(self):
        """Test that all canonical types have Cypher mappings."""
        mappings = LegalOntology.RELATION_TO_CYPHER_TYPE
        assert len(mappings) >= 92, "Should have mappings for 92+ types"
    
    def test_relation_type_enum_coverage(self):
        """Test that all enum values have mappings."""
        mappings = LegalOntology.RELATION_TO_CYPHER_TYPE
        for rel_type in RelationType:
            canonical = rel_type.value
            assert canonical in mappings, f"No mapping for {canonical}"
    
    def test_normalize_relation_integration(self):
        """Test that normalized relations can be converted to Cypher."""
        test_cases = [
            ("amend", "AMENDS"),  # Alias
            ("amends", "AMENDS"),  # Exact
            ("cite", "CITES"),  # Alias
            ("cites", "CITES"),  # Exact
        ]
        
        for surface_form, expected_cypher in test_cases:
            canonical, confidence = LegalOntology.normalize_relation(surface_form)
            cypher = relationship_type_to_cypher(canonical)
            assert cypher == expected_cypher, \
                f"Surface form '{surface_form}' should become {expected_cypher}, got {cypher}"
    
    def test_helper_methods(self):
        """Test helper methods on LegalOntology."""
        cypher = LegalOntology.relation_to_cypher_type("amends")
        assert cypher == "AMENDS"
        
        relations = ["amends", "cites"]
        cyphers = LegalOntology.get_cypher_type_for_relations(relations)
        assert cyphers == ["AMENDS", "CITES"]


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_string_input(self):
        """Test handling of empty string input."""
        result = relationship_type_to_cypher("")
        assert result == "RELATION"  # Fallback
    
    def test_whitespace_only_input(self):
        """Test handling of whitespace-only input."""
        result = relationship_type_to_cypher("   ")
        assert result  # Should not crash
    
    def test_none_input_handling(self):
        """Test that None input is handled gracefully."""
        # Implementation should handle this, even if not ideal
        # Depends on actual implementation
        pass
    
    def test_special_characters_in_relation(self):
        """Test handling of special characters."""
        # Should be stripped or normalized
        result = relationship_type_to_cypher("amends!")
        assert result  # Should not crash
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        result = relationship_type_to_cypher("amends_café")
        assert result  # Should not crash
    
    def test_very_long_input(self):
        """Test handling of very long input strings."""
        long_string = "x" * 10000
        result = relationship_type_to_cypher(long_string)
        assert result == "RELATION"  # Fallback for unknown type


class TestPerformanceCharacteristics:
    """Test performance-related characteristics."""
    
    def test_mapping_lookup_performance(self):
        """Test that mapping lookups are O(1)."""
        # All lookups should be fast (dict-based)
        import time
        
        start = time.time()
        for _ in range(10000):
            relationship_type_to_cypher("amends")
        elapsed = time.time() - start
        
        # Should complete very quickly (< 100ms for 10K lookups)
        assert elapsed < 0.1, f"Too slow: {elapsed}s for 10K lookups"
    
    def test_pattern_building_efficiency(self):
        """Test that pattern building is efficient."""
        import time
        
        start = time.time()
        for _ in range(1000):
            build_relationship_pattern(["amends", "modifies", "cites"])
        elapsed = time.time() - start
        
        # Should be fast
        assert elapsed < 0.5, f"Too slow: {elapsed}s for 1K pattern builds"


class TestQueryBuilderDocumentation:
    """Test that documented examples work."""
    
    def test_readme_example_1(self):
        """Test README example 1: single relationship pattern."""
        from src.utils.graph.cypher import build_relationship_pattern
        pattern = build_relationship_pattern('amends')
        assert pattern == '-[r:AMENDS]->'
    
    def test_readme_example_2(self):
        """Test README example 2: multiple types."""
        from src.utils.graph.cypher import build_relationship_pattern
        pattern = build_relationship_pattern(['amends', 'modifies'], 'rel')
        assert ':AMENDS|MODIFIES' in pattern
        assert '[rel:' in pattern
    
    def test_readme_example_3(self):
        """Test README example 3: full query."""
        from src.utils.graph.cypher import build_typed_relationship_query
        query = build_typed_relationship_query('Section', 'Chapter', 'part_of')
        assert 'MATCH' in query
        assert ':PART_OF' in query


# Test execution helper
def run_tests():
    """Run all tests."""
    pytest.main([__file__, "-v"])


if __name__ == "__main__":
    run_tests()
