"""登临部署包下载工具 — 极简命令行版（仅依赖 paramiko）"""

from __future__ import annotations

import os
import re
import sys

import paramiko

# ── 配置 ──────────────────────────────────────────────
HOST, PORT = "cuftp.denglinai.com", 22022
DEFAULT_USER, DEFAULT_PASS = "lianyou", "S9PmMhCk"
BASE_DIR = "/V2 General release"

SUB_DIRS = [
    "", "Base_driver", "K8s", "Vllm", "Vllm0.13.0_product_images", "vllm",
    "driver", "container", "SDK", "SDK_product_images",
    "Pytorch2.5_product_images", "k8s", "Docs",
]

# (subdir, arch_filter, os_filter, name_filter)
CATEGORIES: dict[str, tuple[str, bool, bool, str | None]] = {
    "driver":        ("Base_driver",               True,  True,  None),
    "sdk":           ("SDK",                       True,  True,  None),
    "cuda11":        ("",                          False, False, "cuda11"),
    "sdk_image":     ("SDK_product_images",        True,  True,  None),
    "pytorch_image": ("Pytorch2.5_product_images", True,  True,  None),
    "container":     ("k8s",                       True,  True,  "container"),
    "vllm_image":    ("Vllm0.13.0_product_images", True,  True,  None),
    "doc":           ("Docs",                      False, False, None),
}

WINDOWS_DISABLED = {"container", "vllm_image", "sdk_image", "pytorch_image"}


# ── SFTP 操作 ─────────────────────────────────────────
def sftp_connect(user: str, pwd: str) -> paramiko.SFTPClient:
    t = paramiko.Transport((HOST, PORT))
    t.connect(username=user, password=pwd)
    return paramiko.SFTPClient.from_transport(t)


def list_versions(sftp: paramiko.SFTPClient) -> list[str]:
    vs = [e for e in sftp.listdir(BASE_DIR)
          if re.match(r"^V2-General_release-\d{8}$", e)]
    vs.sort(reverse=True)
    return vs


def list_files(sftp: paramiko.SFTPClient, version: str) -> list[str]:
    root = f"{BASE_DIR}/{version}"
    files: list[str] = []
    for sub in SUB_DIRS:
        target = f"{root}/{sub}" if sub else root
        try:
            for entry in sftp.listdir(target):
                try:
                    sftp.stat(f"{target}/{entry}")
                    if "." in entry or entry.endswith(".tar") or ".tar." in entry:
                        files.append(f"{sub}/{entry}" if sub else entry)
                except (IOError, FileNotFoundError):
                    continue
        except (IOError, FileNotFoundError):
            continue
    return files


# ── 过滤 ──────────────────────────────────────────────
def _match_arch(name: str, arch: str) -> bool:
    n = os.path.basename(name).lower()
    return ("x86" in n) if arch == "x86" else ("arm64" in n or "aarch64" in n)


def _match_os(name: str, os_name: str) -> bool:
    n = os.path.basename(name).lower()
    if os_name == "linux":
        return "linux" in n or "ubuntu" in n
    if os_name == "windows":
        return "win" in n
    if os_name == "centos":
        return "centos" in n
    return True


