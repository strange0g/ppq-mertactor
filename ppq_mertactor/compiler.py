import os
from pypdf import PdfWriter
from ppq_mertactor.drive import fetch_document, get_folder_metadata

def get_series_code(series: str) -> str:
    """Translates the series string into the Cambridge code."""
    mapping = {
        "Feb/March": "m",
        "May/June": "s",
        "Oct/Nov": "w",
        "Specimen": "y"
    }
    return mapping.get(series, "s")

from typing import Callable, Optional

def compile_examiner_reports(syllabus: str, year: str, folder_id: str, output_dir: str = "output", progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
    """
    Compiles an Examiner Reports Compilation consolidating all series examiner reports for the selected year.
    """
    # 1. Fetch metadata
    metadata = get_folder_metadata(folder_id)

    year_short = year[-2:]

    # Chronological series codes mapping
    series_titles = {
        "m": f"Feb/March {year}",
        "s": f"May/June {year}",
        "w": f"Oct/Nov {year}"
    }

    # Expected file format: 9609_s23_er.pdf
    expected_filenames = []
    for code in ["m", "s", "w"]:
        expected_filenames.append((code, f"{syllabus}_{code}{year_short}_er.pdf"))

    writer = PdfWriter()

    for code, filename in expected_filenames:
        if filename in metadata:
            file_id = metadata[filename]
            doc_path = fetch_document(file_id, filename, progress_callback=progress_callback)

            # Record start page
            start_page_index = len(writer.pages)

            # Append document
            writer.append(doc_path)

            # Add bookmark
            writer.add_outline_item(series_titles[code], start_page_index)

    if len(writer.pages) == 0:
        return None

    # Output
    full_output_dir = os.path.join(output_dir, syllabus, year)
    os.makedirs(full_output_dir, exist_ok=True)

    output_filename = f"{syllabus}_{year}_Examiner_Reports.pdf"
    output_path = os.path.join(full_output_dir, output_filename)

    with open(output_path, "wb") as out_f:
        writer.write(out_f)

    return output_path

def compile_component(syllabus: str, year: str, component: str, series_folders: dict[str, str], output_dir: str = "output", progress_callback: Optional[Callable[[int, int], None]] = None) -> str:
    """
    Compiles a Component Compilation for a specific component.
    """

    # Chronological series order
    chronological_order = {
        "Feb/March": 1,
        "May/June": 2,
        "Oct/Nov": 3,
        "Specimen": 4
    }

    # Sort series
    sorted_series = sorted(series_folders.keys(), key=lambda s: chronological_order.get(s, 99))

    year_short = year[-2:]
    writer = PdfWriter()

    # We will build the pdf and bookmarks
    for series in sorted_series:
        folder_id = series_folders[series]
        series_code = get_series_code(series)

        metadata = get_folder_metadata(folder_id)

        # Filter files belonging to this component
        component_files = {}
        for filename, file_id in metadata.items():
            if not filename.endswith(".pdf"):
                continue

            parts = filename.replace(".pdf", "").split("_")
            if len(parts) != 4:
                continue

            file_syllabus, file_series_year, doc_type, variant = parts

            if file_syllabus != syllabus:
                continue
            if file_series_year != f"{series_code}{year_short}":
                continue
            if doc_type == "gt":
                continue  # Omit Grade Thresholds

            file_component = variant[0]
            if file_component == '0':
                file_component = variant[1]

            if file_component != component:
                continue

            if variant not in component_files:
                component_files[variant] = {}
            component_files[variant][doc_type] = file_id

        if not component_files:
            continue

        # Add top level bookmark for series
        series_bookmark_title = f"{series} {year}"

        series_parent = None
        series_has_pages = False

        # Sort variants (e.g. 11, 12, 13 or 03)
        sorted_variants = sorted(component_files.keys())

        doc_order = {"in": 1, "qp": 2, "ms": 3}
        doc_names = {"in": "Insert", "qp": "Question Paper", "ms": "Mark Scheme"}

        for variant in sorted_variants:
            docs = component_files[variant]
            sorted_doc_types = sorted(docs.keys(), key=lambda d: doc_order.get(d, 99))

            variant_parent = None

            for doc_type in sorted_doc_types:
                file_id = docs[doc_type]
                filename = f"{syllabus}_{series_code}{year_short}_{doc_type}_{variant}.pdf"

                doc_path = fetch_document(file_id, filename, progress_callback=progress_callback)

                # Append pdf
                start_page = len(writer.pages)
                writer.append(doc_path)

                if not series_has_pages:
                    series_parent = writer.add_outline_item(series_bookmark_title, start_page)
                    series_has_pages = True

                if variant_parent is None:
                    variant_title = f"Variant {variant}"
                    variant_parent = writer.add_outline_item(variant_title, start_page, parent=series_parent)

                # Add nested bookmark (Level 3)
                doc_title = f"{doc_names.get(doc_type, doc_type)}"
                writer.add_outline_item(doc_title, start_page, parent=variant_parent)

    # Output
    full_output_dir = os.path.join(output_dir, syllabus, year)
    os.makedirs(full_output_dir, exist_ok=True)

    output_filename = f"{syllabus}_{year}_Component_{component}.pdf"
    output_path = os.path.join(full_output_dir, output_filename)

    with open(output_path, "wb") as out_f:
        writer.write(out_f)

    return output_path
