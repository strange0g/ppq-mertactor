import os
import json
import shutil
import pytest
import responses
from unittest.mock import MagicMock
from ppq_mertactor.drive import fetch_document, get_folder_metadata

# Assume crawl_tree will be added to drive.py
from ppq_mertactor.drive import crawl_tree

@responses.activate
def test_fetch_document_progress_callback():
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    file_id = "test_file_id"
    expected_filename = "test_file.pdf"

    # Mocking response
    url = f"https://drive.google.com/uc?export=download&id={file_id}"

    # responses library stream handling
    responses.add(
        responses.GET,
        url,
        body=b"12345678", # 8 bytes
        headers={"Content-Length": "8"},
        status=200
    )

    callback_mock = MagicMock()

    # Call fetch_document with callback
    fetch_document(file_id, expected_filename, progress_callback=callback_mock)

    # Callback should have been called once with length 8 because chunk_size is 8192
    assert callback_mock.call_count == 1
    callback_mock.assert_any_call(8, 8)

@responses.activate
def test_fetch_document_progress_callback_multiple_chunks():
    from unittest.mock import patch
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    file_id = "test_file_id_chunks"
    expected_filename = "test_file_chunks.pdf"

    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    responses.add(
        responses.GET,
        url,
        body=b"12345678", # 8 bytes
        headers={"Content-Length": "8"},
        status=200
    )

    callback_mock = MagicMock()

    # We patch response.iter_content to force returning small chunks regardless of what responses gives
    with patch('requests.Response.iter_content') as mock_iter:
        mock_iter.return_value = [b"1234", b"5678"]
        fetch_document(file_id, expected_filename, progress_callback=callback_mock)

    assert callback_mock.call_count == 2
    callback_mock.assert_any_call(4, 8)

@responses.activate
def test_fetch_document_cache_hit():
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    file_id = "test_file_id"
    expected_filename = "test_file.pdf"
    cached_path = os.path.join(cache_dir, expected_filename)

    # Create dummy cached file
    with open(cached_path, "wb") as f:
        f.write(b"cached_content")

    # Mocking response to ensure it fails if called (shouldn't be called)
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    responses.add(
        responses.GET,
        url,
        status=500
    )

    # Call fetch_document
    result = fetch_document(file_id, expected_filename)

    # Assert cache is used
    assert result == cached_path
    assert len(responses.calls) == 0

@responses.activate
def test_network_retries():
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    folder_id = "retry_folder_id"
    url = f"https://drive.google.com/drive/folders/{folder_id}"

    # Mock 3 failures then 1 success
    responses.add(responses.GET, url, status=503)
    responses.add(responses.GET, url, status=503)
    responses.add(responses.GET, url, status=503)

    root_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["file_id", "file.pdf"]
    ]});</script>
    """
    responses.add(responses.GET, url, body=root_html, status=200)

    # Call get_folder_metadata
    metadata = get_folder_metadata(folder_id)

    # Assert retry was successful and 4 calls were made
    assert metadata == {"file.pdf": "file_id"}
    assert len(responses.calls) == 4

@responses.activate
def test_crawl_tree():
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    root_id = "root_folder_id"

    # Root folder response (contains years)
    root_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["folder_2023_id", "2023"],
        ["folder_2024_id", "2024"]
    ]});</script>
    """

    # 2023 folder response (contains series)
    html_2023 = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["folder_2023_m_id", "m"],
        ["folder_2023_s_id", "s"]
    ]});</script>
    """

    # 2024 folder response (contains series)
    html_2024 = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["folder_2024_w_id", "w"]
    ]});</script>
    """

    # m folder response (contains files)
    html_2023_m = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["file_1_id", "9609_m23_qp_12.pdf"],
        ["file_2_id", "9609_m23_ms_12.pdf"]
    ]});</script>
    """

    # s folder response (contains files)
    html_2023_s = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["file_3_id", "9609_s23_qp_11.pdf"]
    ]});</script>
    """

    # w folder response (contains files)
    html_2024_w = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["file_4_id", "9609_w24_in_31.pdf"]
    ]});</script>
    """

    responses.add(responses.GET, f"https://drive.google.com/drive/folders/{root_id}", body=root_html, status=200)
    responses.add(responses.GET, f"https://drive.google.com/drive/folders/folder_2023_id", body=html_2023, status=200)
    responses.add(responses.GET, f"https://drive.google.com/drive/folders/folder_2024_id", body=html_2024, status=200)
    responses.add(responses.GET, f"https://drive.google.com/drive/folders/folder_2023_m_id", body=html_2023_m, status=200)
    responses.add(responses.GET, f"https://drive.google.com/drive/folders/folder_2023_s_id", body=html_2023_s, status=200)
    responses.add(responses.GET, f"https://drive.google.com/drive/folders/folder_2024_w_id", body=html_2024_w, status=200)

    # Note: Using ID directly as test
    tree = crawl_tree(root_id)

    assert tree == {
        "2023": {
            "m": {
                "9609_m23_qp_12.pdf": "file_1_id",
                "9609_m23_ms_12.pdf": "file_2_id"
            },
            "s": {
                "9609_s23_qp_11.pdf": "file_3_id"
            }
        },
        "2024": {
            "w": {
                "9609_w24_in_31.pdf": "file_4_id"
            }
        }
    }


@responses.activate
def test_crawl_tree_invalid_root_id():
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    root_id = "invalid_root_folder_id"

    # Mock 404 response
    responses.add(
        responses.GET,
        f"https://drive.google.com/drive/folders/{root_id}",
        status=404
    )

    with pytest.raises(Exception): # should raise HTTPError
        crawl_tree(root_id)

@responses.activate
def test_crawl_tree_empty_folder():
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    root_id = "empty_root_folder_id"

    # Root folder response (contains nothing relevant)
    root_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
    ]});</script>
    """

    responses.add(
        responses.GET,
        f"https://drive.google.com/drive/folders/{root_id}",
        body=root_html,
        status=200
    )

    tree = crawl_tree(root_id)
    assert tree == {}