def filter_files(
    files: list[str], arch: str, os_name: str, cats: list[str],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for cat in cats:
        subdir, af, of, nf = CATEGORIES[cat]
        matched = [
            f for f in files
            if (not subdir or f.startswith(subdir + "/"))
            and (not nf or nf.lower() in os.path.basename(f).lower())
            and (not af or os_name == "windows" or _match_arch(f, arch))
            and (not of or not os_name or _match_os(f, os_name))
        ]
        result[cat] = matched
    return result


# ── 进度条 ─────────────────────────────────────────────
def _progress_bar(done: int, total: int, width: int = 40):
    pct = done / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + "░" * (width - filled)
    mb_done, mb_total = done // 1024 // 1024, total // 1024 // 1024
    sys.stdout.write(f"\r    [{bar}] {pct:6.1%}  {mb_done}/{mb_total}MB")
    sys.stdout.flush()
    if done >= total:
        sys.stdout.write("\n")


# ── 下载 ──────────────────────────────────────────────
def download_files(
    sftp: paramiko.SFTPClient, version: str,
    files: list[str], local_dir: str,
):
    os.makedirs(local_dir, exist_ok=True)
    total = len(files)
    overall_bytes, overall_size = 0, 0
    for rpath in files:
        overall_size += sftp.stat(f"{BASE_DIR}/{version}/{rpath}").st_size

    for i, rpath in enumerate(files, 1):
        remote = f"{BASE_DIR}/{version}/{rpath}"
        local = os.path.join(local_dir, os.path.basename(rpath))
        size = sftp.stat(remote).st_size
        name = os.path.basename(rpath)

        if os.path.exists(local) and os.path.getsize(local) == size:
            overall_bytes += size
            print(f"  [{i}/{total}] 跳过（已存在）{name}")
            continue

        print(f"  [{i}/{total}] {name} ({size // 1024 // 1024}MB)")
        _progress_bar(0, size)
        sftp.get(remote, local, callback=lambda d, t, s=size: _progress_bar(d, s))
        overall_bytes += size

        # 总体进度
        if overall_size:
            op = overall_bytes / overall_size
            print(f"    总体进度: {op:.1%} ({i}/{total} 个文件)")

    print("\n全部完成！")


# ── 交互 ──────────────────────────────────────────────
def _choose(label: str, options: list[str]) -> int:
    for i, o in enumerate(options):
        print(f"  {i + 1}. {o}")
    while True:
        try:
            idx = int(input(f"{label}: ")) - 1
            if 0 <= idx < len(options):
                return idx
        except (ValueError, EOFError):
            pass
        print("  无效选择，请重试")


def main():
    print("=== 登临部署包下载工具（命令行版）===\n")

    user = input(f"用户名 [{DEFAULT_USER}]: ").strip() or DEFAULT_USER
    pwd = input(f"密码 [{DEFAULT_PASS}]: ").strip() or DEFAULT_PASS

    print("连接中...")
    sftp = sftp_connect(user, pwd)
    print("已连接！\n")

    try:
        # 版本
        versions = list_versions(sftp)
        if not versions:
            print("没有可用版本")
            return
        print("可用版本：")
        version = versions[_choose("选择版本", versions)]

        # 架构
        print("\n架构：")
        arch = ["x86", "arm64"][_choose("选择架构", ["x86", "arm64"])]

        # 系统
        print("\n操作系统：")
        os_name = ["linux", "windows", "centos"][
            _choose("选择系统", ["linux", "windows", "centos"])
        ]

        # 类别
        avail = [k for k in CATEGORIES
                 if not (os_name == "windows" and k in WINDOWS_DISABLED)]
        print("\n下载类别：")
        for i, k in enumerate(avail):
            print(f"  {i + 1}. {k}")
        print("  0 = 全部")
        raw = input("选择类别（逗号分隔，如 1,2,3）: ").strip()
        cats = avail if raw == "0" else [
            avail[int(x.strip()) - 1]
            for x in raw.split(",") if x.strip().isdigit()
            and 0 < int(x.strip()) <= len(avail)
        ]

        if not cats:
            print("未选择任何类别")
            return

        # 扫描并过滤
        print("\n扫描远程文件...")
        files = list_files(sftp, version)
        matched = filter_files(files, arch, os_name, cats)

        all_files: list[str] = []
        for cat, flist in matched.items():
            print(f"\n[{cat}] 匹配 {len(flist)} 个文件：")
            for f in flist:
                print(f"    {f}")
            all_files.extend(flist)

        if not all_files:
            print("\n没有匹配的文件")
            return

        print(f"\n共 {len(all_files)} 个文件待下载")
        save_dir = input(f"保存目录 [./downloads/{version}]: ").strip()
        if not save_dir:
            save_dir = f"./downloads/{version}"

        download_files(sftp, version, all_files, save_dir)
    finally:
        sftp.close()


if __name__ == "__main__":
    main()
