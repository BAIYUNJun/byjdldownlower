# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

Two implementations of the same DengLin deployment package downloader:

1. **`download_packages.sh`** — Bash CLI script for Linux/macOS, uses lftp or sftp+expect (legacy)
2. **`downloader/`** — Python PyQt6 desktop app, uses paramiko (primary)

Both connect to the same SFTP server, list SDK versions, filter packages by architecture/OS, and batch-download matching files.

## Running

```bash
# PyQt6 app (primary)
pip install -r requirements.txt
PYTHONPATH=. python3 downloader/main.py

# Shell script (Linux/macOS, legacy)
./download_packages.sh              # interactive
./download_packages.sh --dry-run    # list matches only
```

**Note:** Python 3.9+ required. All `.py` files use `from __future__ import annotations` for PEP 604 union syntax compatibility.

## Dependencies

- PyQt6 >= 6.6.0
- paramiko >= 3.4.0

## Packaging

```bash
# macOS .app (arm64)
python3 -m PyInstaller build/DengLin下载工具.spec --clean -y

# Windows .exe
pyinstaller --onefile --windowed --name "登临部署包下载工具" --distpath ./dist --workpath ./build --specpath ./build downloader/main.py
```

## Development Commands

```bash
# Syntax check (no automated tests exist)
python3 -m py_compile downloader/<file>.py
```

## Architecture

### Shell script (`download_packages.sh`)

Single-file program with two SFTP backends: **lftp** (preferred) and **sftp+expect** (fallback). Not actively developed.

### PyQt6 app (`downloader/`)

**4-page wizard** managed by `QStackedWidget` in `ui/wizard.py` with a step indicator bar:

| Index | Page | File | Role |
|-------|------|------|------|
| 0 | Welcome | `ui/welcome_page.py` | SFTP credentials input (username/password + remember via QSettings) |
| 1 | Config | `ui/config_page.py` | Release type toggle + arch cards + OS cards + SDK version combo |
| 2 | Mode Selection | `ui/mode_selection_page.py` | Preset buttons / dynamic file checkboxes + component checkboxes |
| 3 | Download | `ui/download_page.py` | Matched file list, save dir picker, progress bars, log |

**Two release modes** controlled by a toggle on the config page:

- **Standard release** (default): Version dropdown shows `V2 General release/<version>` entries. User selects arch + OS + version → mode selection page shows preset buttons and 8 fixed category checkboxes → download page fetches files via `FetchFilesWorker` and filters by category/arch/OS.
- **Custom release**: Version dropdown shows root-level folders (excluding `V2 General release` / `V1 General release`). No arch/OS selection needed → mode selection page hides presets, fetches folder contents via `FetchCustomFilesWorker` and generates a checkbox per file → download page downloads checked files directly.

The release type toggle is **auto-hidden** if no custom folders exist on the server (detected on first entry to config page via `FetchCustomFoldersWorker`).

**Wizard state flow** — `WizardWindow` stores `_username`, `_password`, `_selected_arch`, `_selected_version`, `_selected_os`, `_release_type` and passes them through `on_enter()` calls when navigating between pages. The `next_clicked` signal chain is 4-string for config→mode (`arch, version, os, release_type`) and dict for mode→download (`mode_config`).

**Async via QThread** — `workers.py` contains five worker threads: `FetchVersionsWorker`, `FetchFilesWorker`, `FetchCustomFoldersWorker`, `FetchCustomFilesWorker`, `DownloadWorker`. Each creates its own SFTPClient, connects, does work, disconnects. No connection pooling. UI communicates with workers via Qt signals/slots only.

**Data flow:**
```
Standard release:
  config_page(arch, version, os, "standard")
    → mode_selection_page(presets + fixed categories)
    → download_page(FetchFilesWorker → filter → download)

Custom release:
  config_page("", folder, "", "custom")
    → mode_selection_page(FetchCustomFilesWorker → dynamic checkboxes)
    → download_page(direct download with is_custom=True)
```

## Config System (`downloader/config.py`)

