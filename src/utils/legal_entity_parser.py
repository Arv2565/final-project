"""Legal entity parsing utilities for statute references, case citations, and section numbers.

Provides structured extraction of legal entities from text with canonical ID generation.
Supports:
  - Section references: "Section 420 IPC" -> IPC:Section:420
  - Act references: "Code of Criminal Procedure, 1973" -> CRPC:1973
  - Case citations: "AIR 1970 SC 1876" -> AIR_1970_SC_1876
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


class ReporterType(Enum):
    """Indian legal case reporters."""
    AIR = "AIR"  # All India Reporter
    SCC = "SCC"  # Supreme Court Cases
    CR_LJ = "Cr LJ"  # Criminal Law Journal
    LNIND = "LNIND"  # Legal Navigator India
    SCALE = "Scale"  # Scale Reporter
    JMFC = "JMFC"  # Journal MFC
    SCCC = "SCCC"  # Supreme Court Criminal Cases
    OTHER = "Other"


class CourtType(Enum):
    """Indian court hierarchy."""
    SC = "SC"  # Supreme Court
    HC = "HC"  # High Court
    DIST = "District Court"
    SESSIONS = "Sessions Court"
    CRD = "Criminal District Court"
    LD = "Labour Division"
    OTHER = "Other"


@dataclass
class StatuteReference:
    """Parsed statute reference (Act/Code)."""
    name: str  # e.g., "Indian Penal Code"
    abbreviation: str  # e.g., "IPC"
    year: Optional[int]  # e.g., 1860
    canonical_id: str  # e.g., "IPC:1860"
    confidence: float  # 0.5-1.0


@dataclass
class SectionReference:
    """Parsed section reference with hierarchy."""
    statute: str  # e.g., "IPC"
    section_number: str  # e.g., "420"
    subsection: Optional[str]  # e.g., "1" from "420(1)"
    clause: Optional[str]  # e.g., "a" from "420(1)(a)"
    canonical_id: str  # e.g., "IPC:Section:420"
    display_name: str  # e.g., "Section 420 IPC"
    confidence: float  # 0.5-1.0


@dataclass
class CaseCitation:
    """Parsed case citation with multiple report formats."""
    case_name: str  # e.g., "MC Verghese v Ponnan"
    year: int  # e.g., 1970
    primary_reporter: ReporterType  # Primary reporter (AIR, SCC, etc.)
    primary_report_page: str  # e.g., "1876"
    court: CourtType  # e.g., "SC"
    secondary_reports: List[Tuple[ReporterType, int, str]]  # [(SCC, 1969, "37"), ...]
    canonical_id: str  # e.g., "AIR_1970_SC_1876"
    display_name: str  # Full citation
    confidence: float  # 0.5-1.0


class StatuteParser:
    """Parse statute references (acts, codes, rules)."""

    # Comprehensive act registry with abbreviations
    ACT_REGISTRY: Dict[str, Tuple[str, Optional[int]]] = {
        # Major statutes
        "Indian Penal Code": ("IPC", 1860),
        "IPC": ("IPC", 1860),
        "Code of Criminal Procedure": ("CRPC", 1973),
        "CrPC": ("CRPC", 1973),
        "CRPC": ("CRPC", 1973),
        "Criminal Procedure Code": ("CRPC", 1973),
        "Code of Civil Procedure": ("CPC", 1908),
        "CPC": ("CPC", 1908),
        "Indian Evidence Act": ("IEA", 1872),
        "IEA": ("IEA", 1872),
        "Constitution of India": ("COI", None),
        "Indian Contract Act": ("ICA", 1872),
        "National Investigation Agency Act": ("NIA", 2016),
        "NIA": ("NIA", 2016),
        "Prevention of Money Laundering Act": ("PMLA", 2002),
        "PMLA": ("PMLA", 2002),
        "Bharatiya Nyaya Sanhita": ("BNS", 2023),
        "BNS": ("BNS", 2023),
        "Motor Vehicles Act": ("MVA", 1988),
        "MVA": ("MVA", 1988),
    }

    @staticmethod
    def parse(text: str) -> Optional[StatuteReference]:
        """Parse statute reference from text.

        Examples:
          "Indian Penal Code, 1860" -> StatuteReference(IPC, 1860)
          "Section 405 of the IPC" -> StatuteReference(IPC, 1860)
          "under the CRPC" -> StatuteReference(CRPC, 1973)
        """
        if not text or len(text) > 200:  # Sanity check
            return None

        text_lower = text.lower()

        # Try to match against registry
        for statute_name, (abbrev, year) in StatuteParser.ACT_REGISTRY.items():
            if statute_name.lower() in text_lower:
                # Try to extract year if not in registry
                year_match = re.search(r',?\s*(\d{4})', text)
                extracted_year = int(year_match.group(1)) if year_match else year
                
                canonical_id = f"{abbrev}:{extracted_year}" if extracted_year else abbrev
                
                return StatuteReference(
                    name=statute_name,
                    abbreviation=abbrev,
                    year=extracted_year,
                    canonical_id=canonical_id,
                    confidence=0.95 if year else 0.85
                )

        # Fallback: extract abbreviation pattern (e.g., "IPC 1860", "CRPC")
        abbrev_match = re.search(r'\b([A-Z]{2,5})\b\s*(?:of\s+)?(?:the\s+)?(?:,?\s*(\d{4}))?', text)
        if abbrev_match:
            abbrev = abbrev_match.group(1)
            year_str = abbrev_match.group(2)
            year = int(year_str) if year_str else None
            canonical_id = f"{abbrev}:{year}" if year else abbrev
            
            return StatuteReference(
                name=abbrev,  # Unknown full name
                abbreviation=abbrev,
                year=year,
                canonical_id=canonical_id,
                confidence=0.70
            )

        return None


class SectionParser:
    """Parse section references with hierarchy."""

    # Pattern: "Section 420" / "Sec 420" / "§420" / "S.420" / "420" (in context)
    SECTION_PATTERN = re.compile(
        r'(?:section|sec|§|s\.)\s*(\d+)(?:\(([0-9a-z]+)\))?(?:\(([a-z])\))?',
        re.IGNORECASE
    )

    # Pattern: "Section 420 IPC" / "Section 420 of the IPC"
    SECTION_WITH_STATUTE_PATTERN = re.compile(
        r'(?:section|sec|§|s\.)\s*(\d+)(?:\(([0-9a-z]+)\))?(?:\(([a-z])\))?'
        r'(?:\s+(?:of\s+)?(?:the\s+)?)?([A-Z]{2,5})',
        re.IGNORECASE
    )

    @staticmethod
    def parse(text: str, statute: Optional[str] = None) -> Optional[SectionReference]:
        """Parse section reference from text.

        Args:
            text: Text containing section reference (e.g., "Section 420 IPC")
            statute: Optional statute abbreviation to use as fallback

        Examples:
            "Section 420 IPC" -> SectionReference(IPC, 420)
            "Sec 405 of the IPC" -> SectionReference(IPC, 405)
            "Section 34(1)(a) IPC" -> SectionReference(IPC, 34, "1", "a")
        """
        if not text or len(text) > 300:
            return None

        # Try pattern with statute in the text
        match = SectionParser.SECTION_WITH_STATUTE_PATTERN.search(text)
        if match:
            section_num = match.group(1)
            subsection = match.group(2)
            clause = match.group(3)
            statute_abbrev = match.group(4).upper()

            canonical_id = f"{statute_abbrev}:Section:{section_num}"
            display_name = f"Section {section_num}"
            if subsection:
                canonical_id += f"({subsection})"
                display_name += f"({subsection})"
            if clause:
                canonical_id += f"({clause})"
                display_name += f"({clause})"
            display_name += f" {statute_abbrev}"

            return SectionReference(
                statute=statute_abbrev,
                section_number=section_num,
                subsection=subsection,
                clause=clause,
                canonical_id=canonical_id,
                display_name=display_name,
                confidence=0.95
            )

        # Try pattern without statute (use provided statute as fallback)
        match = SectionParser.SECTION_PATTERN.search(text)
        if match and statute:
            section_num = match.group(1)
            subsection = match.group(2)
            clause = match.group(3)

            canonical_id = f"{statute}:Section:{section_num}"
            display_name = f"Section {section_num}"
            if subsection:
                canonical_id += f"({subsection})"
                display_name += f"({subsection})"
            if clause:
                canonical_id += f"({clause})"
                display_name += f"({clause})"
            display_name += f" {statute}"

            return SectionReference(
                statute=statute,
                section_number=section_num,
                subsection=subsection,
                clause=clause,
                canonical_id=canonical_id,
                display_name=display_name,
                confidence=0.85
            )

        return None


class CaseCitationParser:
    """Parse Indian case citations with multiple report formats."""

    # Pattern: "Case Name v Respondent, AIR 1970 SC 1876"
    CASE_CITATION_PATTERN = re.compile(
        r'(.*?)\s+v\.?\s+(.*?),?\s+' +  # Case name and respondent
        r'(AIR|SCC|Cr\.?\s*LJ|LNIND|Scale|JMFC|SCCC)?\s*(\d{4})?\s*' +  # Primary reporter and year
        r'(SC|HC|LD|DIST|Sessions)?\s*(\d+)?',  # Court and page
        re.IGNORECASE
    )

    # Secondary reports pattern: "(2012) 7 SCC 621"
    SECONDARY_REPORT_PATTERN = re.compile(
        r'\((\d{4})\)\s+(\d+)?\s*(SCC|Cr\.?\s*LJ|Scale|JMFC)??\s*(\d+)?',
        re.IGNORECASE
    )

    @staticmethod
    def parse(text: str) -> Optional[CaseCitation]:
        """Parse case citation from text.

        Examples:
          "MC Verghese v Ponnan, AIR 1970 SC 1876" -> CaseCitation(...)
          "Sangeetaben v State, AIR 2012 SC 2844 : (2012) 7 SCC 621" -> CaseCitation(...)
        """
        if not text or len(text) > 500:
            return None

        # Extract case name and primary citation
        match = CaseCitationParser.CASE_CITATION_PATTERN.search(text)
        if not match:
            return None

        case_name = match.group(1).strip()
        reporter_str = match.group(3)
        year_str = match.group(4)
        court_str = match.group(5)

        # If primary reporter/year not present, try to find a secondary reporter pattern
        if not reporter_str or not year_str:
            # First find a year enclosed in parentheses like '(2012)'
            sec_year_match = re.search(r'\((\d{4})\)', text)
            if sec_year_match:
                year_str = sec_year_match.group(1)
                # Look at the text after the closing parenthesis to find optional volume, reporter, and page
                after = text[sec_year_match.end():]
                after_match = re.search(r'\s*(\d+)?\s*(SCC|Cr\.?\s*LJ|Scale|JMFC)?\s*(\d+)?', after, re.IGNORECASE)
                if after_match:
                    vol = after_match.group(1)
                    rep = after_match.group(2)
                    pg = after_match.group(3)

                    reporter_str = rep or reporter_str
                    # Prefer an explicit page (pg), else use volume (vol), else default to "1"
                    page = pg or vol or "1"
                    court_str = "SC" if reporter_str and "SCC" in reporter_str.upper() else court_str
                else:
                    # If no following tokens, default to page 1
                    page = "1"
            else:
                return None

        # Normalize reporter and court
        try:
            year = int(year_str)
        except (ValueError, TypeError):
            return None

        reporter = CaseCitationParser._normalize_reporter(reporter_str)
        court = CaseCitationParser._normalize_court(court_str)
        # Prefer the page extracted from the secondary reporter (if present)
        # otherwise fall back to the main match.group(6), then default to "1".
        if 'page' in locals() and page:
            page = page
        else:
            page = match.group(6) or "1"

        # Extract secondary reports
        secondary_reports = []
        for sec_match in CaseCitationParser.SECONDARY_REPORT_PATTERN.finditer(text):
            sec_year = sec_match.group(1)
            sec_reporter = sec_match.group(3)
            sec_page = sec_match.group(4) or "1"
            
            if sec_reporter:
                sec_rep_type = CaseCitationParser._normalize_reporter(sec_reporter)
                secondary_reports.append((sec_rep_type, int(sec_year), sec_page))

        canonical_id = f"{reporter.value}_{year}_{court.value}_{page}"
        display_name = f"{case_name}, {reporter.value} {year} {court.value} {page}"

        return CaseCitation(
            case_name=case_name,
            year=year,
            primary_reporter=reporter,
            primary_report_page=page,
            court=court,
            secondary_reports=secondary_reports,
            canonical_id=canonical_id,
            display_name=display_name,
            confidence=0.90
        )

    @staticmethod
    def _normalize_reporter(reporter_str: str) -> ReporterType:
        """Normalize reporter type string to enum."""
        if not reporter_str:
            return ReporterType.OTHER
        
        reporter_lower = reporter_str.lower().strip()
        
        if "air" in reporter_lower:
            return ReporterType.AIR
        elif "scc" in reporter_lower:
            return ReporterType.SCC
        elif "cr" in reporter_lower and "lj" in reporter_lower:
            return ReporterType.CR_LJ
        elif "lnind" in reporter_lower:
            return ReporterType.LNIND
        elif "scale" in reporter_lower:
            return ReporterType.SCALE
        elif "jmfc" in reporter_lower:
            return ReporterType.JMFC
        elif "sccc" in reporter_lower:
            return ReporterType.SCCC
        
        return ReporterType.OTHER

    @staticmethod
    def _normalize_court(court_str: Optional[str]) -> CourtType:
        """Normalize court type string to enum."""
        if not court_str:
            return CourtType.OTHER
        
        court_lower = court_str.lower().strip()
        
        if "sc" in court_lower:
            return CourtType.SC
        elif "hc" in court_lower or "high court" in court_lower:
            return CourtType.HC
        elif "dist" in court_lower or "district" in court_lower:
            return CourtType.DIST
        elif "sessions" in court_lower:
            return CourtType.SESSIONS
        elif "crd" in court_lower or "criminal district" in court_lower:
            return CourtType.CRD
        elif "ld" in court_lower or "labour" in court_lower:
            return CourtType.LD
        
        return CourtType.OTHER


class LegalEntityParser:
    """High-level parser for all legal entity types."""

    def __init__(self):
        self.statute_parser = StatuteParser()
        self.section_parser = SectionParser()
        self.case_parser = CaseCitationParser()

    def parse_statute(self, text: str) -> Optional[StatuteReference]:
        """Parse statute reference."""
        return self.statute_parser.parse(text)

    def parse_section(self, text: str, statute: Optional[str] = None) -> Optional[SectionReference]:
        """Parse section reference."""
        return self.section_parser.parse(text, statute)

    def parse_case(self, text: str) -> Optional[CaseCitation]:
        """Parse case citation."""
        return self.case_parser.parse(text)

    def extract_all(self, text: str) -> Dict[str, List]:
        """Extract all legal entities from text.

        Returns:
            {
                'statutes': [StatuteReference, ...],
                'sections': [SectionReference, ...],
                'cases': [CaseCitation, ...],
            }
        """
        statutes = []
        sections = []
        cases = []

        # Extract statutes first
        statute_matches = re.finditer(
            r'(?:under\s+)?(?:the\s+)?(?:Indian|Code|Act|Law|Statute)?\s*([A-Z][A-Za-z\s&,]*(?:Code|Act|Law|Statute))',
            text
        )
        for match in statute_matches:
            statute_text = match.group(1)
            parsed = self.parse_statute(statute_text)
            if parsed:
                statutes.append(parsed)

        # Extract sections (using first statute as context if available)
        primary_statute = statutes[0].abbreviation if statutes else None
        section_matches = re.finditer(
            r'(?:section|sec|§|s\.)\s*(\d+(?:\([0-9a-z]+\))?)',
            text,
            re.IGNORECASE
        )
        for match in section_matches:
            section_text = match.group(0)
            # Try to find statute reference nearby
            context_start = max(0, match.start() - 100)
            context_end = min(len(text), match.end() + 100)
            context = text[context_start:context_end]
            
            parsed = self.parse_section(section_text, primary_statute)
            if parsed:
                sections.append(parsed)

        # Extract case citations
        case_matches = re.finditer(
            r'[A-Z][a-z]+\s+(?:[a-z]+\s+)*v\.?\s+[A-Z][a-z]+.*?(?:,|\.|$)',
            text
        )
        for match in case_matches:
            case_text = match.group(0)
            parsed = self.parse_case(case_text)
            if parsed:
                cases.append(parsed)

        return {
            'statutes': statutes,
            'sections': sections,
            'cases': cases,
        }
