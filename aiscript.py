import os
import json
import time
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
import PyPDF2
from typing import Dict, List, Any
import PIL.Image

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

        # Initialize model (Gemini Pro with vision capabilities)
        self.model = genai.GenerativeModel('gemini-1.5-flash')

        # Generation config for consistent responses
        self.generation_config = {
            'temperature': 0.1,
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 8192,
        }

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            str: Extracted text from PDF
        """
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

    def upload_pdf_to_gemini(self, pdf_path: str) -> str:
        """
        Upload PDF file to Gemini for processing

        Args:
            pdf_path (str): Path to the PDF file

        Returns:
            str: File URI from Gemini
        """
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

    def process_pdf_with_gemini(self, pdf_path: str, processing_prompt: str = None) -> Dict[str, Any]:
        """
        Process PDF using Gemini API

        Args:
            pdf_path (str): Path to the PDF file
            processing_prompt (str): Custom prompt for processing

        Returns:
            Dict[str, Any]: Processed data from Gemini
        """

        # Default processing prompt
        if not processing_prompt:
            processing_prompt = """
            Please analyze this PDF document and extract the following information in JSON format.
            Return ONLY the JSON response, no additional text or formatting unless it is any other language than english if so, convert it to english:

            {
                "title": "Document title",
                "summary": "Brief summary of the document (2-3 sentences)",
                "key_points": ["List of key points or main topics"],
                "metadata": {
                    "document_type": "Type of document (report, paper, manual, etc.)",
                    "estimated_pages": "Number of pages if determinable",
                    "date_mentions": "Any dates mentioned in the document",
                    "author_info": "Author information if available"
                },
                "sections": [
                    {
                        "heading": "Section heading",
                        "content": "Summary of section content"
                    }
                ],
                "entities": {
                    "people": ["Names of people mentioned"],
                    "organizations": ["Organizations mentioned"],
                    "locations": ["Places mentioned"],
                    "dates": ["Important dates"],
                    "key_numbers": ["Key numbers or statistics"]
                },
                "actionable_items": ["Any action items, recommendations, or next steps mentioned"],
                "keywords": ["Important keywords or technical terms"]
            }

            Please provide accurate information based on the document content. If certain information is not available, use null or empty arrays as appropriate.
            """

        try:
            # First, try to upload PDF directly to Gemini
            uploaded_file = self.upload_pdf_to_gemini(pdf_path)

            if uploaded_file:
                try:
                    # Process with uploaded file
                    response = self.model.generate_content(
                        [uploaded_file, processing_prompt],
                        generation_config=self.generation_config
                    )

                    response_text = response.text

                    # Clean up uploaded file
                    try:
                        genai.delete_file(uploaded_file.name)
                    except:
                        pass  # Ignore cleanup errors

                    # Try to parse JSON from response
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
        """
        Fallback method: Extract text first, then process with Gemini

        Args:
            pdf_path (str): Path to the PDF file
            processing_prompt (str): Processing prompt

        Returns:
            Dict[str, Any]: Processed data from Gemini
        """
        print(f"Using text extraction fallback for {pdf_path}")

        # Extract text from PDF
        pdf_text = self.extract_text_from_pdf(pdf_path)

        if not pdf_text:
            return {"error": "Could not extract text from PDF", "file": pdf_path}

        # Truncate text if too long (Gemini has token limits)
        max_chars = 100000  # Approximately 25k tokens
        if len(pdf_text) > max_chars:
            pdf_text = pdf_text[:max_chars] + "\n\n[TEXT TRUNCATED DUE TO LENGTH]"
            print(f"Warning: Text truncated for {pdf_path} due to length")

        # Process with Gemini
        try:
            full_prompt = f"{processing_prompt}\n\nDocument text:\n{pdf_text}"

            response = self.model.generate_content(
                full_prompt,
                generation_config=self.generation_config
            )

            response_text = response.text

            # Try to parse JSON from response
            return self.parse_json_response(response_text, "text_extraction")

        except Exception as e:
            print(f"Error processing text with Gemini: {e}")
            return {"error": str(e), "file": pdf_path}

    def parse_json_response(self, response_text: str, method: str) -> Dict[str, Any]:
        """
        Parse JSON from Gemini response

        Args:
            response_text (str): Response from Gemini
            method (str): Processing method used

        Returns:
            Dict[str, Any]: Parsed JSON or error response
        """
        try:
            # Remove any markdown formatting
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]

            # Find JSON content
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}') + 1

            if start_idx != -1 and end_idx != -1:
                json_str = cleaned_text[start_idx:end_idx]
                parsed_json = json.loads(json_str)
                parsed_json["processing_method"] = method
                return parsed_json
            else:
                return {
                    "raw_response": response_text,
                    "processing_method": method,
                    "note": "No JSON structure found in response"
                }

        except json.JSONDecodeError as e:
            return {
                "raw_response": response_text,
                "processing_method": method,
                "json_error": str(e),
                "note": "Could not parse JSON from response"
            }

    def process_directory(self,
                         pdf_directory: str,
                         output_directory: str,
                         custom_prompt: str = None,
                         delay_seconds: float = 2.0) -> Dict[str, Any]:
        """
        Process all PDFs in a directory

        Args:
            pdf_directory (str): Directory containing PDF files
            output_directory (str): Directory to save JSON files
            custom_prompt (str): Custom processing prompt
            delay_seconds (float): Delay between API calls

        Returns:
            Dict[str, Any]: Processing results summary
        """

        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)

        # Find all PDF files
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
            print(f"\nProcessing {i}/{len(pdf_files)}: {pdf_path.name}")

            try:
                # Process PDF with Gemini
                processed_data = self.process_pdf_with_gemini(str(pdf_path), custom_prompt)

                # Create output filename
                output_filename = f"{pdf_path.stem}.json"
                output_path = os.path.join(output_directory, output_filename)

                # Add metadata
                processed_data["source_file"] = pdf_path.name
                processed_data["processed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                processed_data["file_size_bytes"] = pdf_path.stat().st_size

                # Save JSON file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(processed_data, f, indent=2, ensure_ascii=False)

                print(f"✓ Saved: {output_filename}")
                results["processed_successfully"] += 1
                results["results"].append({
                    "file": pdf_path.name,
                    "status": "success",
                    "output": output_filename,
                    "processing_method": processed_data.get("processing_method", "unknown")
                })

            except Exception as e:
                print(f"✗ Failed: {pdf_path.name} - {e}")
                results["failed"] += 1
                results["results"].append({
                    "file": pdf_path.name,
                    "status": "failed",
                    "error": str(e)
                })

            # Delay between requests to respect API limits
            if i < len(pdf_files):
                print(f"Waiting {delay_seconds} seconds before next request...")
                time.sleep(delay_seconds)

        # Save processing summary
        results["processing_completed"] = time.strftime("%Y-%m-%d %H:%M:%S")
        summary_path = os.path.join(output_directory, "processing_summary.json")
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)

        print(f"\n{'='*50}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*50}")
        print(f"Total files: {results['total_files']}")
        print(f"Successfully processed: {results['processed_successfully']}")
        print(f"Failed: {results['failed']}")
        print(f"Results saved to: {output_directory}")
        print(f"Summary saved to: {summary_path}")

        return results

def create_env_template():
    """
    Create a template .env file
    """
    template_content = """# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# You can get your API key from:
