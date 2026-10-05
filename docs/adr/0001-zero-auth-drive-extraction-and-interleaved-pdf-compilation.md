# ADR 0001: Zero-Credential Drive Extraction and Interleaved PDF Collation

## Context
Past papers for Cambridge Business (9609) across 2016–2025 are hosted in a public Google Drive folder hierarchy partitioned by year and series. Users need to compile these into single-year revision booklets per component and unified examiner reports per year without requiring Google Cloud API keys, OAuth credentials, or manual downloads.

## Decision
1. **Zero-Credential Direct Fetching**: Extract folder tree metadata and stream PDF downloads directly from Google Drive public endpoints, caching raw PDFs locally under `.cache/drive_cache/`. This avoids requiring Google Cloud API credentials or OAuth setups while remaining fully functional out-of-the-box.
2. **Interleaved Collation Order**: For each component compilation, collate documents strictly in the sequence `[Insert] -> [Question Paper] -> [Mark Scheme]` for each variant in chronological series order (`Feb/March -> May/June -> Oct/Nov`), omitting Grade Thresholds.
3. **Chronological Examiner Reports**: For each year, merge all available series examiner reports into a single consolidated document, annotated with PDF bookmarks for each series.
4. **Interactive TUI**: Implement an interactive terminal interface using `questionary` and `rich` for multi-year and component selection with real-time download and merge progress indicators.
