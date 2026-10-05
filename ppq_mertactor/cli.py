import argparse
import sys
import questionary
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from ppq_mertactor.compiler import compile_component, compile_examiner_reports
from ppq_mertactor.drive import crawl_tree

def run_compilation_pipeline(years, components, do_er, syllabus, output_dir, tree=None, default_series_folders=None, default_er_folder=None):
    if default_series_folders is None:
        default_series_folders = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Compiling papers...", total=len(years) * (len(components) + (1 if do_er else 0)))

        download_task_id = None

        def download_progress_callback(chunk_size, total_bytes):
            nonlocal download_task_id
            if total_bytes == 0:
                return
            if download_task_id is None:
                download_task_id = progress.add_task("[green]Downloading...", total=total_bytes)
            else:
                task_obj = progress._tasks[download_task_id]
                if task_obj.total != total_bytes:
                    progress.update(download_task_id, total=total_bytes, completed=0)

            progress.update(download_task_id, advance=chunk_size)
            task_obj = progress._tasks[download_task_id]
            if task_obj.completed >= task_obj.total:
                progress.remove_task(download_task_id)
                download_task_id = None

        for year in years:
            # Resolve series folders and er folder for this year
            series_folders = default_series_folders.copy()
            er_folder = default_er_folder

            if tree and year in tree:
                year_node = tree[year]
                er_folder = year_node.get('_folder_id', er_folder)

                # Mapping Drive series folder names to Cambridge series names
                series_mapping = {
                    'm': 'Feb/March',
                    's': 'May/June',
                    'w': 'Oct/Nov',
                    'y': 'Specimen'
                }

                for code, name in series_mapping.items():
                    if code in year_node and '_folder_id' in year_node[code]:
                        series_folders[name] = year_node[code]['_folder_id']

            for comp in components:
                progress.update(task, description=f"[cyan]Compiling {year} Component {comp}...")
                if series_folders:
                    compile_component(
                        syllabus=syllabus,
                        year=year,
                        component=comp,
                        series_folders=series_folders,
                        output_dir=output_dir,
                        progress_callback=download_progress_callback
                    )
                else:
                    progress.console.print(f"[red]Skipping {year} Component {comp} - no series folder IDs provided.")
                progress.advance(task)

            if do_er:
                progress.update(task, description=f"[cyan]Compiling {year} Examiner Reports...")
                if er_folder:
                    compile_examiner_reports(
                        syllabus=syllabus,
                        year=year,
                        folder_id=er_folder,
                        output_dir=output_dir,
                        progress_callback=download_progress_callback
                    )
                else:
                    progress.console.print(f"[red]Skipping {year} Examiner Reports - no ER folder ID provided.")
                progress.advance(task)

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

    if not years or (not components and not do_er):
        return

    tree = None
    if not series_folders and not args.er_folder:
        try:
            tree = crawl_tree(args.root_folder)
        except Exception as e:
            print(f"Failed to crawl root folder: {e}")

    run_compilation_pipeline(
        years=years,
        components=components,
        do_er=do_er,
        syllabus=syllabus,
        output_dir=args.output_dir,
        tree=tree,
        default_series_folders=series_folders,
        default_er_folder=args.er_folder
    )

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
    parser.add_argument("--root-folder", type=str, default="1MLOKA_LiWgEbS_XajDifzLtBUFmqJGBM", help="Google Drive Root Folder ID for discovery.")
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
    year_choices = ["Select All"] + [str(y) for y in range(2016, 2026)]
    selected_years = questionary.checkbox(
        "Select examination years to compile:",
        choices=year_choices
    ).ask()

    if not selected_years:
        print("No years selected. Exiting.")
        return

    if "Select All" in selected_years:
        selected_years = [str(y) for y in range(2016, 2026)]

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
    er_folder_id = None
    tree = None

    try:
        print("\n[Discovering root folder to automatically map examination series...]")
        tree = crawl_tree("1MLOKA_LiWgEbS_XajDifzLtBUFmqJGBM")
    except Exception as e:
        print(f"Failed to crawl default root folder: {e}")

    # Call compiler logic
    run_compilation_pipeline(
        years=selected_years,
        components=components,
        do_er=do_er,
        syllabus=syllabus,
        output_dir=output_dir,
        tree=tree,
        default_series_folders=series_folders,
        default_er_folder=er_folder_id
    )
