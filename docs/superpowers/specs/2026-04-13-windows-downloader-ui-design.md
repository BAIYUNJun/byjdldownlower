# Windows 下载工具 UI 设计文档

## 概述

将 `download_packages.sh` 脚本的逻辑迁移到 Windows 桌面应用，使用 Python + PyQt6 构建，提供向导式 UI 界面。SFTP 连接使用 paramiko 纯 Python 实现。

## 技术栈

- **UI 框架**: PyQt6
- **SFTP 客户端**: paramiko
- **文件匹配**: fnmatch (标准库)
- **打包**: PyInstaller (生成 exe)

## 项目结构

```
downloader/
├── main.py              # 入口，启动 PyQt6 应用
├── ui/
│   ├── wizard.py        # 向导主窗口（QStackedWidget 管理页面切换）
│   ├── welcome_page.py  # 欢迎页
│   ├── config_page.py   # 架构 + 版本选择页
│   └── download_page.py # 文件列表 + 下载进度页
├── sftp_client.py       # paramiko 封装（连接、列目录、下载文件）
└── config.py            # SFTP 配置常量（主机、端口、���户名、密码）
```

## 数据流

1. `sftp_client.py` 使用 paramiko 连接 SFTP 服务器
2. 获取版本列表和文件列表
3. UI 页面通过 Qt 信号/槽与 sftp_client 交互
4. 下载操作在 QThread 中运行，通过信号更新进度条

## 页面设计

### 页面 1：欢迎页

- 工具名称 "DengLin vLLM 部署包下载工具" 居中大字体
- 服务器信息（地址:端口）显示
- 底部居中 "开始" 按钮

### 页面 2：配置页

- **架构选择**: 两个大卡片按钮 (x86_64 / arm64)，选中高亮
- **版本选择**: 从服务器获取版本列表，下拉框显示，默认选中最新版本，旁边有"刷新"按钮
- 获取版本期间显示 loading 状态
- 底部：上一步 / 下一步

### 页面 3：下载页

- **文件列表**: 显示匹配文件（驱动包、容器包、vLLM 镜像），图标区分类型
- **保存目录**: 目录路径 + "浏览"按钮
- **下载按钮**: 开始下载
- **进度区域**: 总体进度条（已下载/总文件数）+ 当前文件名 + 单文件进度条 + 速度 + 已用时间
- **日志区域**: 底部文本框，实时显示下载日志
- 下载完成后显示"完成"提示 + "打开文件夹"按钮

## SFTP 客户端逻辑

与原脚本一一对应：

| 原脚本功能 | Python 实现 |
|-----------|------------|
| `get_available_versions()` | paramiko 连接，遍历 `/V2 General release/` 目录，正则匹配 `V2-General_release-YYYYMMDD`，按日期降序排序 |
| `get_remote_file_list()` | 逐个遍历子目录 (`Base_driver`, `K8s`, `Vllm` 等) 收集文件列表 |
| `filter_matches()` | fnmatch 匹配驱动包/容器包/vLLM 镜像 |
| `download_files()` | paramiko `get()` 下载，回调函数报告进度 |

## 异步处理

- 版本获取和文件下载放在 QThread 中执行，不阻塞 UI
- 通过 Qt 信号传递进度和状态

## 错误处理

| 场景 | 处理方式 |
|------|---------|
| 网络连接失败 | 弹窗提示 + "重试"按钮 |
| 版本列表为空 | 提示"未找到可用版本" + 返回上一步 |
| 匹配文件为空 | 下载页提示"无匹配文件" + 显示所有文件供检查 |
| 下载中断 | 断点续传（检查本地文件大小，跳过已完成文件） |
| SFTP 认证失败 | 明确提示"认证失败，请检查配置" |

## 文件匹配规则

与原脚本一致：

- **x86**: `*driver*manylinux*x86*.tar*`, `*container*x86*.tar*`, `*vllm*x86*.tar*`
- **arm64**: `*driver*manylinux*(arm64|aarch64)*.tar*`, `*container*(arm64|aarch64)*.tar*`, `*vllm*(arm64|aarch64)*.tar*`

## 依赖

- PyQt6
- paramiko
