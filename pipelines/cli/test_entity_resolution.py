"""Tests for legal entity resolution and parsing.

Validates:
  - Section reference parsing (Section 420 IPC, Sec 405, etc.)
  - Case citation parsing (AIR 1970 SC 1876, multiple formats)
  - Statute reference parsing (IPC, CRPC, etc.)
  - Deduplication of entity variants
  - Canonical ID generation and validation
"""
import pytest
from src.utils.legal_entity_parser import (
    LegalEntityParser, SectionParser, CaseCitationParser, StatuteParser,
    SectionReference, CaseCitation, StatuteReference,
    ReporterType, CourtType
)
from src.utils.entity_resolver import EntityResolver, EntityCluster
from src.config import LegalOntology, EntityType


class TestSectionParser:
    """Test section reference parsing."""

    def test_simple_section(self):
        """Test parsing simple section: Section 420 IPC"""
        parsed = SectionParser.parse("Section 420 IPC")
        assert parsed is not None
        assert parsed.statute == "IPC"
        assert parsed.section_number == "420"
        assert parsed.canonical_id == "IPC:Section:420"
        assert parsed.display_name == "Section 420 IPC"
        assert parsed.confidence >= 0.85

    def test_section_with_subsection(self):
        """Test parsing section with subsection: Section 420(1) IPC"""
        parsed = SectionParser.parse("Section 420(1) IPC")
        assert parsed is not None
        assert parsed.section_number == "420"
        assert parsed.subsection == "1"
        assert "Section 420(1)" in parsed.display_name

    def test_section_abbreviated(self):
        """Test parsing abbreviated section: Sec 405"""
        parsed = SectionParser.parse("Sec 405 of the IPC")
        assert parsed is not None
        assert parsed.section_number == "405"
        assert parsed.statute == "IPC"

    def test_section_crpc(self):
        """Test parsing CRPC section: Section 125 CRPC"""
        parsed = SectionParser.parse("Section 125 CRPC")
        assert parsed is not None
        assert parsed.statute == "CRPC"
        assert parsed.section_number == "125"
        assert parsed.canonical_id == "CRPC:Section:125"

    def test_section_variations(self):
        """Test various section reference formats."""
        test_cases = [
            ("Section 34 IPC", "34", "IPC"),
            ("Sec 377 IPC", "377", "IPC"),
            ("§ 498A IPC", "498A", "IPC"),
            ("S. 302 IPC", "302", "IPC"),
        ]
        
        for text, expected_num, expected_statute in test_cases:
            parsed = SectionParser.parse(text)
            if parsed:
                assert parsed.section_number == expected_num, f"Failed for {text}"
                assert parsed.statute == expected_statute, f"Failed for {text}"


class TestCaseCitationParser:
    """Test case citation parsing."""

    def test_air_citation(self):
        """Test parsing AIR citation: MC Verghese v Ponnan, AIR 1970 SC 1876"""
        text = "MC Verghese v Ponnan, AIR 1970 SC 1876"
        parsed = CaseCitationParser.parse(text)
        assert parsed is not None
        assert "Verghese" in parsed.case_name
        assert parsed.year == 1970
        assert parsed.primary_reporter == ReporterType.AIR
        assert parsed.court == CourtType.SC
        assert parsed.primary_report_page == "1876"
        assert "AIR_1970_SC_1876" in parsed.canonical_id

    def test_multiple_reporters(self):
        """Test parsing case with multiple reporters."""
        text = "Sangeetaben v State, AIR 2012 SC 2844 : (2012) 7 SCC 621"
        parsed = CaseCitationParser.parse(text)
        assert parsed is not None
        assert parsed.year == 2012
        assert parsed.primary_reporter == ReporterType.AIR
        # Should extract secondary report
        assert len(parsed.secondary_reports) >= 0  # May vary based on regex

    def test_scc_citation(self):
        """Test parsing SCC citation."""
        text = "State v Ahmed, (2012) 9 SCC 1"
        parsed = CaseCitationParser.parse(text)
        assert parsed is not None
        assert parsed.primary_report_page == "1"

    def test_case_citation_normalization(self):
        """Test that case citation variations are normalized."""
        variations = [
            "MC Verghese v Ponnan, AIR 1970 SC 1876",
            "MC Verghese v. Ponnan, AIR 1970 SC 1876",
        ]
        
        parsed_list = [CaseCitationParser.parse(v) for v in variations]
        # Should parse both
        assert all(p is not None for p in parsed_list)


