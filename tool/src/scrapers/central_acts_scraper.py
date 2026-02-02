import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote

# Directory to save PDFs - create in data/knowledge_base/central_acts/
DOWNLOAD_DIR = os.path.join("data", "knowledge_base", "central_acts")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"Created directory: {DOWNLOAD_DIR}")

# A stable base URL for starting the scrape.
# The server will add the necessary temporary tokens when we access it via a session.
START_URL = "https://www.indiacode.nic.in/handle/123456789/1362/browse?type=shorttitle&sort_by=1&order=ASC&rpp=100"
BASE_URL = "https://www.indiacode.nic.in"

# Create a session object to persist cookies and headers
session = requests.Session()

# Update the session with headers to mimic a real browser
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
})

def download_pdf(pdf_url, folder):
    """Downloads a PDF from a given URL using our session."""
    try:
        pdf_name = unquote(os.path.basename(pdf_url))
        print(f"    -> Attempting to download: {pdf_name}")
        
        response = session.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        file_path = os.path.join(folder, pdf_name)
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"    ✅ Successfully downloaded {pdf_name}")
    except requests.exceptions.RequestException as e:
        print(f"    ❌ Error downloading {pdf_url}: {e}")

def scrape_website():
    """Scrapes the website using a session to handle tokens and headers."""
    # Start with page showing 100 items per page to get more items per request
    current_page_url = START_URL.replace("rpp=100", "rpp=100")  # Already 100, but making it explicit
    page_count = 1
    total_pdfs_downloaded = 0
    
    while current_page_url:
        print(f"\n--- Scraping Page {page_count}: {current_page_url} ---")
        try:
            response = session.get(current_page_url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Check if we can find the total items count
            panel_heading = soup.find("div", class_="panel-heading1")
            if panel_heading and page_count == 1:
                heading_text = panel_heading.get_text()
                print(f"Found page info: {heading_text.strip()}")

            table = soup.find("table", class_="panel")
            if not table:
                print("Could not find the main data table. The website structure may have changed.")
                break

            # Find all links inside the fourth column (td) of each data row (tr)
            rows = table.select("tr:has(td)") # Selects only rows with data cells
            if not rows:
                print("No data rows found on this page.")
                break

            page_pdfs = 0
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    view_link_tag = cells[3].find("a", href=True)
                    if view_link_tag:
                        inner_page_url = urljoin(BASE_URL, view_link_tag["href"])
                        print(f"  > Visiting: {inner_page_url}")

                        try:
                            inner_response = session.get(inner_page_url, timeout=30)
                            inner_response.raise_for_status()
                            inner_soup = BeautifulSoup(inner_response.content, "html.parser")

                            # Find PDF links - look for links containing .pdf
                            pdf_link_tags = inner_soup.find_all("a", href=lambda href: href and ".pdf" in href.lower())
                            
                            if pdf_link_tags:
                                # Download the first PDF found (usually the English version)
                                pdf_link_tag = pdf_link_tags[0]
                                pdf_url = urljoin(BASE_URL, pdf_link_tag['href'])
                                download_pdf(pdf_url, DOWNLOAD_DIR)
                                page_pdfs += 1
                                total_pdfs_downloaded += 1
                            else:
                                print(f"    - No PDF link found on page.")
                        
                        except requests.exceptions.RequestException as e:
                            print(f"  - Error accessing inner page {inner_page_url}: {e}")
                        
                        # Small delay to be respectful
                        import time
                        time.sleep(0.5)
            
            print(f"  Downloaded {page_pdfs} PDFs from this page (Total so far: {total_pdfs_downloaded})")

            # Look for next page link - try multiple selectors
            next_page_tag = None
            
            # Method 1: Look for Next Page link by title
            next_page_tag = soup.find("a", href=True, title="Next Page")
            
            # Method 2: Look for next page image
            if not next_page_tag:
                next_page_imgs = soup.find_all("img", src=lambda src: src and "nextPage" in src)
                if next_page_imgs:
                    next_page_tag = next_page_imgs[0].find_parent("a")
            
            # Method 3: Look for pagination links with offset parameter
            if not next_page_tag:
                pagination_links = soup.find_all("a", href=lambda href: href and "offset=" in href)
                if pagination_links:
                    # Find the link with the next offset
                    current_offset = 0
                    if "offset=" in current_page_url:
                        current_offset = int(current_page_url.split("offset=")[1].split("&")[0] if "&" in current_page_url.split("offset=")[1] else current_page_url.split("offset=")[1])
                    
                    for link in pagination_links:
                        href = link['href']
                        if "offset=" in href:
                            link_offset = int(href.split("offset=")[1].split("&")[0] if "&" in href.split("offset=")[1] else href.split("offset=")[1])
                            if link_offset > current_offset:
                                next_page_tag = link
                                break
            
            if next_page_tag and next_page_tag.get('href'):
                current_page_url = urljoin(BASE_URL, next_page_tag["href"])
                page_count += 1
                print(f"  → Found next page: {current_page_url}")
                
                # Add delay between pages
                import time
                time.sleep(1)
            else:
                current_page_url = None
                print("\n--- No 'Next Page' link found. Scraping complete. ---")

        except requests.exceptions.RequestException as e:
            print(f"❌ Critical error accessing page {current_page_url}: {e}")
            break
    
    print(f"\n🎉 SCRAPING COMPLETED")
    print(f"📊 Total pages processed: {page_count}")
    print(f"📄 Total PDFs downloaded: {total_pdfs_downloaded}")
    print(f"📁 Files saved to: {DOWNLOAD_DIR}")

if __name__ == "__main__":
    scrape_website()