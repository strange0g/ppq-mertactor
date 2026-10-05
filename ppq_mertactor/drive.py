import os
import requests
import re

def fetch_document(file_id: str, expected_filename: str) -> str:
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

    with open(cached_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return cached_path

def get_folder_metadata(folder_id: str) -> dict[str, str]:
    """
    Scrapes the public Google Drive folder page to extract file IDs and their names.
    Returns a dictionary mapping filenames to their Google Drive file IDs.
    """
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    response = requests.get(url)
    response.raise_for_status()

    # We will use a regular expression to extract the ID and Name pairs.
    # From the mock HTML: ["mock_qp_id", "9609_s23_qp_11.pdf"]
    # In actual Drive HTML, the structure might be more complex, but we search for
    # sequences that resemble `["<id>","<filename>"]`.
    # For a tracer bullet, a simple regex is sufficient, though it might need
    # refinement for real Drive HTML structure. Let's make it robust enough for the mock.

    # regex pattern to match ["id", "name"]
    pattern = r'\["([^"]+)",\s*"([^"]+\.pdf)"\]'
    matches = re.findall(pattern, response.text)

    metadata = {}
    for file_id, filename in matches:
        metadata[filename] = file_id

    return metadata
