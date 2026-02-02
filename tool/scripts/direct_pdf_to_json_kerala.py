"""
Direct PDF to JSON converter for Kerala Acts using Gemini API.
Simpler than agent-based approach, handles scanned PDFs with OCR via Gemini Vision.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, List
import argparse
import base64
from io import BytesIO
from dotenv import load_dotenv
import pandas as pd

import pypdf
import google.generativeai as genai
from PIL import Image
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

# Configuration
KERALA_ACTS_DIR = Path("/Users/pranav/Documents/Projects/final-project/data/kerala_acts")
OUTPUT_JSON_PATH = Path("/Users/pranav/Documents/Projects/final-project/data/knowledge_base/kerala_acts.json")
ERROR_LOG_PATH = Path("/Users/pranav/Documents/Projects/final-project/data/knowledge_base/processing_errors.log")
SUMMARY_REPORT_PATH = Path("/Users/pranav/Documents/Projects/final-project/data/knowledge_base/processing_summary.txt")
MAX_PAGES_IGNORE = 50
LARGE_PDF_THRESHOLD = 20

# Ensure output directory exists
OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Configure logging - both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler(ERROR_LOG_PATH, mode='a')  # File logging (append mode)
    ]
)
logger = logging.getLogger(__name__)

# Initialize Gemini API - use GEMINI_API_KEY from .env file
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in .env file or environment")
genai.configure(api_key=api_key)

# Get model name from environment or use default
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Check for poppler availability for PDF image extraction
HAS_POPPLER = False
try:
    from pdf2image import convert_from_path
    # Quick test if poppler is available
    HAS_POPPLER = True
except ImportError:
    logger.warning("pdf2image not installed. Scanned PDF OCR will be limited.")
    HAS_POPPLER = False


def get_pdf_page_count(pdf_path: Path) -> Optional[int]:
    """Get the total number of pages in a PDF."""
    try:
        pdf = pypdf.PdfReader(str(pdf_path))
        return len(pdf.pages)
    except Exception as e:
        logger.error(f"Error getting page count for {pdf_path.name}: {e}")
        return None


def extract_text_from_pdf(pdf_path: Path, page_start: int = 0, page_end: Optional[int] = None) -> str:
    """
    Extract text from specific pages of a PDF.
    
    Args:
        pdf_path: Path to PDF
        page_start: Starting page (0-indexed)
        page_end: Ending page (0-indexed, inclusive)
        
    Returns:
        Extracted text
    """
    try:
        pdf = pypdf.PdfReader(str(pdf_path))
        total_pages = len(pdf.pages)
        
        end = min(page_end + 1 if page_end is not None else total_pages, total_pages)
        
        text = ""
        for page_num in range(page_start, end):
            page = pdf.pages[page_num]
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path.name}: {e}")
        return ""


def extract_page_as_image(pdf_path: Path, page_num: int) -> Optional[str]:
    """
    Extract a single page as an image and encode to base64.
    Uses pdf2image or converts PDF page to image via PIL.
    
    Args:
        pdf_path: Path to PDF
        page_num: Page number (0-indexed)
        
    Returns:
        Base64 encoded image string or None
    """
    try:
        from pdf2image import convert_from_path
        
        # Extract single page as image
        images = convert_from_path(str(pdf_path), first_page=page_num+1, last_page=page_num+1, dpi=150)
        
        if not images:
            return None
        
        # Convert to base64
        img_buffer = BytesIO()
        images[0].save(img_buffer, format='PNG')
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return img_base64
    except ImportError:
        logger.warning("pdf2image not installed, falling back to text extraction")
        return None
    except Exception as e:
        logger.warning(f"Error extracting page as image from {pdf_path.name}: {e}")
        return None


def process_pdf_with_gemini(text_content: str, images: List[str], pdf_filename: str) -> Optional[Dict]:
    """
    Send extracted content to Gemini API for JSON conversion.
    
    Args:
        text_content: Extracted text from PDF
        images: List of base64 encoded images
        pdf_filename: Original PDF filename
        
    Returns:
        Dictionary with act information or None on error
    """
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Build the request
        content = []
        
        # Add filename for context
        if text_content:
            # Text-based PDF
            prompt = f"""You are analyzing a Kerala legal act document: {pdf_filename}