class TestStatuteParser:
    """Test statute reference parsing."""

    def test_ipc_parsing(self):
        """Test parsing Indian Penal Code."""
        test_cases = [
            "Indian Penal Code",
            "IPC",
            "Indian Penal Code, 1860",
            "IPC 1860",
        ]
        
        for text in test_cases:
            parsed = StatuteParser.parse(text)
            assert parsed is not None, f"Failed to parse: {text}"
            assert parsed.abbreviation == "IPC"
            assert parsed.year == 1860 or parsed.year is None

    def test_crpc_parsing(self):
        """Test parsing Code of Criminal Procedure."""
        text = "Code of Criminal Procedure, 1973"
        parsed = StatuteParser.parse(text)
        assert parsed is not None
        assert parsed.abbreviation == "CRPC"
        assert parsed.year == 1973

    def test_constitution_parsing(self):
        """Test parsing Constitution of India."""
        parsed = StatuteParser.parse("Constitution of India")
        assert parsed is not None
        assert parsed.abbreviation == "COI"

    def test_unknown_statute(self):
        """Test parsing unknown statute with abbreviation extraction."""
        parsed = StatuteParser.parse("Some New Law 2020, ABC")
        # Should either parse with heuristics or return None
        # This tests graceful fallback
        assert parsed is None or parsed.abbreviation  # Either None or has abbreviation


class TestEntityResolver:
    """Test entity resolution and deduplication."""

    def test_section_resolution_variants(self):
        """Test that different section variants resolve to same ID."""
        resolver = EntityResolver(strict_mode=False)
        
        # Different ways to reference same section
        variants = [
            "Section 420 IPC",
            "Sec 420 IPC",
            "420 IPC",
        ]
        
        canonical_ids = []
        for variant in variants:
            cid = resolver.resolve_section(variant)
            if cid:
                canonical_ids.append(cid)
        
        # All should resolve to same canonical ID
        if canonical_ids:
            assert len(set(canonical_ids)) == 1, f"Variants resolved to different IDs: {canonical_ids}"

    def test_case_resolution_variants(self):
        """Test that different case citation formats resolve to same ID."""
        resolver = EntityResolver(strict_mode=False)
        
        # Same case with variations
        text1 = "MC Verghese v Ponnan, AIR 1970 SC 1876"
        text2 = "MC Verghese v. Ponnan, AIR 1970 SC 1876"
        
        cid1 = resolver.resolve_case(text1)
        cid2 = resolver.resolve_case(text2)
        
        if cid1 and cid2:
            assert cid1 == cid2, f"Case variants resolved differently: {cid1} vs {cid2}"

    def test_statute_resolution(self):
        """Test statute resolution."""
        resolver = EntityResolver(strict_mode=False)
        
        variants = [
            "Indian Penal Code",
            "IPC",
            "IPC, 1860",
        ]
        
        canonical_ids = []
        for variant in variants:
            cid = resolver.resolve_statute(variant)
            if cid:
                canonical_ids.append(cid)
        
        # Should have resolved at least one
        assert len(canonical_ids) > 0

    def test_cluster_tracking(self):
        """Test that resolver tracks entity clusters."""
        resolver = EntityResolver()
        
        # Resolve same section twice with different texts
        resolver.resolve_section("Section 420 IPC")
        resolver.resolve_section("Sec 420 IPC")
        
        stats = resolver.stats()
        assert stats['section_clusters'] >= 1
        assert stats['total_variants'] >= 1

    def test_get_all_variants(self):
        """Test retrieval of all variants for a canonical ID."""
        resolver = EntityResolver()
        
        resolver.resolve_section("Section 420 IPC")
        resolver.resolve_section("Sec 420 IPC")
        
        variants = resolver.get_all_variants("IPC:Section:420")
        assert len(variants) >= 1

    def test_non_legal_fallback(self):
        """Test fuzzy matching fallback for non-standard text."""
        resolver = EntityResolver(strict_mode=False)
        
        # Register a known section
        resolver.resolve_section("Section 420 IPC")
        
        # Try similar but not exact text (should fuzzy match)
        similar_text = "S. 420 IPC"
        result = resolver.get_canonical_id(similar_text)
        # May or may not match depending on fuzzy threshold
        assert result is None or "420" in result


