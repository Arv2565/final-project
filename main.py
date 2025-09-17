# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin, urlparse, parse_qs, urlunparse
# import os
# import time
# import re
# from typing import List, Set
# from collections import deque

# class PDFExtractor:
#     def __init__(self, max_pages=10, delay_seconds=2):
#         """
#         Initialize PDF Extractor with pagination support

#         Args:
#             max_pages (int): Maximum number of pages to crawl
#             delay_seconds (int): Delay between page requests
#         """
#         self.max_pages = max_pages
#         self.delay_seconds = delay_seconds
#         self.visited_urls = set()
#         self.pdf_links = set()
#         self.session = requests.Session()

#         # Headers to appear more like a real browser
#         self.headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
#             'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
#             'Accept-Language': 'en-US,en;q=0.5',
#             'Accept-Encoding': 'gzip, deflate',
#             'Connection': 'keep-alive',
#             'Upgrade-Insecure-Requests': '1',
#         }
#         self.session.headers.update(self.headers)

#     def extract_pdf_links_from_page(self, url: str) -> List[str]:
#         """
#         Extract PDF links from a single page

#         Args:
#             url (str): URL to extract PDFs from

#         Returns:
#             List[str]: List of PDF URLs found on the page
#         """
#         page_pdf_links = []

#         try:
#             print(f"Scanning page: {url}")
#             response = self.session.get(url, timeout=15)
#             response.raise_for_status()

#             soup = BeautifulSoup(response.content, 'html.parser')

#             # Method 1: Direct PDF links in href attributes
#             links = soup.find_all('a', href=True)
#             for link in links:
#                 href = link['href']
#                 absolute_url = urljoin(url, href)

#                 # Check if link points to a PDF
#                 if self.is_pdf_link(href):
#                     if absolute_url not in self.pdf_links:
#                         page_pdf_links.append(absolute_url)
#                         self.pdf_links.add(absolute_url)
#                         print(f"  📄 Found PDF: {absolute_url}")

#             # Method 2: PDF links in JavaScript/onclick attributes
#             for element in soup.find_all(attrs={"onclick": True}):
#                 onclick = element.get('onclick', '')
#                 if '.pdf' in onclick.lower():
#                     urls = re.findall(r"['\"]([^'\"]*\.pdf[^'\"]*)['\"]", onclick, re.IGNORECASE)
#                     for pdf_url in urls:
#                         absolute_url = urljoin(url, pdf_url)
#                         if absolute_url not in self.pdf_links:
#                             page_pdf_links.append(absolute_url)
#                             self.pdf_links.add(absolute_url)
#                             print(f"  📄 Found PDF in onclick: {absolute_url}")

#             # Method 3: Look for PDFs in data attributes and embedded scripts
#             scripts = soup.find_all('script')
#             for script in scripts:
#                 if script.string:
#                     pdf_urls = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', script.string, re.IGNORECASE)
#                     for pdf_url in pdf_urls:
#                         if '/' in pdf_url:  # Likely a URL path
#                             absolute_url = urljoin(url, pdf_url)
#                             if absolute_url not in self.pdf_links:
#                                 page_pdf_links.append(absolute_url)
#                                 self.pdf_links.add(absolute_url)
#                                 print(f"  📄 Found PDF in script: {absolute_url}")

#             print(f"  ✓ Found {len(page_pdf_links)} PDFs on this page")
#             return page_pdf_links

#         except requests.RequestException as e:
#             print(f"  ✗ Error fetching page {url}: {e}")
#             return []
#         except Exception as e:
#             print(f"  ✗ Error processing page {url}: {e}")
#             return []

#     def find_pagination_links(self, url: str, soup: BeautifulSoup) -> List[str]:
#         """
#         Find pagination links on the current page

#         Args:
#             url (str): Current page URL
#             soup (BeautifulSoup): Parsed HTML of the page

#         Returns:
#             List[str]: List of pagination URLs
#         """
#         pagination_links = []

#         # Common pagination patterns
#         pagination_selectors = [
#             'a[href*="page"]',
#             'a[href*="p="]',
#             'a[href*="offset"]',
#             'a[href*="start"]',
#             '.pagination a',
#             '.pager a',
#             '.page-numbers a',
#             'a[rel="next"]',
#             'a:contains("Next")',
#             'a:contains(">")',
#             'a:contains("→")',
#             'a[href*="next"]'
#         ]

#         for selector in pagination_selectors:
#             try:
#                 elements = soup.select(selector)
#                 for element in elements:
#                     href = element.get('href')
#                     if href:
#                         absolute_url = urljoin(url, href)
#                         if absolute_url not in self.visited_urls and absolute_url not in pagination_links:
#                             pagination_links.append(absolute_url)
#             except:
#                 continue

#         # Look for numbered pagination (1, 2, 3, etc.)
#         page_links = soup.find_all('a', href=True)
#         for link in page_links:
#             href = link['href']
#             text = link.get_text(strip=True)

