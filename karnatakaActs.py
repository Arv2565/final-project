import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import re
import time

def sanitize_filename(name):
    """Removes invalid characters from a string to create a valid filename."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = re.sub(r'\s+', '_', name)
    return name[:150] + ".pdf"

def download_file(url, filepath):
    """Downloads a file from a URL and saves it to a specified path."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # Using a session object for potentially better handling of cookies/redirects
        with requests.Session() as s:
            response = s.get(url, headers=headers, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"      ---> ✅ Successfully downloaded to {filepath}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"      ---> ❌ Failed to download {url}. Error: {e}")
        return False

def scrape_latest_laws():
    """
    Scrapes Karnataka law acts. It intelligently finds and downloads direct PDFs
    and Google Drive files, while logging non-downloadable links.
    """
    base_url = "https://www.latestlaws.com"
    listing_url = f"{base_url}/bare-acts/state-acts-rules/karnataka-state-laws/"
    download_dir = "karnataka_law"

    os.makedirs(download_dir, exist_ok=True)
    print(f"📁 PDFs will be saved in the '{download_dir}' directory.")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Fetching main listing page: {listing_url}")
        response = requests.get(listing_url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Fatal Error: Could not fetch the main page. {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    act_list_container = soup.find('ul', id='act_child_list')
    if not act_list_container:
        print("Fatal Error: Could not find the list of acts. Website structure may have changed.")
        return

    act_links = act_list_container.find_all('a')
    print(f"Found {len(act_links)} acts to process.")

    non_downloadable_links = []
    downloaded_files_log = []

    for i, link in enumerate(act_links):
        act_title = link.text.strip()
        act_url = link.get('href')
        if not act_url.startswith('http'):
            act_url = f"{base_url}{act_url}"

        print(f"\n[{i+1}/{len(act_links)}] Processing: {act_title}")

        try:
            act_response = requests.get(act_url, headers=headers, timeout=20)
            act_response.raise_for_status()
            act_soup = BeautifulSoup(act_response.content, 'html.parser')

            found_link = False

            # --- SMART PDF FINDING LOGIC ---

            # 1. Check for Direct PDF Links (ends with .pdf)
            direct_pdf_tag = act_soup.find('a', href=re.compile(r'\.pdf$', re.IGNORECASE))
            if direct_pdf_tag:
                pdf_url = direct_pdf_tag.get('href')
                if not pdf_url.startswith('http'):
                    pdf_url = f"{base_url}{pdf_url}"
                print(f"   --> Found Direct PDF Link: {pdf_url}")
                filename = sanitize_filename(act_title)
                filepath = os.path.join(download_dir, filename)
                if download_file(pdf_url, filepath):
                    downloaded_files_log.append({"Act Title": act_title, "Saved Filename": filename, "Source URL": pdf_url})
                found_link = True

            # 2. If not found, check for Google Drive Links
            if not found_link:
                # Search in both iframes and anchor tags for Google Drive links
                gdrive_tag = act_soup.find(['iframe', 'a'], {'src': re.compile(r'drive\.google\.com')}) or \
                             act_soup.find('a', {'href': re.compile(r'drive\.google\.com')})

                if gdrive_tag:
                    gdrive_url = gdrive_tag.get('src') or gdrive_tag.get('href')
                    # Extract the file ID from the URL
                    match = re.search(r'/d/([a-zA-Z0-9_-]+)', gdrive_url)
                    if match:
                        file_id = match.group(1)
                        # Construct the direct download link
                        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
                        print(f"   --> Found Google Drive Link. Attempting download from: {download_url}")
                        
                        filename = sanitize_filename(act_title)
                        filepath = os.path.join(download_dir, filename)
                        if download_file(download_url, filepath):
                             downloaded_files_log.append({"Act Title": act_title, "Saved Filename": filename, "Source URL": gdrive_url})
                        found_link = True

            # 3. If not found, check for Scribd Links
            if not found_link:
                iframe = act_soup.find('iframe', class_='scribd_iframe_embed')
                if iframe:
                    viewer_url = iframe.get('src')
                    print(f"   --> Found Scribd Viewer. Logging to CSV.")
                    non_downloadable_links.append({"Act Title": act_title, "Page URL": act_url, "Link Type": "Scribd Viewer", "Viewer URL": viewer_url})
                    found_link = True
            
            # 4. If nothing is found
            if not found_link:
                print("   --> No downloadable link or viewer found.")
                non_downloadable_links.append({"Act Title": act_title, "Page URL": act_url, "Link Type": "Not Found", "Viewer URL": "N/A"})
            
            # A small delay to be polite to the server
            time.sleep(1)

        except requests.exceptions.RequestException as e:
            print(f"   --> ❌ Failed to process page {act_url}. Error: {e}")

    # --- Save results to CSV files ---
    if non_downloadable_links:
        df_view = pd.DataFrame(non_downloadable_links)
        view_filename = "karnataka_acts_for_viewing.csv"
        df_view.to_csv(view_filename, index=False, encoding='utf-8')
        print(f"\n📄 Saved {len(non_downloadable_links)} non-downloadable links to '{view_filename}'")
        
    if downloaded_files_log:
        df_log = pd.DataFrame(downloaded_files_log)
        log_filename = "karnataka_acts_downloaded.csv"
        df_log.to_csv(log_filename, index=False, encoding='utf-8')
        print(f"💾 Saved a log of {len(downloaded_files_log)} downloaded files to '{log_filename}'")

    print(f"\n🎉 Scraping complete! {len(downloaded_files_log)} files downloaded.")

if __name__ == "__main__":
    scrape_latest_laws()