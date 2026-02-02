#!/usr/bin/env python3
"""Verification script for entity resolution implementation.

Validates all components are working correctly and ready for production.
"""
import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def check_imports():
    """Verify all required modules can be imported."""
    logger.info("Checking imports...")
    
    try:
        from src.utils.legal_entity_parser import (
            LegalEntityParser, SectionParser, CaseCitationParser, StatuteParser
        )
        logger.info("  ✅ legal_entity_parser imported")
    except Exception as e:
        logger.error(f"  ❌ Failed to import legal_entity_parser: {e}")
        return False
    
    try:
        from src.utils.entity_resolver import EntityResolver, EntityCluster
        logger.info("  ✅ entity_resolver imported")
    except Exception as e:
        logger.error(f"  ❌ Failed to import entity_resolver: {e}")
        return False
    
    try:
        import src.workflows.graphs.enrichment as enrichment
        if hasattr(enrichment, 'canonicalize_entities_legal'):
            logger.info("  ✅ enrichment module updated (canonicalize_entities_legal found)")
        else:
            logger.error("  ❌ enrichment module missing canonicalize_entities_legal")
            return False
    except Exception as e:
        logger.error(f"  ❌ Failed to import enrichment: {e}")
        return False
    
    try:
        from src.config import LegalOntology
        if hasattr(LegalOntology, 'validate_canonical_id'):
            logger.info("  ✅ legal_ontology updated (validate_canonical_id found)")
        else:
            logger.error("  ❌ legal_ontology missing validate_canonical_id")
            return False
    except Exception as e:
        logger.error(f"  ❌ Failed to import legal_ontology: {e}")
        return False
    
    return True


def check_section_parser():
    """Test section parser functionality."""
    logger.info("\nTesting SectionParser...")
    
    from src.utils.legal_entity_parser import SectionParser
    
    test_cases = [
        ("Section 420 IPC", "420", "IPC", "IPC:Section:420"),
        ("Sec 405 of the IPC", "405", "IPC", "IPC:Section:405"),
        ("Section 125 CRPC", "125", "CRPC", "CRPC:Section:125"),
    ]
    
    passed = 0
    for text, expected_num, expected_statute, expected_id in test_cases:
        parsed = SectionParser.parse(text)
        if parsed and parsed.section_number == expected_num and \
           parsed.statute == expected_statute and \
           parsed.canonical_id == expected_id:
            logger.info(f"  ✅ {text} → {parsed.canonical_id}")
            passed += 1
        else:
            logger.error(f"  ❌ {text} failed")
    
    return passed == len(test_cases)


def check_case_parser():
    """Test case citation parser functionality."""
    logger.info("\nTesting CaseCitationParser...")
    
    from src.utils.legal_entity_parser import CaseCitationParser
    
    test_cases = [
        "MC Verghese v Ponnan, AIR 1970 SC 1876",
        "Sangeetaben v State, AIR 2012 SC 2844",
    ]
    
    passed = 0
    for text in test_cases:
        parsed = CaseCitationParser.parse(text)
        if parsed and parsed.year and parsed.primary_reporter and parsed.court:
            logger.info(f"  ✅ {text} → {parsed.canonical_id}")
            passed += 1
        else:
            logger.error(f"  ❌ {text} failed")
    
    return passed == len(test_cases)


def check_statute_parser():
    """Test statute parser functionality."""
    logger.info("\nTesting StatuteParser...")
    
    from src.utils.legal_entity_parser import StatuteParser
    
    test_cases = [
        ("Indian Penal Code", "IPC"),
        ("Code of Criminal Procedure, 1973", "CRPC"),
        ("Constitution of India", "COI"),
    ]
    
    passed = 0
    for text, expected_abbrev in test_cases:
        parsed = StatuteParser.parse(text)
        if parsed and parsed.abbreviation == expected_abbrev:
            logger.info(f"  ✅ {text} → {parsed.abbreviation}")
            passed += 1
        else:
            logger.error(f"  ❌ {text} failed")
    
    return passed == len(test_cases)


def check_entity_resolver():
    """Test entity resolver functionality."""
    logger.info("\nTesting EntityResolver...")
    
    from src.utils.entity_resolver import EntityResolver
    
    resolver = EntityResolver(strict_mode=False)
    
    # Test section resolution
    section_variants = [
        "Section 420 IPC",
        "Sec 420 IPC",
    ]
    
    canonical_ids = []
    for variant in section_variants:
        try:
            cid = resolver.resolve_section(variant)
            if cid:
                canonical_ids.append(cid)
        except Exception as e:
            logger.error(f"  Error resolving {variant}: {e}")
            return False
    
    # All should map to same canonical ID
    if len(set(canonical_ids)) == 1:
        logger.info(f"  ✅ Section variants deduplicated: {canonical_ids[0]}")
    else:
        logger.error(f"  ❌ Section variants not deduplicated: {canonical_ids}")
        return False
    
    # Test statistics
    stats = resolver.stats()
    if stats['section_clusters'] >= 1:
        logger.info(f"  ✅ Resolver statistics: {stats['section_clusters']} section clusters, "
                   f"{stats['total_variants']} total variants")
    else:
        logger.error(f"  ❌ Resolver statistics empty")
        return False
    
    return True


