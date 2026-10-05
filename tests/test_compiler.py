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
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
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
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)


@responses.activate
def test_full_component_compilation():
    from ppq_mertactor.compiler import compile_component
    cache_dir = ".cache/drive_cache"
    output_dir = "output_full"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    with open("tests/fixtures/qp.pdf", "rb") as f:
        pdf_content = f.read()

    # Folders mapping
    series_folders = {
        "Feb/March": "folder_m",
        "May/June": "folder_s",
        "Oct/Nov": "folder_w",
        "Specimen": "folder_y"
    }

    # Generate HTML content for each series
    # Component 1 => variants 11, 12, 13 (we'll just use 11 and 12 for testing, plus an Insert)
    # We will test Component 3 to ensure we test 'in', 'qp', 'ms', and omit 'gt'

    mock_htmls = {
        "folder_m": """<script>AF_initDataCallback({key: 'ds:1', data: [
            ["m_in_32", "9609_m23_in_32.pdf"],
            ["m_qp_32", "9609_m23_qp_32.pdf"],
            ["m_ms_32", "9609_m23_ms_32.pdf"],
            ["m_gt", "9609_m23_gt.pdf"],
            ["m_qp_12", "9609_m23_qp_12.pdf"]
        ]});</script>""",
        "folder_s": """<script>AF_initDataCallback({key: 'ds:1', data: [
            ["s_qp_31", "9609_s23_qp_31.pdf"],
            ["s_ms_31", "9609_s23_ms_31.pdf"]
        ]});</script>""",
        "folder_w": """<script>AF_initDataCallback({key: 'ds:1', data: [
            ["w_ms_33", "9609_w23_ms_33.pdf"],
            ["w_qp_33", "9609_w23_qp_33.pdf"],
            ["w_in_33", "9609_w23_in_33.pdf"]
        ]});</script>""",
        "folder_y": """<script>AF_initDataCallback({key: 'ds:1', data: [
            ["y_qp_03", "9609_y23_qp_03.pdf"],
            ["y_ms_03", "9609_y23_ms_03.pdf"],
            ["y_in_03", "9609_y23_in_03.pdf"]
        ]});</script>"""
    }

    for series, folder_id in series_folders.items():
        responses.add(responses.GET, f"https://drive.google.com/drive/folders/{folder_id}", body=mock_htmls[folder_id], status=200)

    # Add responses for all PDF files
    all_file_ids = [
        "m_in_32", "m_qp_32", "m_ms_32", "m_gt", "m_qp_12",
        "s_qp_31", "s_ms_31",
        "w_ms_33", "w_qp_33", "w_in_33",
        "y_qp_03", "y_ms_03", "y_in_03"
    ]
    for fid in all_file_ids:
        responses.add(responses.GET, f"https://drive.google.com/uc?export=download&id={fid}", body=pdf_content, status=200)

    # Call compile_component for Component 3
    # Note: Component 3 will include variants starting with 3 (e.g. 31, 32, 33, 03 for specimen)
    compile_component(
        syllabus="9609",
        year="2023",
        component="3",
        series_folders=series_folders,
        output_dir=output_dir
    )

    # Verification
    output_pdf_path = os.path.join(output_dir, "9609", "2023", "9609_2023_Component_3.pdf")
    assert os.path.exists(output_pdf_path), "Component compilation PDF not found."

    reader = PdfReader(output_pdf_path)

    # We have 10 valid files for component 3:
    # m: in_32, qp_32, ms_32
    # s: qp_31, ms_31
    # w: in_33, qp_33, ms_33
    # y: in_03, qp_03, ms_03
    # 11 files total. Each is 1 page long from fixture (qp.pdf is 1 page in this code? No, wait: length of qp.pdf is 1 page. Let's verify lengths later, assume each is 1 page)
    # Actually qp.pdf has 1 page in our minds but let's check its length first. Wait, test_single_variant_collation says reader.pages == 2, which means qp.pdf has 1 page and ms.pdf has 1 page. So 11 pages total.
    # Total pages should be 11.
    assert len(reader.pages) == 11, f"Expected 11 pages, got {len(reader.pages)}"

    # Check bookmarks (outlines)
    # Outline format in pypdf: list of Destination objects or lists.
    outlines = reader.outline

    def count_bookmarks(outlines):
        count = 0
        for item in outlines:
            if isinstance(item, list):
                count += count_bookmarks(item)
            else:
                count += 1
        return count

    # We expect:
    # 4 top-level bookmarks (Feb/March 2023, May/June 2023, Oct/Nov 2023, Specimen 2023)
    # inside Feb/March: Variant 32 - Insert, Variant 32 - Question Paper, Variant 32 - Mark Scheme (3)
    # inside May/June: Variant 31 - Question Paper, Variant 31 - Mark Scheme (2)
    # inside Oct/Nov: Variant 33 - Insert, Variant 33 - Question Paper, Variant 33 - Mark Scheme (3)
    # inside Specimen: Variant 03 - Insert, Variant 03 - Question Paper, Variant 03 - Mark Scheme (3)
    # Total = 4 + 3 + 2 + 3 + 3 = 15 bookmarks
    assert count_bookmarks(outlines) == 15, "Incorrect number of bookmarks."

    # Verify bookmark titles recursively
    titles = []
    def extract_titles(items):
        for item in items:
            if isinstance(item, list):
                extract_titles(item)
            else:
                titles.append(item.title)
    extract_titles(outlines)

    expected_titles = [
        "Feb/March 2023",
        "Variant 32 - Insert",
        "Variant 32 - Question Paper",
        "Variant 32 - Mark Scheme",
        "May/June 2023",
        "Variant 31 - Question Paper",
        "Variant 31 - Mark Scheme",
        "Oct/Nov 2023",
        "Variant 33 - Insert",
        "Variant 33 - Question Paper",
        "Variant 33 - Mark Scheme",
        "Specimen 2023",
        "Variant 03 - Insert",
        "Variant 03 - Question Paper",
        "Variant 03 - Mark Scheme"
    ]
    assert titles == expected_titles, f"Expected titles {expected_titles}, but got {titles}"