- `SFTP_HOST/PORT/USER/PASS` — connection defaults (overridden by user input at runtime)
- `CUSTOM_CATEGORIES` — dict of download categories, each with `subdir`, `arch_filter`, `os_filter`, optional `name_filter`. Controls what files are matched in standard release mode.
- `PRESETS` — quick-select buttons that auto-check categories. "测试 CV" includes `cuda11` linked to SDK.
- `OS_OPTIONS` — available OS choices. `OS_DISABLED_CATEGORIES` defines which categories are disabled for Windows/CentOS.
- `SUB_DIRS` — remote subdirectories to scan during standard release file listing.
- `REMOTE_BASE_DIR` — `"/V2 General release"`, the parent directory for standard release versions.
- `ARCH_PATTERNS` — **dead code**, not imported anywhere. Actual matching uses `_matches_arch()` / `_matches_os()` in `sftp_client.py`.

## File Matching Logic (`downloader/sftp_client.py`)

### Standard release

`filter_custom(file_list, arch, selected_categories, os_name)` applies filters in order per category:
1. Subdirectory prefix match
2. Name keyword match (`name_filter` in config)
3. Architecture match (`_matches_arch` — x86/arm64/aarch64 in filename). **Windows files skip this filter**.
4. OS match (`_matches_os` — "linux"/"win"/"centos" in filename)

### Custom release

`get_custom_folders()` lists root `/` directories, excludes `V2/V1 General release`, returns only directories. `get_custom_files(folder)` lists files in a custom folder root (no recursion, no filtering).

### Download path construction

`download_file(is_custom=False)` uses `{REMOTE_BASE_DIR}/{version}/{path}` for standard and `/{version}/{path}` for custom. Files already present locally with matching size are **skipped** (not true resume — no partial transfer).

## UI Patterns

- **Card buttons** (`ArchCardButton`, `OsCardButton`) — checkable QPushButtons with blue border `#4A90D9` + light blue bg `#E8F0FE` when checked. Must connect `toggled` signal to `_update_style()` for Qt internal state changes.
- **Preset buttons** — checkable QPushButtons in a QButtonGroup (exclusive). Auto-update checkboxes via `_on_preset_clicked`.
- **SDK ↔ cuda11 linkage** — `mode_selection_page.py` connects SDK checkbox `toggled` to auto-check cuda11. Uses `_auto_updating` flag to prevent recursive triggers.
- **Global stylesheet** in `main.py` — QComboBox must include `QAbstractItemView` styling for dropdown visibility.
- **Window title:** "登临部署包下载工具V0.1"
- **Config page uses QScrollArea** — content wrapped in scroll area to handle varying content height (release type toggle may be hidden). The scroll area must override global stylesheet with `border: none; background: transparent;` to remove gray border.
- **Font fallback** — `QFont("Microsoft YaHei", ...)` is used throughout; falls back to system font on macOS (PingFang SC via global stylesheet). The log box uses `QFont("Consolas", 10)` which falls back to Menlo on macOS.

## Credential Persistence (`downloader/credentials.py`)

Uses `QSettings("DengLin", "vLLMDownloader")` with organization/app name set in `main.py`. Plaintext storage — no encryption. On macOS stores to `~/Library/Preferences/com.DengLin.vLLMDownloader.plist`.

## Development Notes

- No automated tests or linting configured
- SFTP credentials are hardcoded as defaults in `config.py` but overridden by user input at runtime
- The shell script is legacy; all new features go into the PyQt6 app
- `QCoreApplication.setOrganizationName("DengLin")` and `setApplicationName("vLLMDownloader")` must be called before any QSettings usage
- All UI text is in Chinese (简体中文)
- **Known bug in `download_page.py`**: `_on_overall_progress` and `_on_file_completed` are each defined twice (lines ~343/353 and ~347/357). Python uses the last definition, so the per-file speed-tracking resets in the first `_on_file_completed` are dead code. This causes the download speed display to drift (cumulative instead of per-file).