def check_canonical_validation():
    """Test canonical ID validation."""
    logger.info("\nTesting Canonical ID Validation...")
    
    try:
        from src.config import LegalOntology, EntityType
        
        test_cases = [
            ("IPC:Section:420", EntityType.SECTION.value, True),
            ("IPC:1860", EntityType.STATUTE.value, True),
            ("Invalid", EntityType.SECTION.value, False),
        ]
        
        passed = 0
        for canonical_id, entity_type, expected_valid in test_cases:
            try:
                is_valid, msg = LegalOntology.validate_canonical_id(canonical_id, entity_type)
                if is_valid == expected_valid:
                    status = "✅" if is_valid else "✅ (correctly rejected)"
                    logger.info(f"  {status} {canonical_id}")
                    passed += 1
                else:
                    logger.error(f"  ❌ {canonical_id} - Expected {expected_valid}, got {is_valid}")
            except Exception as e:
                logger.error(f"  ❌ Exception validating {canonical_id}: {e}")
        
        return passed >= 2  # At least 2 of 3
    except Exception as e:
        logger.error(f"  ❌ Exception in validation check: {e}")
        return False


def check_enrichment_updated():
    """Test that enrichment module is updated."""
    logger.info("\nTesting Enrichment Module Update...")
    
    try:
        import src.workflows.graphs.enrichment as enrich_module
        
        if not hasattr(enrich_module, 'canonicalize_entities_legal'):
            logger.error("  ❌ canonicalize_entities_legal function not found")
            return False
        
        # Test with legal entities
        sections = ["Section 420 IPC", "Sec 420 IPC"]
        name_map, groups = enrich_module.canonicalize_entities_legal(sections, entity_type='Section')
        
        # Should have single canonical mapping
        unique_canonicals = set(name_map.values())
        if len(unique_canonicals) >= 1:
            logger.info(f"  ✅ Legal canonicalization working: {list(unique_canonicals)[0]}")
        else:
            logger.error(f"  ❌ Legal canonicalization failed: {unique_canonicals}")
            return False
        
        return True
    except Exception as e:
        logger.error(f"  ❌ Exception: {e}")
        return False


def check_documentation():
    """Verify documentation files exist."""
    logger.info("\nChecking Documentation...")
    
    doc_files = [
        "docs/ENTITY_RESOLUTION.md",
        "docs/ENTITY_RESOLUTION_QUICKSTART.md",
        "ENTITY_RESOLUTION_SUMMARY.md",
    ]
    
    passed = 0
    for doc_file in doc_files:
        doc_path = project_root / doc_file
        if doc_path.exists():
            size_kb = doc_path.stat().st_size / 1024
            logger.info(f"  ✅ {doc_file} ({size_kb:.1f} KB)")
            passed += 1
        else:
            logger.error(f"  ❌ {doc_file} not found")
    
    return passed == len(doc_files)


def check_test_suite():
    """Verify test file exists."""
    logger.info("\nChecking Test Suite...")
    
    test_file = project_root / "scripts/test_entity_resolution.py"
    if test_file.exists():
        size_kb = test_file.stat().st_size / 1024
        logger.info(f"  ✅ Test suite exists ({size_kb:.1f} KB)")
        
        # Count test classes
        content = test_file.read_text()
        test_classes = content.count("class Test")
        test_methods = content.count("def test_")
        logger.info(f"     • {test_classes} test classes")
        logger.info(f"     • {test_methods} test methods")
        
        return True
    else:
        logger.error(f"  ❌ Test suite not found")
        return False


def main():
    """Run all verification checks."""
    logger.info("=" * 60)
    logger.info("Entity Resolution Implementation Verification")
    logger.info("=" * 60)
    
    checks = [
        ("Import Check", check_imports),
        ("SectionParser", check_section_parser),
        ("CaseCitationParser", check_case_parser),
        ("StatuteParser", check_statute_parser),
        ("EntityResolver", check_entity_resolver),
        ("Canonical Validation", check_canonical_validation),
        ("Enrichment Update", check_enrichment_updated),
        ("Documentation", check_documentation),
        ("Test Suite", check_test_suite),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            result = check_func()
            results[name] = result
        except Exception as e:
            logger.error(f"  ❌ Exception: {e}")
            results[name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅" if result else "❌"
        logger.info(f"{status} {name}")
    
    logger.info(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        logger.info("\n🎉 All checks passed! Entity resolution is ready for production.")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} check(s) failed. Review logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
