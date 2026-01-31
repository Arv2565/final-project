import re
from pathlib import Path
from typing import List, Union

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListItem, ListFlowable

def clean_text(text: str) -> str:
    """Clean text for ReportLab Paragraph."""
    # Replace newlines with <br/> for ReportLab
    text = text.replace('\n', '<br/>')
    return text

def parse_markdown_to_flowables(text: str, styles) -> List:
    """
    Parser to convert markdown text into ReportLab Flowables.
    Handles:
    - Headers (#, ##) with bold styling
    - Bold text (**text**) and ALL CAPS phrases
    - Nested Lists (Numbered and Bulleted) with styling
    """
    flowables = []
    lines = text.split('\n')
    
    normal_style = styles["Normal"]
    h1_style = styles["Heading1"]
    h2_style = styles["Heading2"]
    centered_style = styles["CenteredBold"]
    
    # State for list processing
    # We group consecutive list items of the same level/type
    # But effectively, we just need to know "Are we in a list? What level?"
    # To support breaking lists (L1 -> L2 -> L1), we just flush when styling changes.
    
    current_list_items = []
    current_indent = 0 # 0, 1 (sub), etc.
    current_type = None # 'bullet' or 'number'

    def flush_list():
        nonlocal current_list_items, current_indent, current_type
        if current_list_items:
            # Determine styling based on indentation and type
            # Indent: Base 24, +24 per level
            base_indent = 24 + (current_indent * 24)
            
            # Bullet char?
            # If manual value is passed in ListItem, bulletType is ignored for text, but layout matters.
            # We use 'bullet' generic type to let value control the marker.
            
            t = ListFlowable(
                current_list_items,
                bulletType='bullet',
                start='circle',
                leftIndent=base_indent,
                bulletFontSize=11,
                bulletOffsetY=0
            )
            flowables.append(t)
            # flowables.append(Spacer(1, 6)) # Spacing after list block?
            current_list_items = []
            
    for line in lines:
        raw_line = line
        line = line.strip()
        
        # Blank Lines
        if not line:
            flush_list()
            flowables.append(Spacer(1, 6))
            continue
            
        # Bold formatting: **text** -> <b>text</b>
        formatted_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
        
        # Bold ALL CAPS phrases (2+ words) except predictable headers?
        # The prompt mostly wants phrases like WHEREAS, THIS AGREEMENT bolded.
        def bold_replacer(match):
            text = match.group(0)
            return f"<b>{text}</b>"
        formatted_line = re.sub(r'\b([A-Z]{2,}(?:\s+[A-Z]{2,})*)\b', bold_replacer, formatted_line)
        
        # Rupee Fix
        formatted_line = formatted_line.replace('₹', 'Rs.')

        # Calculate Indentation Level (approx 2-4 spaces = 1 level)
        leading_spaces = len(raw_line) - len(raw_line.lstrip())
        indent_level = 0
        if leading_spaces >= 2:
            indent_level = 1
        if leading_spaces >= 6: 
            indent_level = 2

        # Headers
        if line.startswith('# '):
            flush_list()
            flowables.append(Paragraph(formatted_line[2:], h1_style))
            flowables.append(Spacer(1, 12))
            continue
        elif line.startswith('## '):
            flush_list()
            flowables.append(Paragraph(formatted_line[3:], h2_style))
            continue
        elif line.startswith('DRAFT OF '):
            flush_list()
            flowables.append(Paragraph(formatted_line, centered_style))
            continue
            
        # List Items detection
        is_list = False
        marker_val = '•'
        content = formatted_line
        
        # Bullets
        if line.startswith('* ') or line.startswith('- ') or line.startswith('• '):
            is_list = True
            list_type = 'bullet'
            content = formatted_line[2:].strip()
            # Style bullets based on level
            if indent_level == 0:
                marker_val = '•' # Filled circle
            else:
                marker_val = '○' # Open circle (or hyphen '-')
        
        # Numbered (1. or 1) )
        elif re.match(r'^(\d+)\.\s', line):
            is_list = True
            list_type = 'number'
            match = re.match(r'^(\d+)\.\s(.*)', formatted_line)
            marker_val = match.group(1) + '.'
            content = match.group(2).strip()
            
        # Alpha List (a. or b.)
        elif re.match(r'^([a-z])\.\s', line):
            is_list = True
            list_type = 'alpha'
            match = re.match(r'^([a-z])\.\s(.*)', formatted_line)
            marker_val = match.group(1) + '.'
            content = match.group(2).strip()

        if is_list:
            # If indentation or type changed, flush previous group
            if (current_list_items and 
               (indent_level != current_indent or list_type != current_type)):
                flush_list()
            
            current_indent = indent_level
            current_type = list_type
            
            p = Paragraph(content, normal_style)
            current_list_items.append(ListItem(p, value=marker_val))
            
        else:
            # Normal text
            flush_list()
            flowables.append(Paragraph(formatted_line, normal_style))
            # Normal style has spaceAfter=6
            
    flush_list()
    return flowables

