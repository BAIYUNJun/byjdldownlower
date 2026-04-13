# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Two implementations of the same DengLin vLLM deployment package downloader:

1. **`download_packages.sh`** — Bash CLI script for Linux/macOS, uses lftp or sftp+expect
2. **`downloader/`** — Python PyQt6 desktop app for Windows, uses paramiko

Both connect to the same SFTP server, list SDK versions, filter packages by architecture, and batch-download matching tarballs.

## Running

```bash
# Shell script (Linux/macOS)
./download_packages.sh              # interactive
./download_packages.sh --dry-run    # list matches only

# PyQt6 app (Windows/macOS)
pip install -r requirements.txt
python downloader/main.py
```

## Dependencies

- PyQt6 >= 6.6.0
- paramiko >= 3.4.0

## Architecture

### Shell script (`download_packages.sh`)

Single-file program with two SFTP backends: **lftp** (preferred, single connection) and **sftp+expect** (fallback, fragile prompt parsing). Flow: select architecture → detect tools → `select_sdk_version()` fetches versions from `/V2 General release/` → glob-to-regex conversion → `filter_matches()` → batch download.

Key detail: `get_available_versions()` writes to a temp file to avoid expect deadlocks from command substitution.

### PyQt6 app (`downloader/`)

**Wizard pattern** — three pages managed by `QStackedWidget` in `ui/wizard.py` with a step indicator bar:

| Page | File | Role |
|------|------|------|
| Welcome | `ui/welcome_page.py` | Tool name, server info, start button |
| Config | `ui/config_page.py` | Architecture card buttons + version combo box (fetched async) |
| Download | `ui/download_page.py` | Matched file list, save dir picker, progress bars, log |

**Async via QThread** — `workers.py` contains three worker threads:
- `FetchVersionsWorker` — connects, lists versions, emits `success(list)` or `error(str)`
- `FetchFilesWorker` — lists + filters files for chosen version/arch
- `DownloadWorker` — downloads files sequentially, emits per-file and overall progress

All network I/O goes through `sftp_client.py` which wraps paramiko. UI pages communicate with workers via Qt signals/slots only.

**Data flow:**
```
config.py (constants) → sftp_client.py (paramiko wrapper) → workers.py (QThread) → UI pages (signals/slots)
```

## SFTP Server Details

- Host: `cuftp.denglinai.com:22022`
- Credentials are hardcoded in both `download_packages.sh` and `downloader/config.py`
- Remote base: `/V2 General release`
- Version format: `V2-General_release-YYYYMMDD`
- Known subdirectories: `Base_driver`, `K8s`, `Vllm`, `Vllm0.13.0_product_images`, `vllm`, `driver`, `container`

## File Matching Rules

- **x86**: `*driver*manylinux*x86*.tar*`, `*container*x86*.tar*`, `*vllm*x86*.tar*`
- **arm64**: matches both `arm64` and `aarch64` naming variants

## Packaging for Windows

```bash
pip install pyinstaller
pyinstaller --onefile --windowed downloader/main.py

# Full command with custom output name (recommended):
pyinstaller --onefile --windowed --name "DengLin下载工具" --distpath ./dist --workpath ./build --specpath ./build downloader/main.py
```

## Common Development Commands

```bash
# Check Python syntax without running
python3 -m py_compile downloader/<file>.py

# Or check syntax via ast module
python3 -c "import ast; ast.parse(open('downloader/<file>.py').read()); print('Syntax OK')"

# Install dependencies
pip install -r requirements.txt

# Run the PyQt6 app
python downloader/main.py

# Run the shell script (interactive)
./download_packages.sh

# Run shell script in dry-run mode (list only)
./download_packages.sh --dry-run
```

## Development Notes

- This project has no automated tests or linting configured
- SFTP credentials are hardcoded in both implementations (`download_packages.sh` line 5-8 and `downloader/config.py` line 3-6)
- The shell script uses a temp file approach for `get_available_versions()` to avoid expect deadlocks from command substitution
