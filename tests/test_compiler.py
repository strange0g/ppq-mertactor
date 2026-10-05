import os
import shutil
import random
import pytest
import responses
from pypdf import PdfReader
from pypdf.errors import PdfStreamError, PdfReadError
from ppq_mertactor.compiler import (
    compile_variant,
    compile_examiner_reports,
    compile_component,
)

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
    compile_variant(
        syllabus="9609",
        year="2023",
        series="May/June",
        variant="11",
        component="1",
        folder_id="mock_folder_id",
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


@responses.activate
def test_corrupt_pdf():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_corrupt"

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

    # 1. First run, empty cache
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

    # 2. Second run, cache populated
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

    # 3. Cache invalidation
    cached_qp = os.path.join(cache_dir, "9609_s23_qp_11.pdf")
    os.remove(cached_qp)

    # 4. Third run, cache missing QP
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
def test_er_compilation_chronological_ordering():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_er"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    with open("tests/fixtures/qp.pdf", "rb") as f:
        er_content = f.read()

    mock_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_w_er", "9609_w23_er.pdf"],
        ["mock_s_gt", "9609_s23_gt.pdf"],
        ["mock_m_er", "9609_m23_er.pdf"],
        ["mock_s_er", "9609_s23_er.pdf"]
    ]});</script>
    """

    responses.add(responses.GET, "https://drive.google.com/drive/folders/mock_er_folder", body=mock_html, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_m_er", body=er_content, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_s_er", body=er_content, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_w_er", body=er_content, status=200)

    output_path = compile_examiner_reports("9609", "2023", "mock_er_folder", output_dir=output_dir)

    assert os.path.exists(output_path)
    assert output_path == os.path.join(output_dir, "9609", "2023", "9609_2023_Examiner_Reports.pdf")

    reader = PdfReader(output_path)
    assert len(reader.pages) == 3

    outlines = reader.outline
    titles = []
    for item in outlines:
        if isinstance(item, list):
            continue
        if hasattr(item, 'title'):
            titles.append(item.title)
        elif isinstance(item, dict) and '/Title' in item:
            titles.append(item['/Title'])

    assert titles == ["Feb/March 2023", "May/June 2023", "Oct/Nov 2023"]


@responses.activate
def test_er_compilation_missing_series():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_er_missing"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    with open("tests/fixtures/qp.pdf", "rb") as f:
        er_content = f.read()

    mock_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_w_er", "9609_w23_er.pdf"],
        ["mock_m_er", "9609_m23_er.pdf"]
    ]});</script>
    """

    responses.add(responses.GET, "https://drive.google.com/drive/folders/mock_er_folder_missing", body=mock_html, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_m_er", body=er_content, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_w_er", body=er_content, status=200)

    output_path = compile_examiner_reports("9609", "2023", "mock_er_folder_missing", output_dir=output_dir)
    assert os.path.exists(output_path)

    reader = PdfReader(output_path)
    assert len(reader.pages) == 2

    outlines = reader.outline
    titles = []
    for item in outlines:
        if isinstance(item, list):
            continue
        if hasattr(item, 'title'):
            titles.append(item.title)
        elif isinstance(item, dict) and '/Title' in item:
            titles.append(item['/Title'])

    assert titles == ["Feb/March 2023", "Oct/Nov 2023"]


