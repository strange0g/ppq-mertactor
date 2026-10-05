import pytest
from unittest.mock import patch, MagicMock
from ppq_mertactor import cli

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_root_folder_crawling(mock_pipeline):
    """Test running the CLI headlessly with root folder discovery."""
    args = ["--all-years", "--all-components", "--root-folder", "custom_root_id"]

    with patch("ppq_mertactor.cli.crawl_tree") as mock_crawl:
        mock_crawl.return_value = {"2023": {"m": {"file.pdf": "id"}}}
        with patch("ppq_mertactor.cli.questionary"):
            cli.main(args)

    mock_crawl.assert_called_once_with("custom_root_id")
    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    # Check that the tree was passed
    assert call_kwargs.get("tree") == {"2023": {"m": {"file.pdf": "id"}}} or mock_pipeline.call_args[0][5] == {"2023": {"m": {"file.pdf": "id"}}}

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_components(mock_pipeline):
    """Test running the CLI headlessly with specific components and year."""
    # We will pass arguments that simulate `python -m ppq_mertactor --year 2023 --components 1 2`
    args = ["--year", "2023", "--components", "1", "2", "--series-m", "id1"]

    # We will mock questionary so it doesn't run, even though it shouldn't be called if headless args are passed
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    # Check that compile_component was called correctly
    assert mock_pipeline.call_count == 1

    # Verify the calls
    call_kwargs = mock_pipeline.call_args[1]

    assert call_kwargs.get('years') == ["2023"] or mock_pipeline.call_args[0][0] == ["2023"]
    assert call_kwargs.get('components') == ["1", "2"] or mock_pipeline.call_args[0][1] == ["1", "2"]

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_examiner_reports(mock_pipeline):
    """Test running the CLI headlessly for examiner reports."""
    args = ["--year", "2022", "--examiner-reports", "--er-folder", "id2"]

    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get('do_er') is True or mock_pipeline.call_args[0][2] is True

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_all_components(mock_pipeline):
    """Test running the CLI headlessly with --all-components."""
    args = ["--year", "2023", "--all-components", "--series-m", "id1"]

    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get('components') == ["1", "2", "3", "4"] or mock_pipeline.call_args[0][1] == ["1", "2", "3", "4"]

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_all_years(mock_pipeline):
    """Test running the CLI headlessly with --all-years."""
    args = ["--all-years", "--examiner-reports", "--er-folder", "id2"]

    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    expected_years = [str(y) for y in range(2016, 2026)]
    assert call_kwargs.get('years') == expected_years or mock_pipeline.call_args[0][0] == expected_years

@patch("ppq_mertactor.cli.questionary")
@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_tui_select_all_years(mock_pipeline, mock_questionary):
    """Test TUI 'Select All' functionality."""
    args = []

    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox

    mock_text = MagicMock()
    mock_questionary.text.return_value = mock_text

    # We select "Select All"
    mock_checkbox.ask.side_effect = [
        ["Select All", "2021"], # years (Select All should override other selections)
        ["Component 1"]         # targets
    ]

    mock_text.ask.side_effect = [
        "9609",    # syllabus
        "output",  # output
    ]

    with patch("ppq_mertactor.cli.crawl_tree") as mock_crawl:
        mock_crawl.return_value = {} # Mock tree
        cli.main(args)

    assert mock_pipeline.call_count == 1
    # Check that all years 2016-2025 were passed to the pipeline
    call_kwargs = mock_pipeline.call_args[1]
    expected_years = [str(y) for y in range(2016, 2026)]
    assert call_kwargs.get('years') == expected_years or mock_pipeline.call_args[0][0] == expected_years

