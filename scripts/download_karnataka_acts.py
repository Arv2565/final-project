import os
import re
import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
BASE_URL = "https://www.latestlaws.com/bare-acts/state-acts-rules/karnataka-state-laws/"
TARGET_YEAR = 1985
DOWNLOAD_DIR = "/Users/pranav/Documents/Projects/final-project/data/karnataka_acts"
LOG_FILE = os.path.join(DOWNLOAD_DIR, "download_results.txt")

# Create download directory
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

def get_session_with_retries():
    """Create a requests session with retry strategy and proper headers."""
    session = requests.Session()
    
    # Retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers to mimic real browser
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    })
    
    return session

def get_pdf_link_from_page(session, act_url):
    """Visits the specific act page and searches for the PDF download link (Google Drive or direct)."""
    try:
        response = session.get(act_url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pdf_link = None
        
        # 1. First priority: Look for Google Drive links
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link['href']
            text = link.get_text(strip=True).lower()
            
            # Check for Google Drive links (most common for LatestLaws)
            if 'drive.google.com' in href:
                # Convert view link to direct download if needed
                if '/view' in href:
                    # Extract file ID from URL
                    file_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', href)
                    if file_id_match:
                        file_id = file_id_match.group(1)
                        # Use the view URL (works better than export)
                        pdf_link = f"https://drive.google.com/file/d/{file_id}/view"
                        break
                else:
                    pdf_link = href
                    break
        
        # 2. Secondary: Look for direct PDF links
        if not pdf_link:
            for link in all_links:
                href = link['href']
                text = link.get_text(strip=True).lower()
                
                # Check various patterns for direct PDF links
                if href.lower().endswith('.pdf'):
                    pdf_link = urljoin(act_url, href)
                    break
                elif 'download' in text and ('.pdf' in href.lower() or 'pdf' in text):
                    pdf_link = urljoin(act_url, href)
                    break
                elif '.pdf' in href.lower():
                    pdf_link = urljoin(act_url, href)
                    break
        
        # 3. Try finding PDF in buttons or other elements
        if not pdf_link:
            buttons = soup.find_all(['button', 'a'], {'class': lambda x: x and 'download' in x.lower() if x else False}, href=True)
            for btn in buttons:
                href = btn.get('href', '')
                if href and 'drive.google.com' in href:
                    pdf_link = href
                    break
                elif href and '.pdf' in href.lower():
                    pdf_link = urljoin(act_url, href)
                    break
        
        # 4. Try to find any PDF-like URLs in the page (including Google Drive)
        if not pdf_link:
            # Look for Google Drive URLs
            gdrive_pattern = r'https://drive\.google\.com/file/d/[a-zA-Z0-9-_]+/view[^"\s]*'
            gdrive_matches = re.findall(gdrive_pattern, response.text)
            if gdrive_matches:
                pdf_link = gdrive_matches[0]
            else:
                # Fall back to direct PDF pattern
                pdf_pattern = r'(https?://[^\s"\'><]+\.pdf|/[^\s"\'><]*\.pdf)'
                matches = re.findall(pdf_pattern, response.text)
                if matches:
                    pdf_link = urljoin(act_url, matches[0])
        
        return pdf_link
    except Exception as e:
        print(f"   [Error] Could not parse page {act_url}: {e}")
        return None

def download_file(session, url, filename):
    """Downloads the file from the URL. Handles both direct downloads and Google Drive."""
    try:
        # Special handling for Google Drive URLs
        if 'drive.google.com' in url:
            # Extract file ID from Google Drive URL
            file_id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
            if not file_id_match:
                print(f"   [Error] Could not extract file ID from Google Drive URL: {url}")
                return False
            
            file_id = file_id_match.group(1)
            # Use export URL for direct download (works better than /view)
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            response = session.get(download_url, stream=True, timeout=20, allow_redirects=True)
            response.raise_for_status()
        else:
            # Direct download for non-Google Drive URLs
            response = session.get(url, stream=True, timeout=20)
            response.raise_for_status()
        
        filepath = os.path.join(DOWNLOAD_DIR, filename)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return True
    except Exception as e:
        print(f"   [Error] Download failed for {url}: {e}")
        return False

def main():
    session = get_session_with_retries()
    
    print(f"Fetching acts from {BASE_URL}...")
    try:
        response = session.get(BASE_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = soup.find_all('a', href=True)
        results = []

        print("Filtering acts and searching for PDFs...")
        for link in links:
            title = link.get_text(strip=True)
            href = urljoin(BASE_URL, link['href'])
            
            # Use regex to find a 4-digit year at the VERY END of the title
            match = re.search(r'(\d{4})$', title)
            
            if match:
                year = int(match.group(1))
                if year < TARGET_YEAR and "/bare-acts/" in href:
                    print(f"Found: {title} ({year})")
                    
                    # Visit the individual page to find the PDF
                    pdf_url = get_pdf_link_from_page(session, href)
                    
                    status = "FAILED"
                    if pdf_url:
                        # Clean filename: remove special chars, keep year
                        clean_name = re.sub(r'[^\w\s-]', '', title).replace(' ', '_') + ".pdf"
                        if download_file(session, pdf_url, clean_name):
                            status = "SUCCESS"
                            print(f"   [+] Downloaded: {clean_name}")
                        else:
                            status = "FAILED (Download Error)"
                    else:
                        status = "FAILED (No PDF link found)"
                        print(f"   [-] No PDF link found for this act.")
                    
                    results.append(f"Name: {title} | Year: {year} | Status: {status} | Link: {href}")
                    
                    # Small delay to be polite to the server
                    time.sleep(1)

        # Write the text file report
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write(f"DOWNLOAD REPORT - ACTS BEFORE {TARGET_YEAR}\n")
            f.write("="*50 + "\n")
            for line in results:
                f.write(line + "\n")
        
        print(f"\nFinished! Results saved to {LOG_FILE}")
        print(f"PDFs are in the '{DOWNLOAD_DIR}' folder.")

    except Exception as e:
        print(f"A critical error occurred: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