# https://makersuite.google.com/app/apikey
"""

    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(template_content)
        print("Created .env template file. Please add your GEMINI_API_KEY.")
        return False
    return True

def main():
    """
    Main function to run the PDF processor
    """

    # Check for .env file and create template if needed
    if not create_env_template():
        return

    # Load environment variables
    load_dotenv()

    # Check if API key is available
    if not os.getenv('GEMINI_API_KEY'):
        print("Error: GEMINI_API_KEY not found in .env file")
        print("Please add your Gemini API key to the .env file")
        print("You can get an API key from: https://makersuite.google.com/app/apikey")
        return

    # Get directories
    pdf_dir = input("Enter PDF directory path (default: './pdfs'): ").strip()
    if not pdf_dir:
        pdf_dir = "./pdfs"

    if not os.path.exists(pdf_dir):
        print(f"Error: Directory '{pdf_dir}' does not exist")
        return

    output_dir = input("Enter output directory path (default: './json_output'): ").strip()
    if not output_dir:
        output_dir = "./json_output"

    # Custom prompt (optional)
    use_custom_prompt = input("Do you want to use a custom processing prompt? (y/n): ").strip().lower()
    custom_prompt = None

    if use_custom_prompt in ['y', 'yes']:
        print("Enter your custom prompt (press Enter twice to finish):")
        prompt_lines = []
        empty_lines = 0
        while empty_lines < 2:
            line = input()
            if line == "":
                empty_lines += 1
            else:
                empty_lines = 0
            prompt_lines.append(line)
        custom_prompt = "\n".join(prompt_lines[:-2])  # Remove the last two empty lines

    # Delay setting
    delay = input("Enter delay between requests in seconds (default: 2): ").strip()
    try:
        delay_seconds = float(delay) if delay else 2.0
    except ValueError:
        delay_seconds = 2.0

    # Initialize processor and run
    try:
        print("Initializing Gemini PDF Processor...")
        processor = GeminiPDFProcessor()

        print(f"Starting batch processing...")
        print(f"Input directory: {pdf_dir}")
        print(f"Output directory: {output_dir}")
        print(f"Delay between requests: {delay_seconds} seconds")

        results = processor.process_directory(
            pdf_directory=pdf_dir,
            output_directory=output_dir,
            custom_prompt=custom_prompt,
            delay_seconds=delay_seconds
        )

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
