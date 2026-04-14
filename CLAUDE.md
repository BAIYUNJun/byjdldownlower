# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

## Architecture

### Shell script (`download_packages.sh`)

Single-file program with two SFTP backends: **lftp** (preferred) and **sftp+expect** (fallback). Not actively developed.

### PyQt6 app (`downloader/`)

**4-page wizard** managed by `QStackedWidget` in `ui/wizard.py` with a step indicator bar:

| Index | Page | File | Role |
|-------|------|------|------|
| 0 | Welcome | `ui/welcome_page.py` | SFTP credentials input (username/password + remember via QSettings) |
| 1 | Config | `ui/config_page.py` | Architecture cards + OS cards + SDK version combo (fetched async) |
| 2 | Mode Selection | `ui/mode_selection_page.py` | Preset buttons (测试vLLM/测试CV/其他) + 8 component checkboxes |
| 3 | Download | `ui/download_page.py` | Matched file list, save dir picker, progress bars, log |

**Data flow:**
```
credentials.py (QSettings) ←→ welcome_page.py (user input)
config.py (categories/presets) → sftp_client.py (filter_custom) → workers.py (QThread) → UI pages (signals/slots)
```

**Async via QThread** — `workers.py` contains three worker threads (FetchVersionsWorker, FetchFilesWorker, DownloadWorker). Each creates its own SFTPClient, connects, does work, disconnects. No connection pooling. UI communicates with workers via Qt signals/slots only.

**Wizard state flow** — `WizardWindow` stores `_username`, `_password`, `_selected_arch`, `_selected_version`, `_selected_os` and passes them through `on_enter()` calls when navigating between pages.

## Config System (`downloader/config.py`)

- `CUSTOM_CATEGORIES` — dict of download categories, each with `subdir`, `arch_filter`, `os_filter`, optional `name_filter`. Controls what files are matched.
- `PRESETS` — quick-select buttons that auto-check categories. "测试 CV" includes `cuda11` linked to SDK.
- `OS_OPTIONS` — available OS choices. `OS_DISABLED_CATEGORIES` defines which categories are disabled for Windows/CentOS (container/image types).
- `SUB_DIRS` — all remote subdirectories to scan during file listing.

## File Matching Logic (`downloader/sftp_client.py`)

`filter_custom(file_list, arch, selected_categories, os_name)` applies filters in order per category:
1. Subdirectory prefix match
2. Name keyword match (`name_filter` in config)
3. Architecture match (`_matches_arch` — x86/arm64/aarch64 in filename). **Windows files skip this filter** since Windows filenames lack arch indicators.
4. OS match (`_matches_os` — "linux"/"win"/"centos" in filename)

**FTP file naming conventions:**
- Linux driver: `denglin-driver-v2-X.Y.Z-manylinux_2_28-x86_64.tar.xz`
- Windows driver: `denglin-driver-v2-X.Y.Z-windows.zip`
- Linux SDK: `denglin-sdk-MR-X.X-TIMESTAMP-manylinux_2_28-x86_64.tar.xz`
- Windows SDK: `denglin-sdk-MR-X.X-TIMESTAMP-win.zip`
- cuda11: `cuda11.tar` (version root directory, cross-platform)

## UI Patterns

- **Card buttons** (`ArchCardButton`, `OsCardButton`) — checkable QPushButtons with blue border `#4A90D9` + light blue bg `#E8F0FE` when checked. Must connect `toggled` signal to `_update_style()` for Qt internal state changes.
- **Preset buttons** — checkable QPushButtons in a QButtonGroup (exclusive). Auto-update checkboxes via `_on_preset_clicked`.
- **SDK ↔ cuda11 linkage** — `mode_selection_page.py` connects SDK checkbox `toggled` to auto-check cuda11. Uses `_auto_updating` flag to prevent recursive triggers.
- **Global stylesheet** in `main.py` — QComboBox must include `QAbstractItemView` styling for dropdown visibility.
- **Window title:** "登临部署包下载工具V0.1"

## Credential Persistence (`downloader/credentials.py`)

Uses `QSettings("DengLin", "vLLMDownloader")` with organization/app name set in `main.py`. Plaintext storage — no encryption.

## Packaging for Windows

```bash
pyinstaller --onefile --windowed --name "登临部署包下载工具" --distpath ./dist --workpath ./build --specpath ./build downloader/main.py
```

## Development Commands

```bash
# Syntax check (no automated tests exist)
python3 -m py_compile downloader/<file>.py

# Install dependencies
pip install -r requirements.txt

# Run app
PYTHONPATH=. python3 downloader/main.py
```

## Development Notes

- No automated tests or linting configured
- SFTP credentials are hardcoded as defaults in `config.py` (lines 5-6) but overridden by user input at runtime
- The shell script is legacy; all new features go into the PyQt6 app
- `QCoreApplication.setOrganizationName("DengLin")` and `setApplicationName("vLLMDownloader")` must be called before any QSettings usage
