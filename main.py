import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
import time

def extract_pdf_links(url, download=False, output_dir="pdfs"):
    """
    Extract all PDF links from a website

    Args:
        url (str): The website URL to scan
        download (bool): Whether to download the PDFs or just list them
        output_dir (str): Directory to save PDFs if downloading

    Returns:
        list: List of PDF URLs found
    """

    try:
        # Send GET request to the website
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        print(f"Fetching webpage: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all links
        links = soup.find_all('a', href=True)

        pdf_links = []

        for link in links:
            href = link['href']

            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(url, href)

            # Check if link points to a PDF
            if href.lower().endswith('.pdf') or 'pdf' in href.lower():
                pdf_links.append(absolute_url)
                print(f"Found PDF: {absolute_url}")

        # Also check for links in JavaScript or other attributes
        # Look for PDF links in onclick, data attributes, etc.
        for element in soup.find_all(attrs={"onclick": True}):
            onclick = element.get('onclick', '')
            if '.pdf' in onclick.lower():
                # Extract URL from onclick (basic extraction)
                import re
                urls = re.findall(r"['\"]([^'\"]*\.pdf[^'\"]*)['\"]", onclick, re.IGNORECASE)
                for pdf_url in urls:
                    absolute_url = urljoin(url, pdf_url)
                    if absolute_url not in pdf_links:
                        pdf_links.append(absolute_url)
                        print(f"Found PDF in onclick: {absolute_url}")

        print(f"\nTotal PDFs found: {len(pdf_links)}")

        if download and pdf_links:
            download_pdfs(pdf_links, output_dir)

        return pdf_links

    except requests.RequestException as e:
        print(f"Error fetching the webpage: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def download_pdfs(pdf_links, output_dir="pdfs"):
    """
    Download PDFs from a list of URLs

    Args:
        pdf_links (list): List of PDF URLs to download
        output_dir (str): Directory to save the PDFs
    """

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for i, pdf_url in enumerate(pdf_links, 1):
        try:
            print(f"Downloading {i}/{len(pdf_links)}: {pdf_url}")

            # Get filename from URL
            parsed_url = urlparse(pdf_url)
            filename = os.path.basename(parsed_url.path)

            # If no filename, create one
            if not filename or not filename.endswith('.pdf'):
                filename = f"document_{i}.pdf"

            filepath = os.path.join(output_dir, filename)

            # Download the PDF
            response = requests.get(pdf_url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()

            # Save the PDF
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"✓ Downloaded: {filename}")

            # Small delay to be respectful to the server
            time.sleep(1)

        except Exception as e:
            print(f"✗ Failed to download {pdf_url}: {e}")

def main():
    """
    Main function to run the PDF extractor
    """

    # Example usage
    website_url = input("Enter the website URL: ").strip()

    if not website_url:
        print("No URL provided. Using example URL.")
        website_url = "https://example.com"

    # Ask user if they want to download PDFs
    download_choice = input("Do you want to download the PDFs? (y/n): ").strip().lower()
    download = download_choice in ['y', 'yes']

    if download:
        output_directory = input("Enter output directory (press Enter for 'pdfs'): ").strip()
        if not output_directory:
            output_directory = "pdfs"
    else:
        output_directory = "pdfs"

    # Extract PDF links
    pdf_links = extract_pdf_links(website_url, download=download, output_dir=output_directory)

    # Display results
    if pdf_links:
        print(f"\n{'='*50}")
        print("PDF LINKS FOUND:")
        print(f"{'='*50}")
        for i, link in enumerate(pdf_links, 1):
            print(f"{i}. {link}")
    else:
        print("\nNo PDF links found on this website.")

if __name__ == "__main__":
    main()
