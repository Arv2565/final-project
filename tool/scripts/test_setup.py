#!/usr/bin/env python3
"""
Quick test script to verify PDF to JSON converter setup.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_environment():
    """Check if all required dependencies and environment variables are set."""
    print("=" * 60)
    print("PDF to JSON Converter - Setup Verification")
    print("=" * 60)
    
    checks = {
        "google-generativeai": False,
        "langchain": False,
        "pypdf": False,
        "tqdm": False,
        "pillow": False,
        "GEMINI_API_KEY": False,
        "Kerala Acts Directory": False,
        "Output Directory": False,
    }
    
    # Check Python packages
    packages = [
        ("google-generativeai", "google"),
        ("langchain", "langchain"),
        ("pypdf", "pypdf"),
        ("tqdm", "tqdm"),
        ("pillow", "PIL"),
    ]
    
    print("\n1. Checking Python packages...")
    for package_name, import_name in packages:
        try:
            __import__(import_name)
            checks[package_name] = True
            print(f"   ✓ {package_name}")
        except ImportError:
            print(f"   ✗ {package_name} - NOT INSTALLED")
    
    # Check environment variables
    print("\n2. Checking environment variables...")
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        checks["GEMINI_API_KEY"] = True
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        masked_key = api_key[:10] + "..." + api_key[-5:] if len(api_key) > 15 else "***"
        print(f"   ✓ GEMINI_API_KEY is set ({masked_key})")
    else:
        print("   ✗ GEMINI_API_KEY - NOT SET")
    
    # Check directories
    print("\n3. Checking directories...")
    kerala_acts_dir = Path("/Users/pranav/Documents/Projects/final-project/data/kerala_acts")
    if kerala_acts_dir.exists():
        pdf_count = len(list(kerala_acts_dir.glob("*.pdf")))
        checks["Kerala Acts Directory"] = True
        print(f"   ✓ Kerala Acts Directory exists ({pdf_count} PDFs found)")
    else:
        print(f"   ✗ Kerala Acts Directory - NOT FOUND")
    
    output_dir = Path("/Users/pranav/Documents/Projects/final-project/data/knowledge_base")
    if output_dir.exists():
        checks["Output Directory"] = True
        print(f"   ✓ Output Directory exists")
    else:
        print(f"   ✗ Output Directory - NOT FOUND")
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for check, status in checks.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {check}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All checks passed! Ready to run converter.")
        return True
    else:
        print("\n✗ Some checks failed. Please fix the issues above.")
        if not checks["GOOGLE_API_KEY"]:
            print("\n  To set GOOGLE_API_KEY:")
            print("    export GOOGLE_API_KEY='your-api-key'")
            print("    # or create a .env file with: GOOGLE_API_KEY=your-api-key")
        
        missing_packages = [p for p, status in checks.items() if not status and p not in ["GEMINI_API_KEY", "Kerala Acts Directory", "Output Directory"]]
        if missing_packages:
            print(f"\n  To install missing packages:")
            print(f"    pip install {' '.join(missing_packages)}")
        
        return False


def test_gemini_api():
    """Test if Gemini API is accessible."""
    print("\n" + "=" * 60)
    print("Testing Gemini API Connection")
    print("=" * 60)
    
    try:
        import google.generativeai as genai
        
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            print("✗ GEMINI_API_KEY or GOOGLE_API_KEY not set")
            return False
        
        genai.configure(api_key=api_key)
        
        # Try a simple API call using the model from env
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Respond with just 'OK'")
        
        if response and response.text:
            print(f"✓ Gemini API is accessible")
            print(f"  Response: {response.text.strip()}")
            return True
        else:
            print("✗ Gemini API returned no response")
            return False
    except Exception as e:
        print(f"✗ Gemini API test failed: {e}")
        return False


def test_pdf_processing():
    """Test PDF processing on a sample PDF."""
    print("\n" + "=" * 60)
    print("Testing PDF Processing")
    print("=" * 60)
    
    try:
        from pathlib import Path
        import pypdf
        
        kerala_acts_dir = Path("/Users/pranav/Documents/Projects/final-project/data/kerala_acts")
        pdfs = list(kerala_acts_dir.glob("*.pdf"))
        
        if not pdfs:
            print("✗ No PDFs found in Kerala Acts directory")
            return False
        
        # Test with first PDF
        test_pdf = pdfs[0]
        print(f"\nTesting with: {test_pdf.name}")
        
        reader = pypdf.PdfReader(str(test_pdf))
        page_count = len(reader.pages)
        print(f"✓ PDF loaded successfully ({page_count} pages)")
        
        # Try extracting text from first page
        text = reader.pages[0].extract_text()
        if text:
            print(f"✓ Text extraction successful")
            print(f"  First 100 chars: {text[:100]}...")
        else:
            print(f"⚠ No text extracted (likely scanned PDF)")
        
        return True
    except Exception as e:
        print(f"✗ PDF processing test failed: {e}")
        return False


def show_usage():
    """Show how to use the converter."""
    print("\n" + "=" * 60)
    print("Usage")
    print("=" * 60)
    
    print("""
Quick start:

1. Test with first PDF (dry-run, no files modified):
   python scripts/direct_pdf_to_json_kerala.py --test --dry-run

2. Test with first PDF (actual processing):
   python scripts/direct_pdf_to_json_kerala.py --test

3. Process first 10 PDFs:
   python scripts/direct_pdf_to_json_kerala.py --limit 10

4. Process all PDFs:
   python scripts/direct_pdf_to_json_kerala.py

Options:
  --test              Test with first PDF only
  --limit N           Process first N PDFs
  --dry-run           Don't modify files or knowledge base
  --no-skip-existing  Reprocess PDFs already in knowledge base

For more information, see: docs/KERALA_PDF_TO_JSON_GUIDE.md
    """)


if __name__ == "__main__":
    # Run checks
    env_ok = check_environment()
    
    if not env_ok:
        sys.exit(1)
    
    # Test API
    api_ok = test_gemini_api()
    
    # Test PDF processing
    pdf_ok = test_pdf_processing()
    
    # Show usage
    show_usage()
    
    # Final verdict
    print("\n" + "=" * 60)
    if env_ok and api_ok and pdf_ok:
        print("✓ Everything looks good! Ready to convert PDFs.")
    else:
        print("✗ Some tests failed. Please review the output above.")
    print("=" * 60)