@responses.activate
def test_crawl_tree_deeply_nested_subfolders_ignored():
    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    root_id = "root_folder_with_nesting_id"

    # Root folder response (contains years)
    root_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["folder_2023_id", "2023"],
        ["random_folder_id", "Random Folder"]
    ]});</script>
    """

    # 2023 folder response (contains series)
    html_2023 = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["folder_2023_m_id", "m"],
        ["invalid_series_id", "invalid_series"]
    ]});</script>
    """

    # m folder response (contains files and a nested folder masquerading as file without pdf extension)
    html_2023_m = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["file_1_id", "9609_m23_qp_12.pdf"],
        ["nested_folder_id", "nested_folder"]
    ]});</script>
    """

    responses.add(responses.GET, f"https://drive.google.com/drive/folders/{root_id}", body=root_html, status=200)
    responses.add(responses.GET, f"https://drive.google.com/drive/folders/folder_2023_id", body=html_2023, status=200)
    responses.add(responses.GET, f"https://drive.google.com/drive/folders/folder_2023_m_id", body=html_2023_m, status=200)

    tree = crawl_tree(root_id)

    # Assert nested folders and invalid years/series are ignored
    assert tree == {
        "2023": {
            "m": {
                "9609_m23_qp_12.pdf": "file_1_id",
            }
        }
    }

    # Test that the result is cached
    cache_path = os.path.join(cache_dir, f"crawl_{root_id}.json")
    assert os.path.exists(cache_path)

    with open(cache_path, "r") as f:
        cached_tree = json.load(f)

    assert cached_tree == tree

    # Test cache usage (responses.calls should not increase)
    call_count = len(responses.calls)
    tree2 = crawl_tree(root_id)
    assert len(responses.calls) == call_count
    assert tree2 == tree

@responses.activate
def test_crawl_tree_url():
    # Similar to above, but with URL
    root_id = "root_folder_id"
    url = f"https://drive.google.com/drive/folders/{root_id}?usp=sharing"

    responses.add(
        responses.GET,
        f"https://drive.google.com/drive/folders/{root_id}",
        body='<script>AF_initDataCallback({key: \'ds:1\', data: [["folder_2023_id", "2023"]]});</script>',
        status=200
    )
    responses.add(
        responses.GET,
        f"https://drive.google.com/drive/folders/folder_2023_id",
        body='<script>AF_initDataCallback({key: \'ds:1\', data: [["folder_m_id", "m"]]});</script>',
        status=200
    )
    responses.add(
        responses.GET,
        f"https://drive.google.com/drive/folders/folder_m_id",
        body='<script>AF_initDataCallback({key: \'ds:1\', data: [["f_id", "test.pdf"]]});</script>',
        status=200
    )

    cache_dir = ".cache/drive_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)

    tree = crawl_tree(url)
    assert tree == {
        "2023": {
            "m": {
                "test.pdf": "f_id"
            }
        }
    }
