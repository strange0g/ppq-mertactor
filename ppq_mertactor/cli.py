import argparse
import sys
import questionary
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from ppq_mertactor.compiler import compile_component, compile_examiner_reports
# The compiler needs series_folders. The issue description does not say where they come from for the CLI,
# so let's import the hardcoded list from drive if it's there or just pass an empty dict for testing,
# or better yet, since the requirement is to use existing compile_component and compile_examiner_reports,
# and they both require folder_ids... let's see how drive handles it.
# We'll import a dummy function or use real fetching if we can, but since this is CLI testing, we can
# just use dummy folder mappings for now if not provided, or fetch them if there's a function.

# Let's inspect drive.py briefly in a bash command later to see if it exposes folder fetching.
# For now, let's implement the basic argparse structure.

def run_headless(args):
    series_folders = {}
    if args.series_m: series_folders["Feb/March"] = args.series_m
    if args.series_s: series_folders["May/June"] = args.series_s
    if args.series_w: series_folders["Oct/Nov"] = args.series_w
    if args.series_y: series_folders["Specimen"] = args.series_y

    years = []
    if args.all_years:
        years = [str(y) for y in range(2016, 2026)]
    elif args.year:
        years = [str(args.year)]

    components = []
    if args.all_components:
        components = ["1", "2", "3", "4"]
    elif args.components:
        components = args.components

    do_er = args.examiner_reports
    syllabus = args.syllabus

    # Optional: set cache dir globally or in os.environ since drive.py hardcodes it
    import os
    if args.cache_dir:
        os.environ["DRIVE_CACHE_DIR"] = args.cache_dir # we'll patch drive.py to use this

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Compiling papers...", total=len(years) * (len(components) + (1 if do_er else 0)))

        for year in years:
            for comp in components:
                progress.update(task, description=f"[cyan]Compiling {year} Component {comp}...")
                if series_folders:
                    compile_component(
                        syllabus=syllabus,
                        year=year,
                        component=comp,
                        series_folders=series_folders,
                        output_dir=args.output_dir
                    )
                else:
                    progress.console.print(f"[red]Skipping {year} Component {comp} - no series folder IDs provided.")
                progress.advance(task)

            if do_er:
                progress.update(task, description=f"[cyan]Compiling {year} Examiner Reports...")
                if args.er_folder:
                    compile_examiner_reports(
                        syllabus=syllabus,
                        year=year,
                        folder_id=args.er_folder,
                        output_dir=args.output_dir
                    )
                else:
                    progress.console.print(f"[red]Skipping {year} Examiner Reports - no ER folder ID provided.")
                progress.advance(task)

def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(description="Compile Cambridge past papers.")
    parser.add_argument("--syllabus", type=str, default="9609", help="Syllabus code (default: 9609).")
    parser.add_argument("--year", type=int, help="Specify a single year to compile (e.g. 2023).")
    parser.add_argument("--all-years", action="store_true", help="Compile for all years (2016-2025).")
    parser.add_argument("--components", nargs="+", type=str, help="Specify components to compile (e.g. 1 2 3 4).")
    parser.add_argument("--all-components", action="store_true", help="Compile all components (1-4).")
    parser.add_argument("--examiner-reports", action="store_true", help="Compile examiner reports.")
    parser.add_argument("--cache-dir", type=str, default=".cache/drive_cache", help="Directory for caching downloaded files.")
    parser.add_argument("--output-dir", type=str, default="output", help="Directory for compiled output.")

    # Folder arguments
    parser.add_argument("--series-m", type=str, help="Google Drive folder ID for Feb/March series.")
    parser.add_argument("--series-s", type=str, help="Google Drive folder ID for May/June series.")
    parser.add_argument("--series-w", type=str, help="Google Drive folder ID for Oct/Nov series.")
    parser.add_argument("--series-y", type=str, help="Google Drive folder ID for Specimen series.")
    parser.add_argument("--er-folder", type=str, help="Google Drive folder ID for Examiner Reports.")

    # If no arguments provided, we will launch interactive TUI
    if not argv:
        run_tui()
    else:
        args = parser.parse_args(argv)
        run_headless(args)

def run_tui():
    print("Welcome to the Cambridge Past Paper Compiler!")

    # 1. Ask for years
    year_choices = [str(y) for y in range(2016, 2026)]
    selected_years = questionary.checkbox(
        "Select examination years to compile:",
        choices=year_choices
    ).ask()

    if not selected_years:
        print("No years selected. Exiting.")
        return

    # 2. Ask for compilation targets
    target_choices = [
        "Component 1",
        "Component 2",
        "Component 3",
        "Component 4",
        "Examiner Reports"
    ]
    selected_targets = questionary.checkbox(
        "Select compilation targets:",
        choices=target_choices
    ).ask()

    if not selected_targets:
        print("No targets selected. Exiting.")
        return

    # Map targets to components
    components = []
    do_er = False
    for target in selected_targets:
        if target.startswith("Component"):
            components.append(target.split(" ")[1])
        elif target == "Examiner Reports":
            do_er = True

    # Ask for syllabus
    syllabus = questionary.text("Enter syllabus code (e.g. 9609):", default="9609").ask()
    if not syllabus:
        return

    output_dir = questionary.text("Enter output directory:", default="output").ask() or "output"

    series_folders = {}
    if components:
        print("\n[Components require Google Drive folder IDs for the series]")
        m_id = questionary.text("Folder ID for Feb/March (leave blank if none):").ask()
        if m_id: series_folders["Feb/March"] = m_id

        s_id = questionary.text("Folder ID for May/June (leave blank if none):").ask()
        if s_id: series_folders["May/June"] = s_id

        w_id = questionary.text("Folder ID for Oct/Nov (leave blank if none):").ask()
        if w_id: series_folders["Oct/Nov"] = w_id

        y_id = questionary.text("Folder ID for Specimen (leave blank if none):").ask()
        if y_id: series_folders["Specimen"] = y_id

    er_folder_id = None
    if do_er:
        print("\n[Examiner Reports require a Google Drive folder ID]")
        er_folder_id = questionary.text("Folder ID for Examiner Reports:").ask()

    # Call compiler logic
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Compiling papers...", total=len(selected_years) * (len(components) + (1 if do_er else 0)))

        for year in selected_years:
            for comp in components:
                progress.update(task, description=f"[cyan]Compiling {year} Component {comp}...")
                if series_folders:
                    compile_component(
                        syllabus=syllabus,
                        year=year,
                        component=comp,
                        series_folders=series_folders,
                        output_dir=output_dir
                    )
                else:
                    progress.console.print(f"[red]Skipping {year} Component {comp} - no series folder IDs provided.")
                progress.advance(task)

            if do_er:
                progress.update(task, description=f"[cyan]Compiling {year} Examiner Reports...")
                if er_folder_id:
                    compile_examiner_reports(
                        syllabus=syllabus,
                        year=year,
                        folder_id=er_folder_id,
                        output_dir=output_dir
                    )
                else:
                    progress.console.print(f"[red]Skipping {year} Examiner Reports - no ER folder ID provided.")
                progress.advance(task)
