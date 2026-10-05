import os
from pypdf import PdfWriter
from ppq_mertactor.drive import fetch_document, get_folder_metadata

def get_series_code(series: str) -> str:
    """Translates the series string into the Cambridge code."""
    mapping = {
        "Feb/March": "m",
        "May/June": "s",
        "Oct/Nov": "w"
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