@patch("ppq_mertactor.cli.run_compilation_pipeline")
@patch("ppq_mertactor.cli.questionary")
def test_interactive_tui(mock_questionary, mock_pipeline):
    """Test running the CLI interactively with questionary."""
    args = []

    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox

    mock_text = MagicMock()
    mock_questionary.text.return_value = mock_text

    mock_text.ask.side_effect = [
        "9609",    # syllabus
        "output",  # output
    ]

    mock_checkbox.ask.side_effect = [
        ["2021", "2022"], # years
        ["Component 1", "Examiner Reports"] # targets
    ]

    with patch("ppq_mertactor.cli.crawl_tree") as mock_crawl:
        mock_crawl.return_value = {} # Mock tree
        cli.main(args)

    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get('years') == ["2021", "2022"] or mock_pipeline.call_args[0][0] == ["2021", "2022"]
    assert call_kwargs.get('components') == ["1"] or mock_pipeline.call_args[0][1] == ["1"]
    assert call_kwargs.get('do_er') is True or mock_pipeline.call_args[0][2] is True

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_invalid_year_format(mock_pipeline):
    """Test invalid year format triggers SystemExit."""
    args = ["--year", "abc", "--components", "1"]
    with pytest.raises(SystemExit):
        cli.main(args)
    assert mock_pipeline.call_count == 0

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_missing_arguments(mock_pipeline):
    """Test missing targets or missing years skips correctly."""
    # Years but no targets
    args = ["--year", "2023"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_pipeline.call_count == 0

    # Targets but no years
    args = ["--components", "1", "--examiner-reports", "--er-folder", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_pipeline.call_count == 0

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_output_dir_override(mock_pipeline):
    """Test overriding output directory."""
    args = ["--year", "2023", "--components", "1", "--series-m", "id1", "--output-dir", "/custom/path"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get('output_dir') == "/custom/path" or mock_pipeline.call_args[0][4] == "/custom/path"

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.crawl_tree")
def test_missing_series_folders(mock_crawl, mock_comp):
    """Test that missing series folders skips component compilation."""
    args = ["--year", "2023", "--components", "1"]
    mock_crawl.return_value = {} # Mock tree to simulate no folders found
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_comp.call_count == 0

@patch("ppq_mertactor.cli.compile_examiner_reports")
@patch("ppq_mertactor.cli.crawl_tree")
def test_missing_er_folder(mock_crawl, mock_er):
    """Test that missing er-folder skips examiner reports compilation."""
    args = ["--year", "2023", "--examiner-reports"]
    mock_crawl.return_value = {} # Mock tree to simulate no folders found
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_er.call_count == 0

def test_cache_dir_override():
    """Test cache dir override."""
    import os
    args = ["--year", "2023", "--cache-dir", "/my/cache"]
    # We shouldn't need to patch questionary for this if we just check environ
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert os.environ.get("DRIVE_CACHE_DIR") == "/my/cache"

@patch("ppq_mertactor.cli.questionary")
def test_tui_no_years_selected(mock_questionary):
    """Test TUI with no years selected."""
    args = []
    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox
    mock_checkbox.ask.side_effect = [[]] # No years

    with patch("ppq_mertactor.cli.run_compilation_pipeline") as mock_pipeline:
        cli.main(args)
        assert mock_pipeline.call_count == 0

@patch("ppq_mertactor.cli.questionary")
def test_tui_no_targets_selected(mock_questionary):
    """Test TUI with no targets selected."""
    args = []
    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox
    mock_checkbox.ask.side_effect = [["2023"], []] # Years, but no targets

    with patch("ppq_mertactor.cli.run_compilation_pipeline") as mock_pipeline:
        cli.main(args)
        assert mock_pipeline.call_count == 0

@patch("ppq_mertactor.cli.questionary")
def test_tui_missing_syllabus(mock_questionary):
    """Test TUI with missing syllabus (returns empty)."""
    args = []
    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox
    mock_checkbox.ask.side_effect = [["2023"], ["Component 1"]]

    mock_text = MagicMock()
    mock_questionary.text.return_value = mock_text
    mock_text.ask.side_effect = [""] # Empty syllabus

    with patch("ppq_mertactor.cli.run_compilation_pipeline") as mock_pipeline:
        cli.main(args)
        assert mock_pipeline.call_count == 0


@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_all_years_all_components(mock_pipeline):
    """Test passing both --all-years and --all-components."""
    args = ["--all-years", "--all-components", "--series-m", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    expected_years = [str(y) for y in range(2016, 2026)]
    assert call_kwargs.get('years') == expected_years or mock_pipeline.call_args[0][0] == expected_years
    assert call_kwargs.get('components') == ["1", "2", "3", "4"] or mock_pipeline.call_args[0][1] == ["1", "2", "3", "4"]

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_year_and_all_years(mock_pipeline):
    """Test passing both --year and --all-years."""
    args = ["--year", "2023", "--all-years", "--components", "1", "--series-m", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    # --all-years takes precedence
    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    expected_years = [str(y) for y in range(2016, 2026)]
    assert call_kwargs.get('years') == expected_years or mock_pipeline.call_args[0][0] == expected_years

@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_headless_components_and_all_components(mock_pipeline):
    """Test passing both --components and --all-components."""
    args = ["--year", "2023", "--components", "1", "--all-components", "--series-m", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    # --all-components takes precedence
    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get('components') == ["1", "2", "3", "4"] or mock_pipeline.call_args[0][1] == ["1", "2", "3", "4"]

@patch("ppq_mertactor.cli.questionary")
@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_tui_select_all_alone(mock_pipeline, mock_questionary):
    """Test TUI 'Select All' functionality when selected alone."""
    args = []

    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox

    mock_text = MagicMock()
    mock_questionary.text.return_value = mock_text

    # We select only "Select All"
    mock_checkbox.ask.side_effect = [
        ["Select All"],         # years
        ["Component 1"]         # targets
    ]

    mock_text.ask.side_effect = [
        "9609",    # syllabus
        "output",  # output
    ]

    with patch("ppq_mertactor.cli.crawl_tree") as mock_crawl:
        mock_crawl.return_value = {} # Mock tree
        cli.main(args)

    assert mock_pipeline.call_count == 1
    # Check that all years 2016-2025 were passed to the pipeline
    call_kwargs = mock_pipeline.call_args[1]
    expected_years = [str(y) for y in range(2016, 2026)]
    assert call_kwargs.get('years') == expected_years or mock_pipeline.call_args[0][0] == expected_years

@patch("ppq_mertactor.cli.compile_component")
def test_partial_year_failures(mock_compile):
    """Test partial year failures where one year has folders and another does not."""
    tree = {
        "2023": {
            "m": {"_folder_id": "id_2023_m"}
        },
        "2022": {} # missing folders
    }

    with patch("rich.console.Console.print") as mock_print:
        cli.run_compilation_pipeline(
            years=["2023", "2022"],
            components=["1"],
            do_er=False,
            syllabus="9609",
            output_dir="output",
            tree=tree
        )

    # 2023 should compile
    assert mock_compile.call_count == 1
    call_kwargs = mock_compile.call_args[1]
    assert call_kwargs.get('year') == "2023" or mock_compile.call_args[0][1] == "2023"

    # 2022 should print skipping message
    mock_print.assert_any_call("[red]Skipping 2022 Component 1 - no series folder IDs provided.")

@patch("ppq_mertactor.cli.Progress")
def test_download_byte_progress_updates(mock_progress_class):
    """Test the progress callback in run_compilation_pipeline updates download byte counts."""
    mock_progress = MagicMock()
    mock_progress_class.return_value.__enter__.return_value = mock_progress

    # We will trigger the callback via a mocked compile_component
    with patch("ppq_mertactor.cli.compile_component") as mock_compile:
        # Define a side_effect that calls the callback
        def side_effect(*args, **kwargs):
            cb = kwargs.get('progress_callback')
            # 1. total_bytes = 0 (should do nothing)
            cb(chunk_size=1024, total_bytes=0)
            # 2. Start a new task
            cb(chunk_size=1024, total_bytes=2048)
            # 3. Complete the task
            cb(chunk_size=1024, total_bytes=2048)

        mock_compile.side_effect = side_effect

        # Setup mock tasks for the callback logic
        task_id = 1
        mock_progress.add_task.return_value = task_id
        task_obj = MagicMock()
        task_obj.total = 2048
        # We simulate the task completion
        task_obj.completed = 2048
        mock_progress._tasks = {task_id: task_obj}

        cli.run_compilation_pipeline(
            years=["2023"],
            components=["1"],
            do_er=False,
            syllabus="9609",
            output_dir="output",
            default_series_folders={"m": "id1"}
        )

    mock_progress.add_task.assert_any_call("[green]Downloading...", total=2048)
    mock_progress.update.assert_any_call(task_id, advance=1024)
    mock_progress.remove_task.assert_called_with(task_id)

@patch("ppq_mertactor.cli.run_compilation_pipeline")
@patch("ppq_mertactor.cli.crawl_tree")
def test_headless_root_folder_crawling_failure(mock_crawl, mock_pipeline):
    """Test running the CLI headlessly gracefully handles root folder crawling failures."""
    args = ["--all-years", "--all-components", "--root-folder", "custom_root_id"]

    mock_crawl.side_effect = Exception("Network Error")

    with patch("builtins.print") as mock_print:
        with patch("ppq_mertactor.cli.questionary"):
            cli.main(args)

    mock_print.assert_any_call("Failed to crawl root folder: Network Error")
    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("tree") is None or mock_pipeline.call_args[0][5] is None

@patch("ppq_mertactor.cli.questionary")
@patch("ppq_mertactor.cli.run_compilation_pipeline")
def test_tui_select_all_with_individual_years(mock_pipeline, mock_questionary):
    """Test TUI 'Select All' functionality when selected alongside individual years."""
    args = []

    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox

    mock_text = MagicMock()
    mock_questionary.text.return_value = mock_text

    # We select "Select All" and "2022"
    mock_checkbox.ask.side_effect = [
        ["Select All", "2022"], # years
        ["Component 1"]         # targets
    ]

    mock_text.ask.side_effect = [
        "9609",    # syllabus
        "output",  # output
    ]

    with patch("ppq_mertactor.cli.crawl_tree") as mock_crawl:
        mock_crawl.return_value = {} # Mock tree
        cli.main(args)

    assert mock_pipeline.call_count == 1
    # Check that all years 2016-2025 were passed to the pipeline
    call_kwargs = mock_pipeline.call_args[1]
    expected_years = [str(y) for y in range(2016, 2026)]
    assert call_kwargs.get('years') == expected_years or mock_pipeline.call_args[0][0] == expected_years

@patch("ppq_mertactor.cli.run_compilation_pipeline")
@patch("ppq_mertactor.cli.crawl_tree")
def test_headless_root_folder_crawling_success(mock_crawl, mock_pipeline):
    """Test running the CLI headlessly successfully crawls the root folder."""
    args = ["--all-years", "--all-components", "--root-folder", "custom_root_id"]

    mock_crawl.return_value = {"2023": {"m": {"file.pdf": "id"}}}

    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    mock_crawl.assert_called_once_with("custom_root_id")
    assert mock_pipeline.call_count == 1
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("tree") == {"2023": {"m": {"file.pdf": "id"}}} or mock_pipeline.call_args[0][5] == {"2023": {"m": {"file.pdf": "id"}}}
