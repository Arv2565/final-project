import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, unquote

# Directory to save PDFs
DOWNLOAD_DIR = "centtral_acts"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

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
    current_page_url = START_URL
    page_count = 1
    
    while current_page_url:
        print(f"\n--- Scraping Page {page_count}: {current_page_url} ---")
        try:
            response = session.get(current_page_url, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            table = soup.find("table", class_="panel")
            if not table:
                print("Could not find the main data table. The website structure may have changed.")
                break

            # Find all links inside the fourth column (td) of each data row (tr)
            rows = table.select("tr:has(td)") # Selects only rows with data cells
            if not rows:
                print("No data rows found on this page.")

            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    view_link_tag = cells[3].find("a", href=True)
                    if view_link_tag:
                        inner_page_url = urljoin(BASE_URL, view_link_tag["href"])
                        print(f"  > Visiting: {inner_page_url}")

                        try:
                            inner_response = session.get(inner_page_url, timeout=20)
                            inner_response.raise_for_status()
                            inner_soup = BeautifulSoup(inner_response.content, "html.parser")

                            # Find the first link whose href ends with ".pdf"
                            pdf_link_tag = inner_soup.find("a", href=lambda href: href and ".pdf" in href)
                            if pdf_link_tag:
                                pdf_url = urljoin(BASE_URL, pdf_link_tag['href'])
                                download_pdf(pdf_url, DOWNLOAD_DIR)
                            else:
                                print(f"    - No PDF link found on page.")
                        
                        except requests.exceptions.RequestException as e:
                            print(f"  - Error accessing inner page {inner_page_url}: {e}")

            # Find the "next page" link, identified by its image content
            next_page_tag = soup.find("a", href=True, title="Next Page")
            if next_page_tag:
                current_page_url = urljoin(BASE_URL, next_page_tag["href"])
                page_count += 1
            else:
                current_page_url = None
                print("\n--- No 'Next Page' link found. Scraping complete. ---")

        except requests.exceptions.RequestException as e:
            print(f"❌ Critical error accessing page {current_page_url}: {e}")
            break

if __name__ == "__main__":
    scrape_website()