Extract COMPREHENSIVE information about this legal act and return ONLY valid JSON:

{{
    "title": "Full official title of the act",
    "act_number": "Act number/reference if available",
    "year": "Year of enactment",
    "purpose": "Clear statement of the act's purpose and objectives",
    "scope": "Who/what/where the act applies to - geographical and subject matter scope",
    "key_definitions": {{
        "definition_1": "explanation",
        "definition_2": "explanation"
    }},
    "main_sections": [
        {{
            "section_number": "1",
            "section_title": "Name of section",
            "description": "What this section covers"
        }},
        {{
            "section_number": "2",
            "section_title": "Name",
            "description": "Details"
        }}
    ],
    "important_rules": [
        "Rule 1: Description of rule and what must be done",
        "Rule 2: Description",
        "Rule 3: Description"
    ],
    "penalties_and_enforcement": {{
        "penalties": ["Penalty 1: description", "Penalty 2: description"],
        "enforcement_authority": "Who enforces this act",
        "how_enforced": "Methods of enforcement"
    }},
    "rights_and_duties": {{
        "rights": ["Right 1", "Right 2"],
        "duties": ["Duty 1", "Duty 2"],
        "obligations": ["Obligation 1", "Obligation 2"]
    }},
    "key_procedures": [
        "Procedure 1: Step-by-step process",
        "Procedure 2: Step-by-step process"
    ],
    "administration": "Department/agency administering this act",
    "important_notes": [
        "Note 1: Any exceptions or special cases",
        "Note 2: Any important conditions or limitations"
    ]
}}

Document text (first 15000 characters):
{text_content[:15000]}

Return ONLY valid JSON, no markdown, no explanations."""
            content.append(prompt)
        elif images:
            # Scanned PDF - use Gemini's vision capability
            prompt = f"""You are analyzing a scanned image of a Kerala legal act: {pdf_filename}

Extract COMPREHENSIVE information from the images and return ONLY valid JSON:

{{
    "title": "Full official title (from document or inferred from filename)",
    "act_number": "Act number/reference if visible",
    "year": "Year of enactment if visible",
    "purpose": "Purpose and objectives of the act",
    "scope": "Application - who/what/where the act applies",
    "key_definitions": {{
        "definition_1": "explanation",
        "definition_2": "explanation"
    }},
    "main_sections": [
        {{
            "section_number": "1",
            "section_title": "Title from document",
            "description": "What this section covers"
        }},
        {{
            "section_number": "2",
            "section_title": "Title",
            "description": "Details"
        }}
    ],
    "important_rules": [
        "Rule 1: What must/must not be done",
        "Rule 2: Description",
        "Rule 3: Description"
    ],
    "penalties_and_enforcement": {{
        "penalties": ["Penalty 1 with amount/duration", "Penalty 2"],
        "enforcement_authority": "Who enforces this",
        "how_enforced": "Methods of enforcement"
    }},
    "rights_and_duties": {{
        "rights": ["Right 1", "Right 2"],
        "duties": ["Duty 1", "Duty 2"],
        "obligations": ["Obligation 1"]
    }},
    "key_procedures": [
        "Procedure 1: Step-by-step process",
        "Procedure 2: How to comply"
    ],
    "administration": "Department/agency that administers this",
    "important_notes": [
        "Exception 1",
        "Special condition",
        "Limitation or clarification"
    ]
}}