#             # Check if link text is a number (pagination)
#             if text.isdigit() and int(text) > 1:
#                 absolute_url = urljoin(url, href)
#                 if absolute_url not in self.visited_urls and absolute_url not in pagination_links:
#                     pagination_links.append(absolute_url)

#         return pagination_links

#     def generate_pagination_urls(self, base_url: str) -> List[str]:
#         """
#         Generate potential pagination URLs based on common patterns

#         Args:
#             base_url (str): Base URL to generate pagination from

#         Returns:
#             List[str]: List of potential pagination URLs
#         """
#         generated_urls = []
#         parsed_url = urlparse(base_url)

#         # Pattern 1: ?page=N
#         for page_num in range(2, min(self.max_pages + 1, 6)):  # Try pages 2-5
#             new_query = f"page={page_num}"
#             if parsed_url.query:
#                 new_query = f"{parsed_url.query}&{new_query}"

#             new_url = urlunparse((
#                 parsed_url.scheme, parsed_url.netloc, parsed_url.path,
#                 parsed_url.params, new_query, parsed_url.fragment
#             ))
#             generated_urls.append(new_url)

#         # Pattern 2: /page/N
#         if not parsed_url.path.endswith('/'):
#             base_path = parsed_url.path + '/'
#         else:
#             base_path = parsed_url.path

#         for page_num in range(2, min(self.max_pages + 1, 6)):
#             new_path = f"{base_path}page/{page_num}"
#             new_url = urlunparse((
#                 parsed_url.scheme, parsed_url.netloc, new_path,
#                 parsed_url.params, parsed_url.query, parsed_url.fragment
#             ))
#             generated_urls.append(new_url)

#         return generated_urls

#     def is_pdf_link(self, href: str) -> bool:
#         """
#         Check if a link points to a PDF

#         Args:
#             href (str): The href attribute value

#         Returns:
#             bool: True if link points to PDF
#         """
#         href_lower = href.lower()
#         return (href_lower.endswith('.pdf') or
#                 'pdf' in href_lower or
#                 'filetype=pdf' in href_lower or
#                 'format=pdf' in href_lower)

#     def extract_pdf_links_with_pagination(self, start_url: str, download=False, output_dir="pdfs") -> List[str]:
#         """
#         Extract PDF links from a website with pagination support

#         Args:
#             start_url (str): Starting URL to crawl
#             download (bool): Whether to download PDFs
#             output_dir (str): Directory to save PDFs

#         Returns:
#             List[str]: List of all PDF URLs found
#         """
#         print(f"🔍 Starting PDF extraction from: {start_url}")
#         print(f"📄 Max pages to crawl: {self.max_pages}")
#         print(f"⏱️  Delay between requests: {self.delay_seconds} seconds")
#         print("-" * 60)

#         # Queue for URLs to visit
#         urls_to_visit = deque([start_url])
#         pages_crawled = 0

#         while urls_to_visit and pages_crawled < self.max_pages:
#             current_url = urls_to_visit.popleft()

#             if current_url in self.visited_urls:
#                 continue

#             self.visited_urls.add(current_url)
#             pages_crawled += 1

#             print(f"\n📖 Page {pages_crawled}/{self.max_pages}")

#             # Extract PDFs from current page
#             page_pdfs = self.extract_pdf_links_from_page(current_url)

#             # If no PDFs found, look for pagination links
#             if not page_pdfs or pages_crawled < self.max_pages:
#                 try:
#                     response = self.session.get(current_url, timeout=15)
#                     soup = BeautifulSoup(response.content, 'html.parser')

#                     # Find pagination links
#                     pagination_links = self.find_pagination_links(current_url, soup)

#                     # If no pagination links found, try generating common patterns
#                     if not pagination_links and pages_crawled == 1:
#                         pagination_links = self.generate_pagination_urls(current_url)
#                         print(f"  🔗 Generated {len(pagination_links)} potential pagination URLs")

#                     # Add pagination links to queue
#                     for link in pagination_links[:3]:  # Limit to avoid infinite loops
#                         if link not in self.visited_urls:
#                             urls_to_visit.append(link)
#                             print(f"  🔗 Added to queue: {link}")

#                 except Exception as e:
#                     print(f"  ✗ Error finding pagination links: {e}")

#             # Delay between requests
#             if urls_to_visit and pages_crawled < self.max_pages:
#                 print(f"  ⏱️  Waiting {self.delay_seconds} seconds...")
#                 time.sleep(self.delay_seconds)

#         all_pdf_links = list(self.pdf_links)

#         print(f"\n{'='*60}")
#         print(f"🏁 EXTRACTION COMPLETE")
#         print(f"{'='*60}")
#         print(f"📖 Pages crawled: {pages_crawled}")
#         print(f"📄 Total PDFs found: {len(all_pdf_links)}")

