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

def compile_variant(syllabus: str, year: str, series: str, variant: str, component: str, folder_id: str, output_dir: str = "output") -> str:
    """
    Identifies the QP and MS for a specific variant in a drive folder,
    fetches them, collates them (QP followed by MS),
    and saves the output to the specified structure.
    """
    # 1. Fetch metadata
    metadata = get_folder_metadata(folder_id)

    # 2. Identify documents
    # Format: 9609_s23_qp_11.pdf
    year_short = year[-2:]
    series_code = get_series_code(series)

    qp_filename = f"{syllabus}_{series_code}{year_short}_qp_{variant}.pdf"
    ms_filename = f"{syllabus}_{series_code}{year_short}_ms_{variant}.pdf"

    if qp_filename not in metadata:
        raise ValueError(f"Question Paper {qp_filename} not found in folder metadata.")
    if ms_filename not in metadata:
        raise ValueError(f"Mark Scheme {ms_filename} not found in folder metadata.")

    qp_file_id = metadata[qp_filename]
    ms_file_id = metadata[ms_filename]

    # 3. Fetch documents
    qp_path = fetch_document(qp_file_id, qp_filename)
    ms_path = fetch_document(ms_file_id, ms_filename)

    # 4. Collate documents
    writer = PdfWriter()
    writer.append(qp_path)
    writer.append(ms_path)

    # 5. Output
    full_output_dir = os.path.join(output_dir, syllabus, year)
    os.makedirs(full_output_dir, exist_ok=True)

    output_filename = f"{syllabus}_{year}_Component_{component}.pdf"
    output_path = os.path.join(full_output_dir, output_filename)

    with open(output_path, "wb") as out_f:
        writer.write(out_f)

    return output_path


def compile_component(syllabus: str, year: str, component: str, series_folders: dict[str, str], output_dir: str = "output") -> str:
    """
    Compiles a full-year revision booklet for a specific component.
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
        # filenames usually look like: 9609_s23_qp_11.pdf
        # format is: {syllabus}_{series_code}{year_short}_{doc_type}_{variant}.pdf
        # doc_type: in, qp, ms, gt
        # variant: 2-digit, first digit is component, e.g. 11, 12, 13
        # specimen variants might be 03, wait, test says y_qp_03 -> component 3. So component might be the second char from the end before .pdf

        # Let's extract variants for this component
        # A file is valid if it matches pattern: syllabus_seriesyear_doctype_variant.pdf

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
                continue # Omit Grade Thresholds

            # If variant starts with the component number or ends with component number for specimen?
            # Actually, standard is variant like 11, 12, 13. Or 03 for specimen. Wait, 03 -> component 3.
            # Component is the last digit of the variant for specimen? No, specimen variants are 01, 02, 03.
            # Normal variants: 11 (comp 1, region 1), 32 (comp 3, region 2).
            # So the component is the FIRST digit of the variant. Or if variant starts with '0', the SECOND digit.
            # Actually, int(variant) // 10 if variant is 2 digits? No, 03 is 3. So int(variant[0]) if it's non zero, else int(variant[1])?
            # Wait, 03 means component 3? Yes. 11 means component 1? Yes.
            # If variant length is 2: component number is variant[0] if variant[0] != '0' else variant[1]?
            # Let's look at standard: variant is usually component + region, e.g., '1' + '1' -> '11'.
            # Specimen variants are '0' + component, e.g., '0' + '3' -> '03'.

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
        # Note: in pypdf, add_outline_item returns an OutlineItem which can be used as parent
        series_bookmark_title = f"{series} {year}"

        # We need to add the outline pointing to the first page of this series.
        # But we only know the page after we add it.
        # Actually pypdf add_outline_item takes page_number.
        # The page number is len(writer.pages) at the time of adding.

        # To handle this, we can just track current page count
        # current_page = len(writer.pages)
        # series_parent = writer.add_outline_item(series_bookmark_title, current_page)

        series_parent = None
        series_has_pages = False

        # Sort variants (e.g. 11, 12, 13 or 03)
        sorted_variants = sorted(component_files.keys())

        doc_order = {"in": 1, "qp": 2, "ms": 3}
        doc_names = {"in": "Insert", "qp": "Question Paper", "ms": "Mark Scheme"}

        for variant in sorted_variants:
            docs = component_files[variant]
            sorted_doc_types = sorted(docs.keys(), key=lambda d: doc_order.get(d, 99))

            for doc_type in sorted_doc_types:
                file_id = docs[doc_type]
                filename = f"{syllabus}_{series_code}{year_short}_{doc_type}_{variant}.pdf"

                doc_path = fetch_document(file_id, filename)

                # Append pdf
                start_page = len(writer.pages)
                writer.append(doc_path)

                if not series_has_pages:
                    series_parent = writer.add_outline_item(series_bookmark_title, start_page)
                    series_has_pages = True

                # Add nested bookmark
                doc_title = f"Variant {variant} - {doc_names.get(doc_type, doc_type)}"
                writer.add_outline_item(doc_title, start_page, parent=series_parent)

    # Output
    full_output_dir = os.path.join(output_dir, syllabus, year)
    os.makedirs(full_output_dir, exist_ok=True)

    output_filename = f"{syllabus}_{year}_Component_{component}.pdf"
    output_path = os.path.join(full_output_dir, output_filename)

    with open(output_path, "wb") as out_f:
        writer.write(out_f)

    return output_path
