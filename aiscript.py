import os
import json
import time
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
from typing import Dict, List, Any

# Load environment variables from .env file
load_dotenv()

class GeminiPDFProcessor:
    def __init__(self):
        """
        Initialize Gemini PDF Processor with API key from .env file
        """
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")

        # Configure Gemini API
        genai.configure(api_key=self.api_key)

        # Initialize model
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Generation config for consistent responses
        self.generation_config = {
            'temperature': 0.1,
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 8192,
        }

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return ""

    def upload_pdf_to_gemini(self, pdf_path: str):
        """Upload PDF file to Gemini for processing"""
        try:
            uploaded_file = genai.upload_file(
                path=pdf_path,
                display_name=os.path.basename(pdf_path)
            )

            # Wait for file to be processed
            while uploaded_file.state.name == "PROCESSING":
                print("Waiting for file to be processed...")
                time.sleep(2)
                uploaded_file = genai.get_file(uploaded_file.name)

            if uploaded_file.state.name == "FAILED":
                raise ValueError(f"File processing failed: {uploaded_file.state.name}")

            return uploaded_file

        except Exception as e:
            print(f"Error uploading PDF to Gemini: {e}")
            return None

    def get_content_extraction_prompt(self) -> str:
        """
        Generate a focused prompt for content extraction that's LLM-friendly
        """
        return """
        Extract and structure ALL meaningful content from this document in a clean, organized JSON format.
        Focus on making the content easily understandable and queryable by language models.

        Return ONLY valid JSON with this structure:

        {
            "document_info": {
                "title": "Main title or heading of the document",
                "type": "document type (act, notification, report, manual, etc.)",
                "reference_number": "any document/file/act numbers",
                "date": "any dates mentioned",
                "authority": "issuing authority or department"
            },
            "main_content": {
                "purpose": "What is this document about and why was it created",
                "summary": "Comprehensive summary of the entire document",
                "key_points": [
                    "List of all important points, decisions, or provisions",
                    "Each point should be self-contained and clear"
                ]
            },
            "detailed_sections": [
                {
                    "section_title": "Section name or number",
                    "content": "Full content of this section in clear, readable format",
                    "key_details": ["Specific important details from this section"]
                }
            ],
            "rules_and_provisions": [
                {
                    "rule": "What the rule states",
                    "details": "Specific requirements, conditions, or explanations",
                    "applies_to": "Who or what this applies to"
                }
            ],
            "penalties_and_consequences": [
                {
                    "violation": "What constitutes a violation",
                    "penalty": "What the penalty is",
                    "amount": "Specific amounts if mentioned",
                    "conditions": "Any conditions or circumstances"
                }
            ],
            "important_entities": {
                "people": ["Names of people mentioned"],
                "organizations": ["Government bodies, departments, organizations"],
                "locations": ["Places, addresses, jurisdictions mentioned"],
                "amounts": ["All monetary amounts, fees, fines mentioned"],
                "dates": ["All dates mentioned"],
                "references": ["References to other documents, acts, rules"]
            },
            "action_items": [
                "Things that need to be done",
                "Compliance requirements",
                "Implementation steps"
            ],
            "definitions": [
                {
                    "term": "Technical term or concept",
                    "definition": "What it means in context"
                }
            ],
            "full_text_content": "The complete text content cleaned and formatted for readability"
        }

        IMPORTANT INSTRUCTIONS:
        1. Extract ALL content - don't skip anything important
        2. Clean up OCR errors and formatting issues
        3. Convert any non-English content to English if possible, or indicate what language it is
        4. Make everything readable and understandable
        5. Preserve all numbers, dates, and specific details exactly
        6. If there are tables or lists, format them clearly
        7. Remove administrative headers/footers unless they contain important info
        8. Focus on substance, not formatting artifacts
        """

    def process_pdf_with_gemini(self, pdf_path: str, custom_prompt: str = None) -> Dict[str, Any]:
        """Process PDF using Gemini API"""
        
        # Use custom prompt or default content extraction prompt
        processing_prompt = custom_prompt or self.get_content_extraction_prompt()

        try:
            # Try direct PDF upload first
            uploaded_file = self.upload_pdf_to_gemini(pdf_path)

            if uploaded_file:
                try:
                    response = self.model.generate_content(
                        [uploaded_file, processing_prompt],
                        generation_config=self.generation_config
                    )

                    response_text = response.text

                    # Clean up uploaded file
                    try:
                        genai.delete_file(uploaded_file.name)
                    except:
                        pass

                    return self.parse_json_response(response_text, "direct_upload")

                except Exception as api_error:
                    print(f"Direct PDF processing failed: {api_error}")
                    # Clean up uploaded file
                    try:
                        genai.delete_file(uploaded_file.name)
                    except:
                        pass
                    # Fallback to text extraction
                    return self.process_text_with_gemini(pdf_path, processing_prompt)
            else:
                # Fallback to text extraction method
                return self.process_text_with_gemini(pdf_path, processing_prompt)

        except Exception as e:
            print(f"Error processing PDF {pdf_path}: {e}")
            return {"error": str(e), "file": pdf_path}

    def process_text_with_gemini(self, pdf_path: str, processing_prompt: str) -> Dict[str, Any]:
        """Fallback method: Extract text first, then process with Gemini"""
        print(f"Using text extraction fallback for {pdf_path}")

        # Extract text from PDF
        pdf_text = self.extract_text_from_pdf(pdf_path)

        if not pdf_text:
            return {"error": "Could not extract text from PDF", "file": pdf_path}

        # Handle long documents by splitting if necessary
        max_chars = 100000  # Approximately 25k tokens
        if len(pdf_text) > max_chars:
            # Try to split at natural boundaries (double newlines, section breaks)
            chunks = self.smart_text_split(pdf_text, max_chars)
            if len(chunks) > 1:
                return self.process_multi_chunk_document(chunks, processing_prompt, pdf_path)
            else:
                # Fallback to simple truncation
                pdf_text = pdf_text[:max_chars] + "\n\n[TEXT TRUNCATED - DOCUMENT CONTINUES]"
                print(f"Warning: Text truncated for {pdf_path} due to length")

        # Process with Gemini
        try:
            full_prompt = f"{processing_prompt}\n\nDocument content:\n{pdf_text}"

            response = self.model.generate_content(
                full_prompt,
                generation_config=self.generation_config
            )

            return self.parse_json_response(response.text, "text_extraction")

        except Exception as e:
            print(f"Error processing text with Gemini: {e}")
            return {"error": str(e), "file": pdf_path}

    def smart_text_split(self, text: str, max_chars: int) -> List[str]:
        """Split text intelligently at natural boundaries"""
        if len(text) <= max_chars:
            return [text]

        chunks = []
        current_chunk = ""
        
        # Split by double newlines first (paragraphs)
        paragraphs = text.split('\n\n')
        
        for para in paragraphs:
            # If adding this paragraph would exceed limit
            if len(current_chunk) + len(para) + 2 > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    # Single paragraph is too long, split by sentences
                    sentences = para.split('. ')
                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 2 > max_chars:
                            if current_chunk:
                                chunks.append(current_chunk.strip())
                                current_chunk = sentence
                            else:
                                # Even single sentence too long, truncate
                                chunks.append(sentence[:max_chars])
                                current_chunk = ""
                        else:
                            current_chunk += sentence + ". "
            else:
                current_chunk += para + "\n\n"
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks

    def process_multi_chunk_document(self, chunks: List[str], processing_prompt: str, pdf_path: str) -> Dict[str, Any]:
        """Process document that was split into multiple chunks"""
        print(f"Processing {len(chunks)} chunks for {pdf_path}")
        
        chunk_results = []
        
        for i, chunk in enumerate(chunks, 1):
            print(f"Processing chunk {i}/{len(chunks)}")
            
            chunk_prompt = f"""
            This is part {i} of {len(chunks)} of a larger document. 
            Extract all content from this section following the same JSON structure.
            Mark this as "chunk_{i}_of_{len(chunks)}" in the response.
            
            {processing_prompt}
            
            Document section content:
            {chunk}
            """
            
            try:
                response = self.model.generate_content(
                    chunk_prompt,
                    generation_config=self.generation_config
                )
                
                chunk_result = self.parse_json_response(response.text, f"chunk_{i}")
                chunk_results.append(chunk_result)
                
                # Brief delay between chunks
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing chunk {i}: {e}")
                chunk_results.append({"error": str(e), "chunk": i})

        # Merge chunk results into a single comprehensive result
        return self.merge_chunk_results(chunk_results, pdf_path)

    def merge_chunk_results(self, chunk_results: List[Dict], pdf_path: str) -> Dict[str, Any]:
        """Merge results from multiple chunks into a single comprehensive result"""
        merged = {
            "document_info": {},
            "main_content": {
                "purpose": "",
                "summary": "",
                "key_points": []
            },
            "detailed_sections": [],
            "rules_and_provisions": [],
            "penalties_and_consequences": [],
            "important_entities": {
                "people": [],
                "organizations": [],
                "locations": [],
                "amounts": [],
                "dates": [],
                "references": []
            },
            "action_items": [],
            "definitions": [],
            "full_text_content": "",
            "processing_method": "multi_chunk",
            "total_chunks": len(chunk_results)
        }

        # Merge data from all chunks
        for chunk_result in chunk_results:
            if "error" in chunk_result:
                continue
                
            # Merge document info (take first non-empty values)
            if not merged["document_info"] and chunk_result.get("document_info"):
                merged["document_info"] = chunk_result["document_info"]
            
            # Merge main content
            main_content = chunk_result.get("main_content", {})
            if main_content.get("purpose") and not merged["main_content"]["purpose"]:
                merged["main_content"]["purpose"] = main_content["purpose"]
            
            if main_content.get("summary"):
                merged["main_content"]["summary"] += " " + main_content["summary"]
            
            if main_content.get("key_points"):
                merged["main_content"]["key_points"].extend(main_content["key_points"])
            
            # Merge sections and other arrays
            for field in ["detailed_sections", "rules_and_provisions", "penalties_and_consequences", "action_items", "definitions"]:
                if chunk_result.get(field):
                    merged[field].extend(chunk_result[field])
            
            # Merge entities
            entities = chunk_result.get("important_entities", {})
            for entity_type in merged["important_entities"]:
                if entities.get(entity_type):
                    merged["important_entities"][entity_type].extend(entities[entity_type])
            
            # Concatenate full text
            if chunk_result.get("full_text_content"):
                merged["full_text_content"] += "\n\n" + chunk_result["full_text_content"]

        # Clean up duplicates
        for entity_type in merged["important_entities"]:
            merged["important_entities"][entity_type] = list(set(merged["important_entities"][entity_type]))
        
        merged["main_content"]["key_points"] = list(dict.fromkeys(merged["main_content"]["key_points"]))  # Remove duplicates preserving order
        
        return merged

    def parse_json_response(self, response_text: str, method: str) -> Dict[str, Any]:
        """Parse JSON from Gemini response with robust error handling"""
        try:
            # Clean response text
            cleaned_text = response_text.strip()
            
            # Remove markdown formatting
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            elif cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]

            # Find JSON boundaries
            brace_count = 0
            start_idx = -1
            end_idx = -1
            
            for i, char in enumerate(cleaned_text):
                if char == '{':
                    if start_idx == -1:
                        start_idx = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_idx != -1:
                        end_idx = i + 1
                        break

            if start_idx != -1 and end_idx != -1:
                json_str = cleaned_text[start_idx:end_idx]
                
                # Clean up common JSON issues
                json_str = self.clean_json_string(json_str)
                
                parsed_json = json.loads(json_str)
                parsed_json["processing_method"] = method
                parsed_json["processed_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
                return parsed_json
            else:
                return {
                    "raw_response": response_text,
                    "processing_method": method,
                    "error": "No valid JSON structure found",
                    "note": "Content extraction failed - check raw_response for manual review"
                }

        except json.JSONDecodeError as e:
            return {
                "raw_response": response_text,
                "processing_method": method,
                "json_error": str(e),
                "error": "JSON parsing failed",
                "note": "Content extraction failed - check raw_response for manual review"
            }

    def clean_json_string(self, json_str: str) -> str:
        """Clean up common JSON formatting issues"""
        import re
        
        # Remove control characters
        json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)
        
        # Fix trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Fix broken strings across lines
        json_str = re.sub(r'(["\w])\s*\n\s*(["\w])', r'\1 \2', json_str)
        
        # Fix unescaped quotes in strings
        json_str = re.sub(r'(?<!\\)"(?=.*".*:)', '\\"', json_str)
        
        return json_str

    def process_directory(self,
                         pdf_directory: str,
                         output_directory: str,
                         custom_prompt: str = None,
                         delay_seconds: float = 3.0) -> Dict[str, Any]:
        """Process all PDFs in a directory"""

        # Create output directory
        os.makedirs(output_directory, exist_ok=True)

        # Find PDF files
        pdf_files = list(Path(pdf_directory).glob("*.pdf"))

        if not pdf_files:
            print(f"No PDF files found in {pdf_directory}")
            return {"error": "No PDF files found"}

        print(f"Found {len(pdf_files)} PDF files to process")

        results = {
            "total_files": len(pdf_files),
            "processed_successfully": 0,
            "failed": 0,
            "results": [],
            "processing_started": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"\n{'='*60}")
            print(f"Processing {i}/{len(pdf_files)}: {pdf_path.name}")
            print(f"{'='*60}")

            try:
                # Process PDF
                processed_data = self.process_pdf_with_gemini(str(pdf_path), custom_prompt)

                # Create output filename
                output_filename = f"{pdf_path.stem}_extracted.json"
                output_path = os.path.join(output_directory, output_filename)

                # Add file metadata
                processed_data["source_file"] = pdf_path.name
                processed_data["file_size_bytes"] = pdf_path.stat().st_size
                processed_data["extraction_timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")

                # Save JSON file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, indent=2, ensure_ascii=False)

                print(f"✓ Successfully extracted content to: {output_filename}")
                
                # Show brief summary
                if "main_content" in processed_data:
                    summary = processed_data["main_content"].get("summary", "")
                    if summary:
                        print(f"📄 Summary: {summary[:200]}...")

                results["processed_successfully"] += 1
                results["results"].append({
                    "file": pdf_path.name,
                    "status": "success",
                    "output": output_filename,
                    "method": processed_data.get("processing_method", "unknown")
                })

            except Exception as e:
                print(f"✗ Failed to process {pdf_path.name}: {e}")
                results["failed"] += 1
                results["results"].append({
                    "file": pdf_path.name,
                    "status": "failed",
                    "error": str(e)
                })

            # Delay between requests
            if i < len(pdf_files):
                print(f"⏱️  Waiting {delay_seconds} seconds before next file...")
                time.sleep(delay_seconds)

        # Save summary
        results["processing_completed"] = time.strftime("%Y-%m-%d %H:%M:%S")
        summary_path = os.path.join(output_directory, "extraction_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"EXTRACTION COMPLETE")
        print(f"{'='*60}")
        print(f"📊 Total files: {results['total_files']}")
        print(f"✅ Successfully processed: {results['processed_successfully']}")
        print(f"❌ Failed: {results['failed']}")
        print(f"📁 Results saved to: {output_directory}")
        print(f"📋 Summary: {summary_path}")

        return results

def create_env_template():
    """Create .env template file"""
    template_content = """# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Get your API key from: https://makersuite.google.com/app/apikey
"""

    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(template_content)
        print("Created .env template file. Please add your GEMINI_API_KEY.")
        return False
    return True

def main():
    """Main function"""
    
    if not create_env_template():
        return

    load_dotenv()

    if not os.getenv('GEMINI_API_KEY'):
        print("❌ Error: GEMINI_API_KEY not found in .env file")
        print("Please add your Gemini API key to the .env file")
        return

    # Get input directory
    pdf_dir = input("📁 Enter PDF directory path (default: './pdfs'): ").strip()
    if not pdf_dir:
        pdf_dir = "./pdfs"

    if not os.path.exists(pdf_dir):
        print(f"❌ Error: Directory '{pdf_dir}' does not exist")
        return

    # Get output directory
    output_dir = input("📤 Enter output directory path (default: './extracted_content'): ").strip()
    if not output_dir:
        output_dir = "./extracted_content"

    # Ask about custom prompt
    use_custom = input("🎯 Use custom extraction prompt? (y/n, default: n): ").strip().lower()
    custom_prompt = None

    if use_custom in ['y', 'yes']:
        print("✏️  Enter your custom prompt (press Enter twice to finish):")
        prompt_lines = []
        empty_lines = 0
        while empty_lines < 2:
            line = input()
            if line == "":
                empty_lines += 1
            else:
                empty_lines = 0
            prompt_lines.append(line)
        custom_prompt = "\n".join(prompt_lines[:-2])

    # Set delay
    delay = input("⏱️  Enter delay between requests in seconds (default: 3): ").strip()
    try:
        delay_seconds = float(delay) if delay else 3.0
    except ValueError:
        delay_seconds = 3.0

    # Start processing
    try:
        print("🚀 Initializing Gemini PDF Content Extractor...")
        processor = GeminiPDFProcessor()

        results = processor.process_directory(
            pdf_directory=pdf_dir,
            output_directory=output_dir,
            custom_prompt=custom_prompt,
            delay_seconds=delay_seconds
        )

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()