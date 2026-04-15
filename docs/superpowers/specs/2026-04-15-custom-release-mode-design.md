# 定制发布模式设计文档

## 概述

在配置页面增加"标准发布/定制发布"切换开关，允许用户选择非标准发布的定制文件夹进行文件下载。

## 需求

- 配置页面增加发布类型切换：**标准发布**（默认）和**定制发布**
- 标准发布：所有逻辑不变
- 定制发布：获取FTP根目录下的定制文件夹（排除 `V2 General release` 和 `V1 General release`，只返回目录类型），用户选择后进入模式选择页，预设按钮隐藏，下载组件变为定制文件夹内的文件列表（全部显示，不做架构/OS过滤），用户勾选后��载
- 配置页选择定制发布时，隐藏架构和OS选择卡片

## FTP 验证结果

根目录 `/` 下有约 30 个定制文件夹，每个文件夹根目录包含 1-4 个文件，无子目录结构。文件格式多样（.zip, .tar, .whl, .tar.gz）。根目录也存在文件类型条目（如 `dl-ae-customer-support-v4.1-whisper-py38.tar.gz`），需要过滤只保留目录。

## 设计

### 1. 配置页面 (`downloader/ui/config_page.py`)

**UI 变化：**

在架构选择区域上方，增加发布类型切换控件：
- 两个互斥 checkable QPushButton，放在 QButtonGroup 中
- 标签："标准发布" / "定制发布"
- 样式与现有预设按钮一致（圆角边框，选中时蓝色高亮）
- 默认选中"标准发布"

**切换行为：**

| 区域 | 标准发布 | 定制发布 |
|------|---------|---------|
| 架构选择 | 显示 | 隐藏 |
| 操作系统选择 | 显示 | 隐藏 |
| SDK版本下拉 | 获取 `V2 General release` 下的版本 | 获取根目录下的定制文件夹名 |

**"下一步"信号：**

扩展 `next_clicked` 信号参数，增加 `release_type`：
- `next_clicked(arch, version, os_name, release_type)`
- `release_type`: `"standard"` 或 `"custom"`
- 定制发布时 `arch=""`, `os_name=""`

**定制文件夹获取逻辑：**

选中"定制发布"时自动触发获取，复用 `_fetch_versions` 方法的 UI 更新模式：
- 创建 `FetchCustomFoldersWorker` 获取数据
- 下拉框显示文件夹名
- 切换回"标准发布"时恢复原逻辑

### 2. SFTP 客户端 (`downloader/sftp_client.py`)

新增方法 `get_custom_folders() -> list[str]`：
```python
def get_custom_folders(self) -> list[str]:
    entries = self._sftp.listdir("/")
    exclude = {"V2 General release", "V1 General release"}
    folders = []
    for e in entries:
        if e in exclude:
            continue
        try:
            attr = self._sftp.stat("/" + e)
            if attr.st_mode & 0o170000 == 0o040000:  # 仅目录
                folders.append(e)
        except (IOError, FileNotFoundError):
            continue
    folders.sort(reverse=True)
    return folders
```

新增方法 `get_custom_files(folder: str) -> list[str]`：
```python
def get_custom_files(self, folder: str) -> list[str]:
    entries = self._sftp.listdir("/" + folder)
    files = []
    for entry in entries:
        try:
            attr = self._sftp.stat("/" + folder + "/" + entry)
            if attr.st_mode & 0o170000 != 0o040000:  # 仅文件
                files.append(entry)
        except (IOError, FileNotFoundError):
            continue
    return files
```

注意：定制文件的远程路径为 `/<folder>/<filename>`，与标准发布的 `<REMOTE_BASE_DIR>/<version>/<subdir>/<filename>` 不同。`download_file` 方法需要适配定制模式。

扩展 `download_file` 方法：增加 `is_custom` 参数，定制模式下远程路径为 `/<version>/<remote_path>`（此处 `version` 参数复用为文件夹名）。

### 3. Worker (`downloader/workers.py`)

新增 `FetchCustomFoldersWorker(QThread)`：
- 参数：`username`, `password`
- 调用 `SFTPClient.get_custom_folders()`
- 信号：`success(list[str])`, `error(str)`

新增 `FetchCustomFilesWorker(QThread)`：
- 参数：`username`, `password`, `folder`
- 调用 `SFTPClient.get_custom_files(folder)`
- 信号：`success(list[str])`, `error(str)`

### 4. 模式选择页面 (`downloader/ui/mode_selection_page.py`)

`on_enter()` 增加 `release_type` 参数。

**定制模式 (`release_type == "custom"`) 行为：**
- 隐藏预设按钮区域（"快速选择"标题 + 3个预设按钮）
- 进入页面时启动 `FetchCustomFilesWorker` 获取文件夹内容
- 获取完成后，清空原有 checkbox，为每个文件名动态创建 checkbox
- 文件名作为 checkbox 文本，同时记录完整路径
- "下一步"信号格式：`{"files": ["file1", "file2", ...], "category_labels": {"file1": "file1", ...}}`

**标准模式 (`release_type == "standard"`) 行为：**
- 恢复预设按钮区域
- 恢复固定 checkbox，行为不变

### 5. 下载页面 (`downloader/ui/download_page.py`)

`on_enter()` 增加 `release_type` 参数（从 mode_config 传入）。

**定制模式行为：**
- 跳过 `FetchFilesWorker`（文件列表已从模式选择页获取）
- 直接使用 `mode_config["files"]` 作为下载列表
- 下载时传递 `is_custom=True`，使远程路径正确拼接

**标准模式行为：** 不变。

### 6. 向导窗口 (`downloader/ui/wizard.py`)

- `_go_to_mode_selection()` 增加 `release_type` 参数透传
- `_go_to_download()` 增加 `release_type` 参数透传
- 定制发布时 `arch` 和 `os_name` 为空字符串

### 数据流

```
标准发布:
  config_page(arch, os, version, "standard")
    → wizard: _go_to_mode_selection(arch, version, os, "standard")
    → mode_selection_page: 显示预设 + 固定categories
    → wizard: _go_to_download(mode_config, "standard")
    → download_page: FetchFilesWorker过滤 → 下载

定制发布:
  config_page("", "", folder, "custom")
    → wizard: _go_to_mode_selection("", folder, "", "custom")
    → mode_selection_page: 隐藏预设 + FetchCustomFilesWorker获取文件 → 动态checkbox
    → wizard: _go_to_download(mode_config, "custom")
    → download_page: 直接用勾选文件 → 下载
```

## 涉及文件

| 文件 | 变更类型 |
|------|---------|
| `downloader/sftp_client.py` | 新增 `get_custom_folders()`, `get_custom_files()`, 扩展 `download_file()` |
| `downloader/workers.py` | 新增 `FetchCustomFoldersWorker`, `FetchCustomFilesWorker` |
| `downloader/ui/config_page.py` | 增加发布类型切换UI和逻辑 |
| `downloader/ui/mode_selection_page.py` | 支持定制模式的动态checkbox |
| `downloader/ui/download_page.py` | 支持定制模式的文件下载 |
| `downloader/ui/wizard.py` | 透传 `release_type` 参数 |
| `downloader/config.py` | 无变更 |