def generate_pdf_report(content: str, filename: str) -> str:
    """
    Generate a PDF report from the given text content.
    
    Args:
        content: The text content to include in the PDF (supports basic Markdown).
        filename: The output filename (including path).
        
    Returns:
        The absolute path to the generated PDF.
    """
    output_path = Path(filename).resolve()
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Strict Layout Rules: Aptos (Helvetica as proxy), 11pt, Single Spacing
    # Margins are handled in SimpleDocTemplate below (72pt = 1 inch)
    
    # Body Text: Aptos Regular 11pt, Justified, 6pt space after
    styles["Normal"].fontName = "Helvetica" # Proxy for Aptos
    styles["Normal"].fontSize = 11
    styles["Normal"].leading = 13 # Single spacing approx for 11pt (usually 1.2x = 13.2) or 11/12
    styles["Normal"].alignment = TA_JUSTIFY
    styles["Normal"].spaceAfter = 6
    
    # Headings: Aptos Bold 11pt, Left aligned, 1 blank line (approx 12pt) after
    # Note: User request says "Headings are bold only, same size as body."
    styles["Heading1"].fontName = "Helvetica-Bold"
    styles["Heading1"].fontSize = 11
    styles["Heading1"].leading = 13
    styles["Heading1"].alignment = TA_LEFT
    styles["Heading1"].spaceAfter = 12 # One blank line
    
    styles["Heading2"].fontName = "Helvetica-Bold"
    styles["Heading2"].fontSize = 11
    styles["Heading2"].leading = 13
    styles["Heading2"].alignment = TA_LEFT
    styles["Heading2"].spaceAfter = 12 # One blank line
    styles["Heading2"].spaceBefore = 0 
    
    # Title (used for "What is <Topic>?")
    # Actually, the prompt says "What is..." is a line. It might come as H1.
    # The dedicated Title style for "Legal Analysis Report" might be deprecated or needs to match.
    # User said: "The document must begin with: What is <Topic>? ... Aptos Bold 11pt"
    # So we should probably treat the main title similarly or just use H1.
    title_style = ParagraphStyle(
        'LegalTitle',
        parent=styles['Heading1'],
        fontName="Helvetica-Bold",
        fontSize=11,
        alignment=TA_LEFT, 
        spaceAfter=12
    )

    # Bullet/List Style - "Standard Word hanging indent"
    # Used for Numbered Lists
    bullet_style = ParagraphStyle(
        'LegalBullet',
        parent=styles['Normal'],
        leftIndent=36,       # Hanging indent
        firstLineIndent=-18,  # Number sticks out
        spaceAfter=12,       # "One blank line after list" - handled by flowable separation or here
    )
    
    # Centered Draft Block
    centered_style = ParagraphStyle(
        'CenteredBold',
        parent=styles['Normal'],
        fontName="Helvetica-Bold",
        alignment=1, # Center
        spaceAfter=12
    )
    styles.add(centered_style)

    # Create the report content
    story = []
    
    # Title
    story.append(Paragraph("Legal Analysis Report", title_style))
    story.append(Spacer(1, 12))

    # Parse content
    flowables = parse_markdown_to_flowables(content, styles)
    story.extend(flowables)
    
    # Footer disclaimer
    story.append(Spacer(1, 36))
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Italic'],
        fontSize=8,
        textColor=colors.gray
    )
    story.append(Paragraph("Disclaimer: This document is generated by an AI assistant. It is for informational purposes only and does not constitute professional legal advice.", disclaimer_style))

    doc.build(story)
    return str(output_path)
