import os
import shutil
import random
import pytest
import responses
from pypdf import PdfReader
from pypdf.errors import PdfStreamError, PdfReadError
from ppq_mertactor.compiler import (
    compile_examiner_reports,
    compile_component,
)

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
    assert output_path is None

    # Ensure no directories or files were created
    if os.path.exists(output_dir):
        # We can either check that output_dir is completely empty,
        # or at least that no PDFs were generated in it.
        # Given how `compile_examiner_reports` works, it shouldn't even create
        # the `os.makedirs(full_output_dir, exist_ok=True)` if it returns early.
        assert not os.path.exists(os.path.join(output_dir, "9609")), "Directories should not be created if no PDFs are found"
        # Also check just in case output_dir has no PDFs
        def get_all_files(path):
            files = []
            for dp, dn, filenames in os.walk(path):
                for f in filenames:
                    files.append(os.path.join(dp, f))
            return files
        assert len(get_all_files(output_dir)) == 0, "No files should be written"


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

    assert count_bookmarks(outlines) == 19, "Incorrect number of bookmarks."

    # Verify the 3-tier bookmark hierarchy and target pages
    bookmarks = []

    def extract_bookmarks(items, level=0):
        for item in items:
            if isinstance(item, list):
                extract_bookmarks(item, level + 1)
            else:
                page_idx = reader.get_destination_page_number(item)
                bookmarks.append((level, item.title, page_idx))

    extract_bookmarks(outlines)

    # Note: test fixture qp.pdf is 1 page long.
    # Therefore, each appended document consumes exactly 1 page.
    # We can calculate the exact expected page index for each document.
    expected_bookmarks = [
        (0, "Feb/March 2023", 0),          # starts at page 0
        (1, "Variant 32", 0),              # starts at page 0
        (2, "Insert", 0),                  # in_32
        (2, "Question Paper", 1),          # qp_32
        (2, "Mark Scheme", 2),             # ms_32
        (0, "May/June 2023", 3),           # starts at page 3
        (1, "Variant 31", 3),              # starts at page 3
        (2, "Question Paper", 3),          # qp_31
        (2, "Mark Scheme", 4),             # ms_31
        (0, "Oct/Nov 2023", 5),            # starts at page 5
        (1, "Variant 33", 5),              # starts at page 5
        (2, "Insert", 5),                  # in_33
        (2, "Question Paper", 6),          # qp_33
        (2, "Mark Scheme", 7),             # ms_33
        (0, "Specimen 2023", 8),           # starts at page 8
        (1, "Variant 03", 8),              # starts at page 8
        (2, "Insert", 8),                  # in_03
        (2, "Question Paper", 9),          # qp_03
        (2, "Mark Scheme", 10)             # ms_03
    ]

    assert bookmarks == expected_bookmarks, f"Expected bookmarks {expected_bookmarks}, but got {bookmarks}"


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

    bookmarks = []

    def extract_bookmarks(items, level=0):
        for item in items:
            if isinstance(item, list):
                extract_bookmarks(item, level + 1)
            else:
                page_idx = reader.get_destination_page_number(item)
                bookmarks.append((level, item.title, page_idx))

    extract_bookmarks(outlines)

    expected_bookmarks = [
        (0, "Feb/March 2023", 0),
        (1, "Variant 32", 0),
        (2, "Insert", 0),                  # in_32
        (2, "Question Paper", 1),          # qp_32
        (0, "May/June 2023", 2),
        (1, "Variant 31", 2),
        (2, "Insert", 2),                  # in_31
        (2, "Question Paper", 3),          # qp_31
        (2, "Mark Scheme", 4),             # ms_31
        (0, "Specimen 2023", 5),
        (1, "Variant 03", 5),
        (2, "Mark Scheme", 5)              # ms_03
    ]

    assert bookmarks == expected_bookmarks, f"Expected bookmarks {expected_bookmarks}, but got {bookmarks}"
