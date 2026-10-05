import pytest
from unittest.mock import patch, MagicMock
from ppq_mertactor import cli

@patch("ppq_mertactor.cli.compile_component")
def test_headless_components(mock_compile_component):
    """Test running the CLI headlessly with specific components and year."""
    # We will pass arguments that simulate `python -m ppq_mertactor --year 2023 --components 1 2`
    args = ["--year", "2023", "--components", "1", "2", "--series-m", "id1"]

    # We will mock questionary so it doesn't run, even though it shouldn't be called if headless args are passed
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    # Check that compile_component was called correctly
    assert mock_compile_component.call_count == 2

    # Verify the calls
    call_args_list = mock_compile_component.call_args_list

    # It should be called with syllabus "9609" (hardcoded for now maybe, or passed somehow?)
    # For now, let's just check the kwargs 'year' and 'component'
    # Or positionally
    # Assuming signature is compile_component(syllabus, year, component, series_folders, output_dir)
    assert any(kwargs.get('year') == "2023" and kwargs.get('component') == "1" for args, kwargs in call_args_list) or \
           any(args[1] == "2023" and args[2] == "1" for args, kwargs in call_args_list)

@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_headless_examiner_reports(mock_compile_er):
    """Test running the CLI headlessly for examiner reports."""
    args = ["--year", "2022", "--examiner-reports", "--er-folder", "id2"]

    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    assert mock_compile_er.call_count == 1
    call_args, call_kwargs = mock_compile_er.call_args
    # Assuming signature compile_examiner_reports(syllabus, year, folder_id, output_dir)
    if 'year' in call_kwargs:
        assert call_kwargs['year'] == "2022"
    else:
        assert call_args[1] == "2022"

@patch("ppq_mertactor.cli.compile_component")
def test_headless_all_components(mock_compile_component):
    """Test running the CLI headlessly with --all-components."""
    args = ["--year", "2023", "--all-components", "--series-m", "id1"]

    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    # Assuming components are 1, 2, 3, 4
    assert mock_compile_component.call_count == 4

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_headless_all_years(mock_compile_er, mock_compile_component):
    """Test running the CLI headlessly with --all-years."""
    # This might take a while if we test all components across all years, let's just test examiner reports across all years
    args = ["--all-years", "--examiner-reports", "--er-folder", "id2"]

    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)

    # From 2016 to 2025 is 10 years
    assert mock_compile_er.call_count == 10

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
@patch("ppq_mertactor.cli.questionary")
def test_interactive_tui(mock_questionary, mock_compile_er, mock_compile_component):
    """Test running the CLI interactively with questionary."""
    args = []

    # Setup mock for questionary.checkbox().ask()
    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox

    # Sequence of prompts:
    # 1. Syllabus (text)
    # 2. Years (checkbox)
    # 3. Output dir (text)
    # 4. Targets (checkbox)
    # 5. Component m (text)
    # 6. Component s (text)
    # 7. Component w (text)
    # 8. Component y (text)
    # 9. ER folder (text)

    # For text responses:
    # Syllabus: 9609
    # Output: output
    # m, s, w, y: id1, '', '', ''
    # ER: id2

    mock_text = MagicMock()
    mock_questionary.text.return_value = mock_text
    mock_text.ask.side_effect = [
        "9609",    # syllabus
        "output",  # output
        "id1",     # m
        "",        # s
        "",        # w
        "",        # y
        "id2"      # er
    ]

    mock_checkbox.ask.side_effect = [
        ["2021", "2022"], # years
        ["Component 1", "Examiner Reports"] # targets
    ]

    cli.main(args)

    assert mock_compile_component.call_count == 2 # Comp 1 for 2021 and 2022
    assert mock_compile_er.call_count == 2 # ER for 2021 and 2022

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_invalid_year_format(mock_er, mock_comp):
    """Test invalid year format triggers SystemExit."""
    args = ["--year", "abc", "--components", "1"]
    with pytest.raises(SystemExit):
        cli.main(args)
    assert mock_comp.call_count == 0

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_missing_arguments(mock_er, mock_comp):
    """Test missing targets or missing years skips correctly."""
    # Years but no targets
    args = ["--year", "2023"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_comp.call_count == 0
    assert mock_er.call_count == 0

    # Targets but no years
    args = ["--components", "1", "--examiner-reports", "--er-folder", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_comp.call_count == 0
    assert mock_er.call_count == 0

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_output_dir_override(mock_er, mock_comp):
    """Test overriding output directory."""
    args = ["--year", "2023", "--components", "1", "--series-m", "id1", "--output-dir", "/custom/path"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_comp.call_count == 1
    assert mock_comp.call_args[1].get('output_dir') == "/custom/path" or mock_comp.call_args[0][4] == "/custom/path"

@patch("ppq_mertactor.cli.compile_component")
def test_missing_series_folders(mock_comp):
    """Test that missing series folders skips component compilation."""
    args = ["--year", "2023", "--components", "1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    assert mock_comp.call_count == 0

@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_missing_er_folder(mock_er):
    """Test that missing er-folder skips examiner reports compilation."""
    args = ["--year", "2023", "--examiner-reports"]
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

    with patch("ppq_mertactor.cli.compile_component") as mock_comp:
        cli.main(args)
        assert mock_comp.call_count == 0

@patch("ppq_mertactor.cli.questionary")
def test_tui_no_targets_selected(mock_questionary):
    """Test TUI with no targets selected."""
    args = []
    mock_checkbox = MagicMock()
    mock_questionary.checkbox.return_value = mock_checkbox
    mock_checkbox.ask.side_effect = [["2023"], []] # Years, but no targets

    with patch("ppq_mertactor.cli.compile_component") as mock_comp:
        cli.main(args)
        assert mock_comp.call_count == 0

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

    with patch("ppq_mertactor.cli.compile_component") as mock_comp:
        cli.main(args)
        assert mock_comp.call_count == 0


@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_headless_all_years_all_components(mock_er, mock_comp):
    """Test passing both --all-years and --all-components."""
    args = ["--all-years", "--all-components", "--series-m", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    # 10 years * 4 components = 40 component calls
    assert mock_comp.call_count == 40
    assert mock_er.call_count == 0

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_headless_year_and_all_years(mock_er, mock_comp):
    """Test passing both --year and --all-years."""
    args = ["--year", "2023", "--all-years", "--components", "1", "--series-m", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    # --all-years takes precedence
    assert mock_comp.call_count == 10

@patch("ppq_mertactor.cli.compile_component")
@patch("ppq_mertactor.cli.compile_examiner_reports")
def test_headless_components_and_all_components(mock_er, mock_comp):
    """Test passing both --components and --all-components."""
    args = ["--year", "2023", "--components", "1", "--all-components", "--series-m", "id1"]
    with patch("ppq_mertactor.cli.questionary"):
        cli.main(args)
    # --all-components takes precedence
    assert mock_comp.call_count == 4