#         if all_pdf_links:
#             print(f"\n📋 PDF LINKS FOUND:")
#             for i, link in enumerate(all_pdf_links, 1):
#                 print(f"{i:2d}. {link}")

#             if download:
#                 print(f"\n⬇️  Starting download...")
#                 self.download_pdfs(all_pdf_links, output_dir)
#         else:
#             print("\n❌ No PDF links found across all pages.")

#         return all_pdf_links

#     def download_pdfs(self, pdf_links: List[str], output_dir: str = "pdfs"):
#         """
#         Download PDFs from a list of URLs

#         Args:
#             pdf_links (List[str]): List of PDF URLs to download
#             output_dir (str): Directory to save the PDFs
#         """
#         if not os.path.exists(output_dir):
#             os.makedirs(output_dir)
#             print(f"📁 Created directory: {output_dir}")

#         successful_downloads = 0
#         failed_downloads = 0

#         for i, pdf_url in enumerate(pdf_links, 1):
#             try:
#                 print(f"\n⬇️  Downloading {i}/{len(pdf_links)}: {pdf_url}")

#                 # Get filename from URL
#                 parsed_url = urlparse(pdf_url)
#                 filename = os.path.basename(parsed_url.path)

#                 # Clean filename
#                 if not filename or not filename.lower().endswith('.pdf'):
#                     filename = f"document_{i}.pdf"

#                 # Sanitize filename
#                 filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
#                 filepath = os.path.join(output_dir, filename)

#                 # Download with streaming
#                 response = self.session.get(pdf_url, stream=True, timeout=30)
#                 response.raise_for_status()

#                 # Check if response is actually a PDF
#                 content_type = response.headers.get('content-type', '').lower()
#                 if 'pdf' not in content_type and not pdf_url.lower().endswith('.pdf'):
#                     print(f"  ⚠️  Warning: Content type is {content_type}, may not be a PDF")

#                 # Save the file
#                 with open(filepath, 'wb') as f:
#                     for chunk in response.iter_content(chunk_size=8192):
#                         if chunk:
#                             f.write(chunk)

#                 file_size = os.path.getsize(filepath)
#                 print(f"  ✅ Downloaded: {filename} ({file_size:,} bytes)")
#                 successful_downloads += 1

#                 # Small delay between downloads
#                 time.sleep(1)

#             except Exception as e:
#                 print(f"  ❌ Failed to download {pdf_url}: {e}")
#                 failed_downloads += 1

#         print(f"\n📊 DOWNLOAD SUMMARY:")
#         print(f"✅ Successful: {successful_downloads}")
#         print(f"❌ Failed: {failed_downloads}")
#         print(f"📁 Saved to: {output_dir}")

# def main():
#     """
#     Main function to run the enhanced PDF extractor
#     """
#     print("🔍 Enhanced PDF Extractor with Pagination Support")
#     print("=" * 60)

#     # Get user input
#     website_url = input("🌐 Enter the website URL: ").strip()
#     if not website_url:
#         print("❌ No URL provided.")
#         return

#     # Add protocol if missing
#     if not website_url.startswith(('http://', 'https://')):
#         website_url = 'https://' + website_url

#     # Get max pages
#     max_pages_input = input("📖 Maximum pages to crawl (default: 5): ").strip()
#     try:
#         max_pages = int(max_pages_input) if max_pages_input else 5
#         max_pages = max(1, min(max_pages, 20))  # Limit between 1-20
#     except ValueError:
#         max_pages = 5

#     # Get delay
#     delay_input = input("⏱️  Delay between requests in seconds (default: 2): ").strip()
#     try:
#         delay_seconds = float(delay_input) if delay_input else 2.0
#         delay_seconds = max(1.0, delay_seconds)  # Minimum 1 second
#     except ValueError:
#         delay_seconds = 2.0

#     # Ask about downloading
#     download_choice = input("⬇️  Do you want to download the PDFs? (y/n): ").strip().lower()
#     download = download_choice in ['y', 'yes']

#     output_directory = "pdfs"
#     if download:
#         output_input = input("📁 Enter output directory (default: 'pdfs'): ").strip()
#         if output_input:
#             output_directory = output_input

#     # Initialize extractor and run
#     try:
#         extractor = PDFExtractor(max_pages=max_pages, delay_seconds=delay_seconds)
#         pdf_links = extractor.extract_pdf_links_with_pagination(
#             start_url=website_url,
#             download=download,
#             output_dir=output_directory
#         )

#         if not pdf_links:
#             print("\n💡 SUGGESTIONS:")
#             print("   • Try increasing the number of pages to crawl")
#             print("   • Check if the website has a sitemap or search function")
#             print("   • Look for direct links to document sections")
#             print("   • Some sites may require JavaScript or authentication")

#     except KeyboardInterrupt:
#         print("\n\n⏹️  Process interrupted by user.")
#     except Exception as e:
#         print(f"\n❌ Error: {e}")

# if __name__ == "__main__":
#     main()

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
