import os
import shutil
import responses
from pypdf import PdfReader
from ppq_mertactor.compiler import compile_variant

@responses.activate
def test_single_variant_collation():
    # Setup
    cache_dir = ".cache/drive_cache"
    output_dir = "output"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # Read dummy PDFs
    with open("tests/fixtures/qp.pdf", "rb") as f:
        qp_content = f.read()
    with open("tests/fixtures/ms.pdf", "rb") as f:
        ms_content = f.read()

    # We will mock the root folder mapping, which would eventually be dynamic but for the tracer bullet
    # we just mock the exact folder id for the specific year/series.
    # Let's say the root folder for 2023 May/June has id "mock_folder_id".

    # Mock Google Drive Folder HTML response containing the file IDs
    # In reality, Google embeds this in a script tag like `AF_initDataCallback({key: 'ds:1', data: [...]});`
    # We will simulate a simplified version of this string in our mock.
    mock_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_qp_id", "9609_s23_qp_11.pdf"],
        ["mock_ms_id", "9609_s23_ms_11.pdf"]
    ]});</script>
    """

    folder_url = "https://drive.google.com/drive/folders/mock_folder_id"
    responses.add(responses.GET, folder_url, body=mock_html, status=200)

    qp_url = "https://drive.google.com/uc?export=download&id=mock_qp_id"
    ms_url = "https://drive.google.com/uc?export=download&id=mock_ms_id"

    responses.add(responses.GET, qp_url, body=qp_content, status=200)
    responses.add(responses.GET, ms_url, body=ms_content, status=200)

    # Execute
    # The specification says: "When given a syllabus (9609), a year (2023), and a single series/variant (e.g. May/June 2023 variant 11, component 1)... produces output/9609/2023/9609_2023_Component_1.pdf"

    compile_variant(
        syllabus="9609",
        year="2023",
        series="May/June",
        variant="11",
        component="1",
        folder_id="mock_folder_id", # Pass the known folder for this slice
        output_dir=output_dir
    )

    # Verify
    output_pdf_path = os.path.join(output_dir, "9609", "2023", "9609_2023_Component_1.pdf")
    assert os.path.exists(output_pdf_path), "Output PDF was not generated at the correct path."

    # Check if files were cached by their names
    cached_qp = os.path.join(cache_dir, "9609_s23_qp_11.pdf")
    cached_ms = os.path.join(cache_dir, "9609_s23_ms_11.pdf")
    assert os.path.exists(cached_qp), "QP was not cached."
    assert os.path.exists(cached_ms), "MS was not cached."

    # Verify PDF content / length
    reader = PdfReader(output_pdf_path)
    assert len(reader.pages) == 2, f"Expected 2 pages in compiled PDF, got {len(reader.pages)}"

    # Test caching (run again, should not hit network for PDFs)
    compile_variant(
        syllabus="9609",
        year="2023",
        series="May/June",
        variant="11",
        component="1",
        folder_id="mock_folder_id",
        output_dir=output_dir
    )

    # First call: 1 folder fetch + 2 PDF fetches = 3
    # Second call: 1 folder fetch + 0 PDF fetches = 4 total calls
    assert len(responses.calls) == 4, "Network was hit again despite caching!"

import pytest

@responses.activate
def test_missing_documents():
    output_dir = "output_missing"

    # Test missing QP
    mock_html_no_qp = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_ms_id", "9609_s23_ms_11.pdf"]
    ]});</script>
    """
    responses.add(responses.GET, "https://drive.google.com/drive/folders/folder_no_qp", body=mock_html_no_qp, status=200)

    with pytest.raises(ValueError, match="Question Paper 9609_s23_qp_11.pdf not found in folder metadata"):
        compile_variant(
            syllabus="9609",
            year="2023",
            series="May/June",
            variant="11",
            component="1",
            folder_id="folder_no_qp",
            output_dir=output_dir
        )

    # Test missing MS
    mock_html_no_ms = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_qp_id", "9609_s23_qp_11.pdf"]
    ]});</script>
    """
    responses.add(responses.GET, "https://drive.google.com/drive/folders/folder_no_ms", body=mock_html_no_ms, status=200)

    with pytest.raises(ValueError, match="Mark Scheme 9609_s23_ms_11.pdf not found in folder metadata"):
        compile_variant(
            syllabus="9609",
            year="2023",
            series="May/June",
            variant="11",
            component="1",
            folder_id="folder_no_ms",
            output_dir=output_dir
        )

from pypdf.errors import PdfStreamError, PdfReadError

@responses.activate
def test_corrupt_pdf():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_corrupt"

    # We must ensure there is no cached file, else fetch_document returns it instead of making requests
    cached_qp = os.path.join(cache_dir, "9609_s23_qp_11.pdf")
    cached_ms = os.path.join(cache_dir, "9609_s23_ms_11.pdf")
    if os.path.exists(cached_qp):
        os.remove(cached_qp)
    if os.path.exists(cached_ms):
        os.remove(cached_ms)

    mock_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_qp_id", "9609_s23_qp_11.pdf"],
        ["mock_ms_id", "9609_s23_ms_11.pdf"]
    ]});</script>
    """
    responses.add(responses.GET, "https://drive.google.com/drive/folders/folder_corrupt", body=mock_html, status=200)

    qp_url = "https://drive.google.com/uc?export=download&id=mock_qp_id"
    ms_url = "https://drive.google.com/uc?export=download&id=mock_ms_id"

    # Return invalid PDF bytes
    responses.add(responses.GET, qp_url, body=b"this is not a pdf file", status=200)
    responses.add(responses.GET, ms_url, body=b"this is also not a pdf file", status=200)

    with pytest.raises((PdfStreamError, PdfReadError)):
        compile_variant(
            syllabus="9609",
            year="2023",
            series="May/June",
            variant="11",
            component="1",
            folder_id="folder_corrupt",
            output_dir=output_dir
        )

@responses.activate
def test_cache_invalidation():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_cache"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

    with open("tests/fixtures/qp.pdf", "rb") as f:
        qp_content = f.read()
    with open("tests/fixtures/ms.pdf", "rb") as f:
        ms_content = f.read()

    mock_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_qp_id_2", "9609_s23_qp_11.pdf"],
        ["mock_ms_id_2", "9609_s23_ms_11.pdf"]
    ]});</script>
    """

    responses.add(responses.GET, "https://drive.google.com/drive/folders/folder_cache", body=mock_html, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_qp_id_2", body=qp_content, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_ms_id_2", body=ms_content, status=200)

    # 1. First run, empty cache, should fetch 1 metadata + 2 pdfs = 3 calls
    compile_variant(
        syllabus="9609",
        year="2023",
        series="May/June",
        variant="11",
        component="1",
        folder_id="folder_cache",
        output_dir=output_dir
    )

    assert len(responses.calls) == 3

    # 2. Second run, cache populated, should only fetch 1 metadata = +1 call = 4 total
    compile_variant(
        syllabus="9609",
        year="2023",
        series="May/June",
        variant="11",
        component="1",
        folder_id="folder_cache",
        output_dir=output_dir
    )

    assert len(responses.calls) == 4

    # 3. Cache invalidation: delete only the QP from the cache
    cached_qp = os.path.join(cache_dir, "9609_s23_qp_11.pdf")
    os.remove(cached_qp)

    # 4. Third run, cache missing QP, should fetch 1 metadata + 1 QP pdf = +2 calls = 6 total
    compile_variant(
        syllabus="9609",
        year="2023",
        series="May/June",
        variant="11",
        component="1",
        folder_id="folder_cache",
        output_dir=output_dir
    )

    assert len(responses.calls) == 6