Return ONLY valid JSON, no markdown or explanations."""
            
            content.append(prompt)
            
            # Add images in correct Gemini API format - send all extracted images
            for img_base64 in images:
                content.append({
                    "mime_type": "image/png",
                    "data": img_base64,
                })
        else:
            logger.warning(f"No text or images for {pdf_filename}")
            return None
        
        # Call Gemini
        response = model.generate_content(content)
        response_text = response.text.strip()
        
        # Try to extract JSON if wrapped in markdown
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        # Parse and validate JSON
        result = json.loads(response_text)
        
        # Ensure all required fields exist with proper defaults
        required_fields = {
            "title": "Not specified",
            "act_number": "Not provided",
            "year": "Not provided",
            "purpose": "Not specified",
            "scope": "Not specified",
            "key_definitions": {},
            "main_sections": [],
            "important_rules": [],
            "penalties_and_enforcement": {
                "penalties": [],
                "enforcement_authority": "Not specified",
                "how_enforced": "Not specified"
            },
            "rights_and_duties": {
                "rights": [],
                "duties": [],
                "obligations": []
            },
            "key_procedures": [],
            "administration": "Not specified",
            "important_notes": []
        }
        
        for field, default_value in required_fields.items():
            if field not in result:
                result[field] = default_value
        
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error for {pdf_filename}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing with Gemini for {pdf_filename}: {e}")
        return None


def load_existing_knowledge_base() -> List[Dict]:
    """Load existing knowledge base or return empty list."""
    if OUTPUT_JSON_PATH.exists():
        try:
            with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    return [data]
        except json.JSONDecodeError:
            logger.warning("Knowledge base file is invalid JSON, starting fresh")
            return []
    return []


def save_knowledge_base(data: List[Dict]):
    """Save knowledge base to file. Always appends by loading existing first."""
    try:
        # Always merge with existing to ensure no data loss
        existing = []
        if OUTPUT_JSON_PATH.exists():
            try:
                with open(OUTPUT_JSON_PATH, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    if not isinstance(existing, list):
                        existing = [existing]
            except json.JSONDecodeError:
                existing = []
        
        # Merge: keep existing, add any new ones from data
        existing_titles = {act.get('title', '') for act in existing}
        for act in data:
            if act.get('title', '') not in existing_titles:
                existing.append(act)
                existing_titles.add(act.get('title', ''))
        
        with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        logger.info(f"Knowledge base saved: {len(existing)} total acts")
    except Exception as e:
        logger.error(f"Error saving knowledge base: {e}")


def process_pdf(pdf_path: Path, dry_run: bool = False) -> bool:
    """
    Process a single PDF file.
    
    Args:
        pdf_path: Path to PDF
        dry_run: If True, don't delete the PDF or modify knowledge base
        
    Returns:
        True if successful, False otherwise
    """
    filename = pdf_path.name
    
    # Get page count
    page_count = get_pdf_page_count(pdf_path)
    if page_count is None:
        logger.error(f"Could not determine page count for {filename}")
        return False
    
    logger.info(f"Processing {filename} ({page_count} pages)")
    
    # Skip if > 50 pages
    if page_count > MAX_PAGES_IGNORE:
        logger.info(f"Skipping {filename} - too many pages ({page_count} > {MAX_PAGES_IGNORE})")
        return False
    
    # Determine which pages to process
    if page_count > LARGE_PDF_THRESHOLD:
        # Process latter half only
        start_page = page_count // 2
        end_page = page_count - 1
        logger.info(f"Processing latter half (pages {start_page}-{end_page})")
    else:
        # Process all pages
        start_page = 0
        end_page = page_count - 1
        logger.info(f"Processing all pages (0-{end_page})")
    
    # Extract text
    text_content = extract_text_from_pdf(pdf_path, start_page, end_page)
    
    images = []
    if not text_content or len(text_content) < 100:
        # Try to extract images for scanned PDFs
        logger.info(f"Minimal or no text found, attempting to extract images")
        
        # Extract multiple pages as images for better OCR
        for page_num in range(start_page, min(end_page + 1, start_page + 8)):
            img = extract_page_as_image(pdf_path, page_num)
            if img:
                images.append(img)
                logger.info(f"Extracted image from page {page_num + 1}")
    
    # Process with Gemini
    act_data = process_pdf_with_gemini(text_content, images, filename)
    
    if not act_data:
        logger.error(f"Failed to process {filename}")
        return False
    
    logger.info(f"Successfully converted: {act_data.get('title', 'Unknown')}")
    
    # Append to knowledge base
    if not dry_run:
        knowledge_base = load_existing_knowledge_base()
        knowledge_base.append(act_data)
        save_knowledge_base(knowledge_base)
        
        # Delete original PDF
        try:
            pdf_path.unlink()
            logger.info(f"Deleted: {filename}")
        except Exception as e:
            logger.error(f"Error deleting {filename}: {e}")
    else:
        logger.info(f"[DRY RUN] Would append to knowledge base and delete {filename}")
    
    return True


def process_all_pdfs(limit: Optional[int] = None, dry_run: bool = False, skip_existing: bool = True):
    """
    Process all PDFs in the kerala_acts directory.
    
    Args:
        limit: Maximum number of PDFs to process
        dry_run: If True, don't modify files or knowledge base
        skip_existing: If True, skip PDFs already in knowledge base
    """
    logger.info(f"Starting PDF processing from {KERALA_ACTS_DIR}")
    logger.info(f"Output file: {OUTPUT_JSON_PATH}")
    logger.info(f"Error log: {ERROR_LOG_PATH}")
    logger.info(f"Summary report: {SUMMARY_REPORT_PATH}")
    logger.info(f"Poppler available: {HAS_POPPLER}")
    
    if dry_run:
        logger.warning("Running in DRY RUN mode - no files will be modified")
    
    # Get all PDFs
    pdf_files = sorted(KERALA_ACTS_DIR.glob("*.pdf"))
    
    if limit:
        pdf_files = pdf_files[:limit]
    
    logger.info(f"Found {len(pdf_files)} PDFs to process")
    
    # Load existing knowledge base if skipping
    existing_titles = set()
    if skip_existing:
        kb = load_existing_knowledge_base()
        existing_titles = {act.get('title', '') for act in kb}
        logger.info(f"Loaded {len(existing_titles)} existing acts from knowledge base")
    
    # Track errors and statistics
    successful = 0
    skipped = 0
    failed = 0
    failed_pdfs = []  # Track which PDFs failed
    
    for pdf_path in tqdm(pdf_files, desc="Processing PDFs"):
        if skip_existing and any(pdf_path.stem in title for title in existing_titles):
            logger.info(f"Skipping {pdf_path.name} - already in knowledge base")
            skipped += 1
            continue
        
        try:
            if process_pdf(pdf_path, dry_run=dry_run):
                successful += 1
            else:
                failed += 1
                failed_pdfs.append(pdf_path.name)
        except Exception as e:
            logger.error(f"Unexpected error processing {pdf_path.name}: {e}")
            failed += 1
            failed_pdfs.append(pdf_path.name)
    
    # Create comprehensive summary report
    summary_lines = [
        "=" * 80,
        "PDF PROCESSING SUMMARY REPORT",
        "=" * 80,
        f"Timestamp: {pd.Timestamp.now()}",
        f"Input directory: {KERALA_ACTS_DIR}",
        f"Output KB: {OUTPUT_JSON_PATH}",
        f"Error log: {ERROR_LOG_PATH}",
        "",
        "STATISTICS:",
        "-" * 80,
        f"Total PDFs found: {len(pdf_files)}",
        f"Successful: {successful}",
        f"Failed: {failed}",
        f"Skipped (existing): {skipped}",
        f"Processed: {successful + failed + skipped}/{len(pdf_files)}",
        f"Success rate: {(successful / (successful + failed) * 100):.1f}%" if (successful + failed) > 0 else "N/A",
        "",
    ]
    
    if not dry_run:
        kb = load_existing_knowledge_base()
        summary_lines.extend([
            f"Knowledge base acts: {len(kb)}",
            "",
        ])
    
    if failed_pdfs:
        summary_lines.extend([
            "FAILED PDFs (see error log for details):",
            "-" * 80,
        ])
        for pdf_name in failed_pdfs:
            summary_lines.append(f"  - {pdf_name}")
        summary_lines.append("")
    
    summary_lines.extend([
        "=" * 80,
        "Check error log for detailed error messages.",
        "=" * 80,
    ])
    
    # Write summary to file
    summary_text = "\n".join(summary_lines)
    with open(SUMMARY_REPORT_PATH, 'w') as f:
        f.write(summary_text)
    
    # Log summary
    for line in summary_lines:
        logger.info(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Kerala Acts PDFs to JSON format")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of PDFs to process")
    parser.add_argument("--test", action="store_true", help="Test mode with first PDF only")
    parser.add_argument("--dry-run", action="store_true", help="Don't modify files or knowledge base")
    parser.add_argument("--no-skip-existing", action="store_true", help="Don't skip existing acts in knowledge base")
    
    args = parser.parse_args()
    
    if args.test:
        args.limit = 1
    
    process_all_pdfs(
        limit=args.limit,
        dry_run=args.dry_run,
        skip_existing=not args.no_skip_existing
    )