@responses.activate
def test_er_compilation_grade_thresholds_omitted():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_er_gt"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    with open("tests/fixtures/qp.pdf", "rb") as f:
        er_content = f.read()

    mock_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_s_er", "9609_s23_er.pdf"],
        ["mock_s_gt", "9609_s23_gt.pdf"]
    ]});</script>
    """

    responses.add(responses.GET, "https://drive.google.com/drive/folders/mock_er_folder_gt", body=mock_html, status=200)
    responses.add(responses.GET, "https://drive.google.com/uc?export=download&id=mock_s_er", body=er_content, status=200)

    output_path = compile_examiner_reports("9609", "2023", "mock_er_folder_gt", output_dir=output_dir)
    assert os.path.exists(output_path)

    reader = PdfReader(output_path)
    assert len(reader.pages) == 1

    outlines = reader.outline
    titles = []
    for item in outlines:
        if isinstance(item, list):
            continue
        if hasattr(item, 'title'):
            titles.append(item.title)
        elif isinstance(item, dict) and '/Title' in item:
            titles.append(item['/Title'])

    assert titles == ["May/June 2023"]
    assert "gt" not in str(titles).lower()


@responses.activate
def test_er_compilation_no_reports():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_er_no_reports"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    mock_html = """
    <script>AF_initDataCallback({key: 'ds:1', data: [
        ["mock_s_gt", "9609_s23_gt.pdf"],
        ["mock_qp", "9609_s23_qp_11.pdf"]
    ]});</script>
    """

    responses.add(responses.GET, "https://drive.google.com/drive/folders/mock_er_folder_no_reports", body=mock_html, status=200)

    output_path = compile_examiner_reports("9609", "2023", "mock_er_folder_no_reports", output_dir=output_dir)
    assert os.path.exists(output_path)

    reader = PdfReader(output_path)
    assert len(reader.pages) == 0


@responses.activate
def test_full_component_compilation():
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

    series_folders = {
        "Feb/March": "folder_m",
        "May/June": "folder_s",
        "Oct/Nov": "folder_w",
        "Specimen": "folder_y"
    }

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

    all_file_ids = [
        "m_in_32", "m_qp_32", "m_ms_32", "m_gt", "m_qp_12",
        "s_qp_31", "s_ms_31",
        "w_ms_33", "w_qp_33", "w_in_33",
        "y_qp_03", "y_ms_03", "y_in_03"
    ]
    for fid in all_file_ids:
        responses.add(responses.GET, f"https://drive.google.com/uc?export=download&id={fid}", body=pdf_content, status=200)

    compile_component(
        syllabus="9609",
        year="2023",
        component="3",
        series_folders=series_folders,
        output_dir=output_dir
    )

    output_pdf_path = os.path.join(output_dir, "9609", "2023", "9609_2023_Component_3.pdf")
    assert os.path.exists(output_pdf_path), "Component compilation PDF not found."

    reader = PdfReader(output_pdf_path)
    assert len(reader.pages) == 11, f"Expected 11 pages, got {len(reader.pages)}"

    outlines = reader.outline

    def count_bookmarks(items):
        count = 0
        for item in items:
            if isinstance(item, list):
                count += count_bookmarks(item)
            else:
                count += 1
        return count

    assert count_bookmarks(outlines) == 15, "Incorrect number of bookmarks."

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


@responses.activate
def test_component_compilation_edge_cases_and_invariants():
    cache_dir = ".cache/drive_cache"
    output_dir = "output_edge"
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    with open("tests/fixtures/qp.pdf", "rb") as f:
        pdf_content = f.read()

    series_folders = {
        "Feb/March": "folder_m",
        "May/June": "folder_s",
        "Oct/Nov": "folder_w",
        "Specimen": "folder_y"
    }

    data_m = [
        ["m_in_32", "9609_m23_in_32.pdf"],
        ["m_qp_32", "9609_m23_qp_32.pdf"],
        ["m_gt", "9609_m23_gt.pdf"],
        ["m_invalid_1", "9609_m23_32.pdf"],
        ["m_invalid_2", "invalid_name.pdf"]
    ]
    random.shuffle(data_m)
    data_m_str = str(data_m).replace("'", '"')
    html_m = f"<script>AF_initDataCallback({{key: 'ds:1', data: {data_m_str}}});</script>"

    data_s = [
        ["s_ms_31", "9609_s23_ms_31.pdf"],
        ["s_in_31", "9609_s23_in_31.pdf"],
        ["s_qp_31", "9609_s23_qp_31.pdf"],
        ["s_qp_41", "9609_s23_qp_41.pdf"]
    ]
    random.shuffle(data_s)
    data_s_str = str(data_s).replace("'", '"')
    html_s = f"<script>AF_initDataCallback({{key: 'ds:1', data: {data_s_str}}});</script>"

    data_w = [
        ["w_qp_11", "9609_w23_qp_11.pdf"],
    ]
    data_w_str = str(data_w).replace("'", '"')
    html_w = f"<script>AF_initDataCallback({{key: 'ds:1', data: {data_w_str}}});</script>"

    data_y = [
        ["y_ms_03", "9609_y23_ms_03.pdf"]
    ]
    data_y_str = str(data_y).replace("'", '"')
    html_y = f"<script>AF_initDataCallback({{key: 'ds:1', data: {data_y_str}}});</script>"

    mock_htmls = {
        "folder_m": html_m,
        "folder_s": html_s,
        "folder_w": html_w,
        "folder_y": html_y
    }

    for series, folder_id in series_folders.items():
        responses.add(responses.GET, f"https://drive.google.com/drive/folders/{folder_id}", body=mock_htmls[folder_id], status=200)

    all_file_ids = [
        "m_in_32", "m_qp_32", "m_gt",
        "s_in_31", "s_qp_31", "s_ms_31", "s_qp_41",
        "w_qp_11",
        "y_ms_03"
    ]
    for fid in all_file_ids:
        responses.add(responses.GET, f"https://drive.google.com/uc?export=download&id={fid}", body=pdf_content, status=200)

    compile_component(
        syllabus="9609",
        year="2023",
        component="3",
        series_folders=series_folders,
        output_dir=output_dir
    )

    output_pdf_path = os.path.join(output_dir, "9609", "2023", "9609_2023_Component_3.pdf")
    assert os.path.exists(output_pdf_path), "Component compilation PDF not found."

    reader = PdfReader(output_pdf_path)
    assert len(reader.pages) == 6, f"Expected 6 pages, got {len(reader.pages)}"

    outlines = reader.outline

    def extract_titles(items):
        titles = []
        for item in items:
            if isinstance(item, list):
                titles.extend(extract_titles(item))
            else:
                titles.append(item.title)
        return titles

    titles = extract_titles(outlines)

    expected_titles = [
        "Feb/March 2023",
        "Variant 32 - Insert",
        "Variant 32 - Question Paper",
        "May/June 2023",
        "Variant 31 - Insert",
        "Variant 31 - Question Paper",
        "Variant 31 - Mark Scheme",
        "Specimen 2023",
        "Variant 03 - Mark Scheme"
    ]

    assert titles == expected_titles, f"Expected titles {expected_titles}, but got {titles}"
