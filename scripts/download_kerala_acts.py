import os
import requests
from bs4 import BeautifulSoup
import time
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuration
BASE_URL = "https://lawmdls.keltron.in/fromserver/lawmodules/archives/act/"
DATA_URL = f"{BASE_URL}get_act_details.php"
FOLDER_NAME = "kerala_acts"
TOTAL_TO_DOWNLOAD = 3000 
CHUNK_SIZE = 100 

# Create folder
if not os.path.exists(FOLDER_NAME):
    os.makedirs(FOLDER_NAME)

# Path for the error log
ERROR_LOG_PATH = os.path.join(FOLDER_NAME, "failed_downloads.txt")

def log_error(sl_no, title, reason):
    """Writes failed downloads to a text file."""
    with open(ERROR_LOG_PATH, "a") as f:
        f.write(f"SL NO: {sl_no} | Title: {title} | Error: {reason}\n")

def download_file(url, filename, sl_no, title):
    filepath = os.path.join(FOLDER_NAME, filename)
    
    if os.path.exists(filepath):
        return "skipped"

    try:
        response = requests.get(url, stream=True, timeout=15, verify=False)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return "downloaded"
        else:
            reason = f"Server returned status code {response.status_code}"
            log_error(sl_no, title, reason)
            return "failed"
    except Exception as e:
        log_error(sl_no, title, str(e))
        return "failed"

def scrape_acts():
    downloaded_this_session = 0
    failed_count = 0
    start_index = 0
    
    # Clear the error log at the start of a new full run if you want, 
    # or keep 'a' to append. Here we append to keep history.
    print(f"Checking for acts... Any errors will be saved to {ERROR_LOG_PATH}")

    while start_index < TOTAL_TO_DOWNLOAD:
        payload = {
            "draw": "1",
            "start": str(start_index),
            "length": str(CHUNK_SIZE),
            "txtactno": "", "year": "0", "cboyecond": "1", "toyear": "0",
            "txtacttitle": "", "cbotitlecond": "Any where",
            "cbostatecentral": "1", "doctype": "1"
        }

        try:
            response = requests.post(DATA_URL, data=payload, timeout=20, verify=False)
            data = response.json()
            records = data.get('data', [])
            
            if not records:
                break

            for record in records:
                sl_no = record[0]
                act_title = record[2].replace("/", "-").replace(":", "-")[:100].strip()
                view_html = record[6]
                
                soup = BeautifulSoup(view_html, 'html.parser')
                link_tag = soup.find('a')
                
                if link_tag and 'href' in link_tag.attrs:
                    relative_href = link_tag['href']
                    # Handle malformed links (some might not have .pdf)
                    full_pdf_url = BASE_URL + relative_href
                    filename = f"{sl_no}_{act_title}.pdf"
                    
                    status = download_file(full_pdf_url, filename, sl_no, act_title)
                    
                    if status == "downloaded":
                        print(f"✓ Downloaded: {sl_no}")
                        downloaded_this_session += 1
                    elif status == "failed":
                        print(f"✗ FAILED: {sl_no} (Logged)")
                        failed_count += 1
                else:
                    log_error(sl_no, act_title, "No download link found in 'View' column")
                    failed_count += 1
            
            start_index += CHUNK_SIZE
            time.sleep(1) # Be kind to the Keltron server
            
        except Exception as e:
            print(f"Critical Request Error: {e}")
            break

    print(f"\n--- Process Finished ---")
    print(f"New downloads: {downloaded_this_session}")
    print(f"Errors logged: {failed_count}")
    print(f"Check '{ERROR_LOG_PATH}' for the list of failures.")

if __name__ == "__main__":
    scrape_acts()