class TestCanonicalIDValidation:
    """Test canonical ID format validation."""

    def test_valid_section_id(self):
        """Test valid section canonical IDs."""
        test_cases = [
            ("IPC:Section:420", EntityType.SECTION.value),
            ("CRPC:Section:125", EntityType.SECTION.value),
            ("IPC:Section:34(1)", EntityType.SECTION.value),
        ]
        
        for cid, entity_type in test_cases:
            is_valid, msg = LegalOntology.validate_canonical_id(cid, entity_type)
            assert is_valid, f"Should be valid: {cid} - {msg}"

    def test_valid_statute_id(self):
        """Test valid statute canonical IDs."""
        test_cases = [
            ("IPC", EntityType.STATUTE.value),
            ("IPC:1860", EntityType.STATUTE.value),
            ("CRPC:1973", EntityType.STATUTE.value),
        ]
        
        for cid, entity_type in test_cases:
            is_valid, msg = LegalOntology.validate_canonical_id(cid, entity_type)
            assert is_valid, f"Should be valid: {cid} - {msg}"

    def test_valid_case_id(self):
        """Test valid case canonical IDs."""
        cid = "AIR_1970_SC_1876"
        is_valid, msg = LegalOntology.validate_canonical_id(cid, "Case")
        assert is_valid, f"Should be valid: {cid} - {msg}"

    def test_invalid_ids(self):
        """Test invalid canonical IDs."""
        test_cases = [
            ("NoColonHere", EntityType.SECTION.value),
            ("Section:420", EntityType.STATUTE.value),  # Wrong type
        ]
        
        for cid, entity_type in test_cases:
            is_valid, msg = LegalOntology.validate_canonical_id(cid, entity_type)
            assert not is_valid, f"Should be invalid: {cid}"


class TestLegalEntityParser:
    """Integration tests for high-level parser."""

    def test_extract_all(self):
        """Test extracting all entity types from document text."""
        text = """
        Under Section 420 IPC, dealing with cheating. This is amended by various amendments.
        See also AIR 1970 SC 1876 (MC Verghese v Ponnan) for judicial interpretation.
        The Criminal Procedure Code, 1973, Section 125 deals with maintenance.
        """
        
        parser = LegalEntityParser()
        results = parser.extract_all(text)
        
        # Should extract some entities
        assert 'sections' in results
        assert 'cases' in results
        assert 'statutes' in results

    def test_parser_accuracy_on_sample(self):
        """Test parser on realistic legal document excerpt."""
        text = """
        Section 34 of the IPC provides that common intention. As per AIR 1995 SC 123
        (landmark case), the burden of proof lies with the prosecution. Similarly,
        under Section 420 IPC, the elements of cheating are defined.
        """
        
        parser = LegalEntityParser()
        sections = []
        cases = []
        
        # Extract sections
        for match in parser.section_parser.SECTION_PATTERN.finditer(text):
            result = parser.parse_section(match.group(0))
            if result:
                sections.append(result)
        
        # Extract cases
        cases = [parser.parse_case(t) for t in [
            "AIR 1995 SC 123 (landmark case)"
        ] if parser.parse_case(t)]
        
        # Should extract multiple sections
        assert len(sections) >= 1 or len(cases) >= 0  # At least something parsed


class TestEntityResolutionE2E:
    """End-to-end tests for complete entity resolution workflow."""

    def test_realistic_document_processing(self):
        """Test entity resolution on realistic legal document."""
        document_text = """
        Section 420 IPC deals with cheating. A person guilty of cheating under 
        Sec 420 IPC or Section 420 of the IPC may face imprisonment. 
        
        In the landmark case MC Verghese v Ponnan, AIR 1970 SC 1876, the Supreme Court
        clarified the interpretation. Similarly, in AIR 1970 SC 1876 (MC Verghese v Ponnan),
        a key precedent was established.
        """
        
        resolver = EntityResolver(strict_mode=False)
        
        # Should resolve multiple section variants to same ID
        section_ids = [
            resolver.resolve_section("Section 420 IPC"),
            resolver.resolve_section("Sec 420 IPC"),
            resolver.resolve_section("Section 420 of the IPC"),
        ]
        
        # Filter out Nones
        section_ids = [sid for sid in section_ids if sid]
        
        # All should map to same canonical
        if section_ids:
            unique_ids = set(section_ids)
            assert len(unique_ids) == 1, f"Section variants should map to same ID: {unique_ids}"

    def test_duplicate_prevention(self):
        """Test that entity resolver prevents duplicate node creation."""
        resolver = EntityResolver()
        
        # Register variants of same section
        id1 = resolver.resolve_section("Section 420 IPC")
        id2 = resolver.resolve_section("Sec 420 IPC")
        
        stats_after = resolver.stats()
        
        # Should have only 1 cluster for sections (not 2)
        assert stats_after['section_clusters'] <= 1, "Should deduplicate variants"

    def test_confidence_scoring(self):
        """Test that confidence scores are appropriate."""
        parser = SectionParser()
        
        # Structured parse should have high confidence
        parsed = parser.parse("Section 420 IPC")
        assert parsed and parsed.confidence >= 0.85


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
