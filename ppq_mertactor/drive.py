import os
import requests
import re
import json

from typing import Callable, Optional

def fetch_document(file_id: str, expected_filename: str, progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
    """
    Fetches a document from Google Drive using the public download link,
    or returns the cached version if it exists.
    """
    cache_dir = os.environ.get("DRIVE_CACHE_DIR", os.path.join(".cache", "drive_cache"))
    os.makedirs(cache_dir, exist_ok=True)

    cached_path = os.path.join(cache_dir, expected_filename)
    if os.path.exists(cached_path):
        return cached_path

    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    response = requests.get(url, stream=True)
    response.raise_for_status()

    total_bytes = int(response.headers.get("Content-Length", 0))

    with open(cached_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
                if progress_callback:
                    progress_callback(len(chunk), total_bytes)

    return cached_path

def get_folder_metadata(folder_id: str) -> dict[str, str]:
    """
    Scrapes the public Google Drive folder page to extract file IDs and their names.
    Returns a dictionary mapping filenames/foldernames to their Google Drive IDs.
    """
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    response = requests.get(url)
    response.raise_for_status()

    # We will use a regular expression to extract the ID and Name pairs.
    # From the mock HTML: ["mock_qp_id", "9609_s23_qp_11.pdf"]
    # Also support extracting folder names (no .pdf extension).

    # regex pattern to match ["id", "name"]
    pattern = r'\["([^"]+)",\s*"([^"]+)"\]'
    matches = re.findall(pattern, response.text)

    metadata = {}
    for item_id, item_name in matches:
        metadata[item_name] = item_id

    return metadata

def _extract_folder_id(folder_id_or_url: str) -> str:
    """Extract folder ID from URL or return as is."""
    match = re.search(r'folders/([a-zA-Z0-9_-]+)', folder_id_or_url)
    if match:
        return match.group(1)
    return folder_id_or_url

def crawl_tree(root_folder_id_or_url: str) -> dict:
    """
    Recursively discovers child folders partitioned by year and examination series,
    along with their PDF files, directly from public Google Drive HTML responses.
    Caches the results locally to avoid duplicate network calls.
    Returns nested dictionary: Year -> Series -> Files.
    """
    root_id = _extract_folder_id(root_folder_id_or_url)

    cache_dir = os.environ.get("DRIVE_CACHE_DIR", os.path.join(".cache", "drive_cache"))
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"crawl_{root_id}.json")

    if os.path.exists(cache_path):
        with open(cache_path, "r") as f:
            return json.load(f)

    tree = {}

    # 1. Fetch root folder containing years (2016-2025)
    root_metadata = get_folder_metadata(root_id)

    for item_name, item_id in root_metadata.items():
        # Match years between 2016 and 2025
        if re.match(r'^20(1[6-9]|2[0-5])$', item_name):
            year = item_name
            tree[year] = {}

            # 2. Fetch series folder (m, s, w, y)
            series_metadata = get_folder_metadata(item_id)
            for series_name, series_id in series_metadata.items():
                if series_name in ('m', 's', 'w', 'y'):
                    series = series_name
                    tree[year][series] = {}

                    # 3. Fetch files inside series folder
                    files_metadata = get_folder_metadata(series_id)
                    for file_name, file_id in files_metadata.items():
                        if file_name.endswith('.pdf'):
                            tree[year][series][file_name] = file_id

    # Ensure there are no empty years or series if needed (optional)
    # Cache the result
    with open(cache_path, "w") as f:
        json.dump(tree, f, indent=4)

    return tree

# Update get_folder_metadata to handle non-PDF folders as well
