#!/usr/bin/env python3
"""登临部署包下载工具 - Linux CLI 版本

复用 downloader 包中的 SFTP 客户端和配置，提供终端交互界面。

用法:
    # 交互模式（逐步引导）
    PYTHONPATH=. python3 dl_cli.py

    # 非交互模式（命令行指定所有参数）
    PYTHONPATH=. python3 dl_cli.py --arch x86 --os linux --preset vllm

    # 仅列出匹配文件
    PYTHONPATH=. python3 dl_cli.py --dry-run --arch x86 --os linux --preset vllm
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import termios
import time
import tty

from downloader.config import (
    CUSTOM_CATEGORIES,
    OS_DISABLED_CATEGORIES,
    OS_OPTIONS,
    PRESETS,
    SFTP_HOST,
    SFTP_PASS,
    SFTP_PORT,
    SFTP_USER,
)
from downloader.sftp_client import SFTPClient


# ============================================================
# 工具函数
# ============================================================

# ANSI 转义码
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"
_REVERSE = "\033[7m"
_CLEAR_LINE = "\033[2K"
_MOVE_UP = "\033[A"
_HIDE_CURSOR = "\033[?25l"
_SHOW_CURSOR = "\033[?25h"


def format_size(n: float) -> str:
    """字节数格式化"""
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def print_banner():
    print("=" * 60)
    print("       登临部署包下载工具 (CLI)")
    print("=" * 60)
    print(f"SFTP 服务器: {SFTP_HOST}:{SFTP_PORT}")
    print()


def print_step(title: str):
    """打印步骤标题"""
    print()
    print(f"--- {title} ---")
    print()


# ============================================================
# 终端交互 - 方向键选择器
# ============================================================

class _TermRaw:
    """终端 raw 模式上下文管理器"""

    def __init__(self):
        self._fd = sys.stdin.fileno()
        self._orig: list | None = None

    def __enter__(self):
        self._orig = termios.tcgetattr(self._fd)
        tty.setraw(self._fd)
        return self

    def __exit__(self, *args):
        if self._orig is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._orig)


def _read_key() -> str:
    """读取一个按键，返回名称标识"""
    fd = sys.stdin.fileno()
    ch = os.read(fd, 1).decode("utf-8", errors="ignore")

    if ch == "\r" or ch == "\n":
        return "enter"
    if ch == " ":
        return "space"
    if ch == "\x03":
        return "ctrl_c"
    if ch == "\x1b":
        # 转义序列：方向键是 \x1b[A / \x1b[B / \x1b[C / \x1b[D
        ch2 = os.read(fd, 1).decode("utf-8", errors="ignore")
        if ch2 == "[":
            ch3 = os.read(fd, 1).decode("utf-8", errors="ignore")
            return {"A": "up", "B": "down", "C": "right", "D": "left"}.get(ch3, "esc")
        return "esc"
    if ch in ("j", "J"):
        return "down"
    if ch in ("k", "K"):
        return "up"
    if ch in ("q", "Q"):
        return "q"
    return ch


def arrow_choice(
    prompt: str,
    options: list[str],
    default: int = 0,
) -> int:
    """方向键单选。返回选中项索引（从 0 开始）。"""
    cursor = default
    n = len(options)

    sys.stdout.write(_HIDE_CURSOR)
    sys.stdout.write(f"  {_BOLD}{prompt}{_RESET}  (↑/↓ 移动, Enter 确认)\n")

    for i, opt in enumerate(options):
        sys.stdout.write(f"    {opt}\n")
    sys.stdout.flush()

    # 将光标移回第一个选项行
    sys.stdout.write(f"\033[{n}A")

    def _render():
        for i in range(n):
            sys.stdout.write(_CLEAR_LINE + "\r")
            if i == cursor:
                sys.stdout.write(f"  {_REVERSE}  {options[i]}  {_RESET}")
            else:
                sys.stdout.write(f"    {options[i]}")
            sys.stdout.write("\033[B")  # 下移一行
        # 回到起始位置
        sys.stdout.write(f"\033[{n}A")
        sys.stdout.flush()

    _render()

    try:
        with _TermRaw():
            while True:
                key = _read_key()
                if key == "ctrl_c":
                    raise KeyboardInterrupt
                if key == "up":
                    cursor = (cursor - 1) % n
                elif key == "down":
                    cursor = (cursor + 1) % n
                elif key == "enter":
                    break
                _render()
    except KeyboardInterrupt:
        sys.stdout.write(f"\033[{n}B\n{_SHOW_CURSOR}")
        sys.stdout.flush()
        print("\n  已取消")
        sys.exit(1)

    # 清除选项，打印最终选择
    sys.stdout.write(f"\033[{n + 1}B\r")  # 移到选项区域下方
    for _ in range(n + 1):
        sys.stdout.write(_CLEAR_LINE + _MOVE_UP + "\r")
    sys.stdout.write(f"  {prompt}: {_CYAN}{options[cursor]}{_RESET}\n")
    sys.stdout.write(_SHOW_CURSOR)
    sys.stdout.flush()
    return cursor


def arrow_multi_choice(
    prompt: str,
    items: list[tuple[str, str]],
) -> list[str]:
    """方向键多选。items 是 [(key, label), ...]，返回选中的 key 列表。"""
    selected: set[str] = set()
    cursor = 0
    n = len(items)

    sys.stdout.write(_HIDE_CURSOR)
    sys.stdout.write(
        f"  {_BOLD}{prompt}{_RESET}  "
        f"(↑/↓ 移动, Space 勾选, Enter 确认, q 取消)\n"
    )

    for _key, label in items:
        sys.stdout.write(f"    [ ] {label}\n")
    sys.stdout.flush()

    sys.stdout.write(f"\033[{n}A")

    def _render():
        for i in range(n):
            key, label = items[i]
            mark = f"{_GREEN}[x]{_RESET}" if key in selected else "[ ]"
            sys.stdout.write(_CLEAR_LINE + "\r")
            if i == cursor:
                sys.stdout.write(f"  {_REVERSE} {mark} {label} {_RESET}")
            else:
                sys.stdout.write(f"    {mark} {label}")
            sys.stdout.write("\033[B")
        sys.stdout.write(f"\033[{n}A")
        sys.stdout.flush()

    _render()

    try:
        with _TermRaw():
            while True:
                key = _read_key()
                if key == "ctrl_c" or key == "q":
                    raise KeyboardInterrupt
                if key == "up":
                    cursor = (cursor - 1) % n
                elif key == "down":
                    cursor = (cursor + 1) % n
                elif key == "space":
                    item_key = items[cursor][0]
                    if item_key in selected:
                        selected.discard(item_key)
                    else:
                        selected.add(item_key)
                elif key == "enter":
                    if selected:
                        break
                    # 至少选一个，闪烁提示
                    pass
                _render()
    except KeyboardInterrupt:
        sys.stdout.write(f"\033[{n}B\n{_SHOW_CURSOR}")
        sys.stdout.flush()
        print("\n  已取消")
        sys.exit(1)

    # 清除选项，打印最终选择
    sys.stdout.write(f"\033[{n}B\r")
    for _ in range(n + 1):
        sys.stdout.write(_CLEAR_LINE + _MOVE_UP + "\r")

    chosen = [items[i][1] for i in range(n) if items[i][0] in selected]
    sys.stdout.write(
        f"  {prompt}: {_CYAN}{', '.join(chosen)}{_RESET}\n"
    )
    sys.stdout.write(_SHOW_CURSOR)
    sys.stdout.flush()
    return list(selected)


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """方向键是/否选择"""
    opts = ["是", "否"]
    default_idx = 0 if default else 1
    idx = arrow_choice(prompt, opts, default=default_idx)
    return idx == 0


# ============================================================
# 进度条
# ============================================================

class ProgressDisplay:
    """终端单行进度显示"""

    def __init__(self, total_files: int):
        self.total_files = total_files
        self.completed = 0
        self._start_time = time.time()
        self._file_start_time = time.time()
        self._last_transferred = 0

    def on_file_progress(self, filename: str, transferred: int, total: int):
        pct = transferred / total * 100 if total > 0 else 0
        elapsed = time.time() - self._file_start_time
        speed = (transferred - self._last_transferred) / elapsed if elapsed > 0.3 else 0

        bar_width = 20
        filled = int(bar_width * transferred / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_width - filled)

        overall_pct = self.completed / self.total_files * 100 if self.total_files > 0 else 0

        line = (
            f"\r  [{bar}] {pct:5.1f}% "
            f"| {self.completed + 1}/{self.total_files} ({overall_pct:.0f}%) "
            f"| {os.path.basename(filename)[:30]} "
            f"| {format_size(speed)}/s"
        )
        sys.stdout.write(f"{line:<80}")
        sys.stdout.flush()

    def on_file_done(self, filename: str):
        self.completed += 1
        elapsed = time.time() - self._start_time
        total_elapsed = format_size(
            self.completed / elapsed if elapsed > 0 else 0
        )
        print(f"\r  ✓ {os.path.basename(filename):<40} ({self.completed}/{self.total_files}){'':>20}")
        self._file_start_time = time.time()
        self._last_transferred = 0

    def done(self):
        elapsed = time.time() - self._start_time
        print(f"\n  全部下载完成！耗时 {elapsed:.1f} 秒")


# ============================================================
# 核心业务流程
# ============================================================

def get_credentials(args: argparse.Namespace) -> tuple[str, str]:
    """获取用户名和密码"""
    username = args.username or ""
    password = args.password or ""

    if not username:
        username = input("用户名: ").strip()
    if not password:
        import getpass
        password = getpass.getpass("密码: ")

    if not username or not password:
        print("错误: 用户名和密码不能为空")
        sys.exit(1)

    return username, password


def detect_release_type(client: SFTPClient, args: argparse.Namespace) -> str:
    """检测并选择发布类型（标准/定制）"""
    if args.release_type:
        return args.release_type

    print_step("检测发布类型")
    try:
        folders = client.get_custom_folders()
    except Exception:
        folders = []

    if not folders:
        print("  未检测到定制发布文件夹，使用标准发布模式")
        return "standard"

    print(f"  检测到 {len(folders)} 个定制发布文件夹:")
    for f in folders[:5]:
        print(f"    - {f}")
    if len(folders) > 5:
        print(f"    ... 共 {len(folders)} 个")

    opts = ["标准发布", "定制发布"]
    idx = arrow_choice("请选择发布类型", opts, default=0)
    return "standard" if idx == 0 else "custom"


def select_arch(args: argparse.Namespace) -> str:
    """选择 CPU 架构"""
    if args.arch:
        return args.arch

    print_step("选择 CPU 架构")
    opts = ["x86_64  (Intel / AMD 64位)", "arm64   (ARM 64位 / aarch64)"]
    idx = arrow_choice("请选择架构", opts, default=0)
    return "x86" if idx == 0 else "arm64"


def select_os(args: argparse.Namespace) -> str:
    """选择操作系统"""
    if args.os:
        return args.os

    print_step("选择操作系统")
    opts = [f"{o['label']}  ({o['desc']})" for o in OS_OPTIONS]
    idx = arrow_choice("请选择操作系统", opts, default=0)
    return OS_OPTIONS[idx]["key"]


def select_version(client: SFTPClient, args: argparse.Namespace) -> str:
    """选择 SDK 版本"""
    if args.version:
        return args.version

    print_step("获取可用版本")
    print("  正在连接服务器获取版本列表...")
    versions = client.get_available_versions()

    if not versions:
        print("  错误: 未找到可用版本")
        sys.exit(1)

    print(f"  找到 {len(versions)} 个版本（最新: {versions[0]}）")

    if prompt_yes_no("是否使用最新版本?", default=True):
        return versions[0]

    opts = versions[:20]  # 最多显示 20 个
    if len(versions) > 20:
        print(f"  （仅显示最近 20 个版本）")
    idx = arrow_choice("请选择版本", opts, default=0)
    return opts[idx]


def select_custom_folder(client: SFTPClient, args: argparse.Namespace) -> str:
    """选择定制发布文件夹"""
    if args.folder:
        return args.folder

    print_step("获取定制发布文件夹")
    print("  正在获取文件夹列表...")
    folders = client.get_custom_folders()

    if not folders:
        print("  错误: 未找到定制发布文件夹")
        sys.exit(1)

    print(f"  找到 {len(folders)} 个定制文件夹:")
    opts = folders[:20]
    idx = arrow_choice("请选择文件夹", opts, default=0)
    return opts[idx]


def select_categories(
    args: argparse.Namespace, os_name: str, preset: str | None = None
) -> list[str]:
    """选择下载组件类别"""
    is_restricted = os_name in ("windows", "centos")

    # 如果命令行指定了预设，直接用
    if preset and preset in PRESETS:
        cats = PRESETS[preset]["categories"]
        if is_restricted:
            cats = [c for c in cats if c not in OS_DISABLED_CATEGORIES]
        print(f"\n  使用预设: {PRESETS[preset]['label']}")
        return cats

    # 如果命令行指定了类别
    if args.categories:
        return args.categories

    print_step("选择下载组件")

    # 先让用户选预设或手动
    preset_opts = ["手动选择组件"] + [cfg["label"] for cfg in PRESETS.values()]
    preset_idx = arrow_choice("快速选择", preset_opts, default=0)

    if preset_idx > 0:
        preset_key = list(PRESETS.keys())[preset_idx - 1]
        cats = PRESETS[preset_key]["categories"]
        if is_restricted:
            cats = [c for c in cats if c not in OS_DISABLED_CATEGORIES]
        print(f"  已选择预设: {PRESETS[preset_key]['label']}")
        return cats

    # 手动多选
    available = []
    for key, cfg in CUSTOM_CATEGORIES.items():
        if is_restricted and key in OS_DISABLED_CATEGORIES:
            continue
        available.append((key, cfg["label"]))

    selected = arrow_multi_choice("请勾选需要下载的组件:", available)

    # SDK ↔ cuda11 联动
    if "sdk" in selected and "cuda11" not in selected:
        if "cuda11" in dict(available):
            selected.append("cuda11")
            print("  注意: 已自动勾选 cuda11（SDK 依赖）")

    return selected


def select_custom_files(
    client: SFTPClient, folder: str, args: argparse.Namespace
) -> list[str]:
    """定制模式：选择要下载的文件"""
    print_step("获取文件列表")
    print(f"  正在获取 {folder} 下的文件列表...")
    files = client.get_custom_files(folder)

    if not files:
        print("  错误: 该文件夹下未找到文件")
        sys.exit(1)

    print(f"  找到 {len(files)} 个文件:")
    for f in files:
        print(f"    - {f}")

    items = [(f, f) for f in files]
    selected = arrow_multi_choice("请勾选要下载的文件:", items)
    return selected


def download_files(
    client: SFTPClient,
    version: str,
    files: list[str],
    save_dir: str,
    is_custom: bool = False,
):
    """下载文件并显示进度"""
    if not files:
        print("  没有可下载的文件")
        return

    os.makedirs(save_dir, exist_ok=True)

    progress = ProgressDisplay(len(files))

    for file_path in files:
        filename = os.path.basename(file_path)

        def progress_cb(transferred: int, total: int, fn=filename):
            progress.on_file_progress(fn, transferred, total)

        try:
            client.download_file(
                file_path,
                save_dir,
                version,
                progress_callback=progress_cb,
                is_custom=is_custom,
            )
        except Exception as e:
            print(f"\n  下载失败 {filename}: {e}")
            continue

        progress.on_file_done(filename)

    progress.done()


# ============================================================
# 主流程
# ============================================================

def run_standard_mode(
    client: SFTPClient, args: argparse.Namespace, preset: str | None
):
    """标准发布模式"""
    arch = select_arch(args)
    os_name = select_os(args)
    version = select_version(client, args)
    categories = select_categories(args, os_name, preset)

    print_step("获取文件列表")
    print(f"  架构: {arch} | 系统: {os_name} | 版本: {version}")
    print(f"  组件: {', '.join(CUSTOM_CATEGORIES[c]['label'] for c in categories)}")
    print("  正在获取远程文件列表...")

    all_files = client.get_remote_file_list(version)
    matches = client.filter_custom(all_files, arch, categories, os_name)

    # 汇总匹配结果
    all_matched: list[str] = []
    for cat_key, files in matches.items():
        label = CUSTOM_CATEGORIES[cat_key]["label"]
        if files:
            print(f"\n  [{label}] 匹配 {len(files)} 个文件:")
            for f in files:
                print(f"    - {os.path.basename(f)}")
        else:
            print(f"\n  [{label}] 无匹配文件")
        all_matched.extend(files)

    print(f"\n  共匹配 {len(all_matched)} 个文件")

    if not all_matched:
        print("\n  警告: 未匹配到任何文件！远程文件列表（前 20 条）:")
        for f in all_files[:20]:
            print(f"    - {f}")
        if not prompt_yes_no("是否仍然继续?", default=False):
            return

    if args.dry_run:
        print("\n  [dry-run 模式] 不执行下载")
        return

    save_dir = args.save_dir or os.path.join(os.getcwd(), f"downloads/{version}")
    if not args.save_dir:
        raw = input(f"\n  保存目录 [{save_dir}]: ").strip()
        if raw:
            save_dir = raw

    if not prompt_yes_no("确认开始下载?", default=True):
        print("  已取消")
        return

    print()
    download_files(client, version, all_matched, save_dir, is_custom=False)
    print(f"\n  文件保存到: {save_dir}")


def run_custom_mode(client: SFTPClient, args: argparse.Namespace):
    """定制发布模式"""
    folder = select_custom_folder(client, args)
    files = select_custom_files(client, folder, args)

    if not files:
        print("  未选择任何文件")
        return

    print(f"\n  已选择 {len(files)} 个文件:")
    for f in files:
        print(f"    - {f}")

    if args.dry_run:
        print("\n  [dry-run 模式] 不执行下载")
        return

    save_dir = args.save_dir or os.path.join(os.getcwd(), f"downloads/{folder}")
    if not args.save_dir:
        raw = input(f"\n  保存目录 [{save_dir}]: ").strip()
        if raw:
            save_dir = raw

    if not prompt_yes_no("确认开始下载?", default=True):
        print("  已取消")
        return

    print()
    download_files(client, folder, files, save_dir, is_custom=True)
    print(f"\n  文件保存到: {save_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="登临部署包下载工具 (CLI)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例:\n"
            "  # 交互模式\n"
            "  PYTHONPATH=. python3 dl_cli.py\n"
            "\n"
            "  # 使用预设快速下载\n"
            "  PYTHONPATH=. python3 dl_cli.py --arch x86 --os linux --preset vllm\n"
            "\n"
            "  # 仅列出匹配文件\n"
            "  PYTHONPATH=. python3 dl_cli.py --dry-run --arch arm64 --os linux --preset cv\n"
            "\n"
            "  # 定制发布模式\n"
            "  PYTHONPATH=. python3 dl_cli.py --release-type custom --folder <文件夹名>\n"
            "\n"
            "可用预设: " + ", ".join(f"{k} ({v['label']})" for k, v in PRESETS.items()) + "\n"
            "可用组件: " + ", ".join(CUSTOM_CATEGORIES.keys()) + "\n"
        ),
    )
    parser.add_argument("--username", "-u", help="SFTP 用户名")
    parser.add_argument("--password", "-p", help="SFTP 密码")
    parser.add_argument("--arch", choices=["x86", "arm64"], help="CPU 架构")
    parser.add_argument("--os", dest="os", choices=["linux", "centos", "windows"], help="操作系统")
    parser.add_argument("--version", "-v", help="SDK 版本名称")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="使用预设模式")
    parser.add_argument(
        "--categories", nargs="+",
        choices=list(CUSTOM_CATEGORIES.keys()),
        help="手动指定下载组件类别",
    )
    parser.add_argument(
        "--release-type", choices=["standard", "custom"],
        dest="release_type", help="发布类型",
    )
    parser.add_argument("--folder", help="定制发布文件夹名称")
    parser.add_argument("--save-dir", dest="save_dir", help="下载保存目录")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="仅列出匹配的文件，不实际下载",
    )

    args = parser.parse_args()

    print_banner()

    # 1. 获取凭据
    username, password = get_credentials(args)

    # 2. 连接 SFTP
    print("\n正在连接服务器...")
    client = SFTPClient(username, password)
    try:
        client.connect()
        print("连接成功！")

        # 3. 选择发布类型
        release_type = detect_release_type(client, args)

        if release_type == "custom":
            run_custom_mode(client, args)
        else:
            run_standard_mode(client, args, preset=args.preset)

    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)
    finally:
        client.disconnect()
        print("\n已断开服务器连接")


if __name__ == "__main__":
    main()
