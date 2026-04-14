"""SFTP 服务器配置常量"""

SFTP_HOST = "cuftp.denglinai.com"
SFTP_PORT = 22022
SFTP_USER = "lianyou"
SFTP_PASS = "S9PmMhCk"
REMOTE_BASE_DIR = "/V2 General release"

# 远程目录中已知的子目录
SUB_DIRS = [
    "", "Base_driver", "K8s", "Vllm", "Vllm0.13.0_product_images", "vllm", "driver", "container",
    "SDK", "SDK_product_images", "Pytorch2.5_product_images", "k8s", "doc",
]

# 自定义下载类别配置
CUSTOM_CATEGORIES = {
    "driver":        {"label": "Driver",       "subdir": "Base_driver",              "arch_filter": True,  "os_filter": True},
    "sdk":           {"label": "SDK",           "subdir": "SDK",                      "arch_filter": True,  "os_filter": True},
    "cuda11":        {"label": "cuda11 头文件", "subdir": "",                        "arch_filter": False, "os_filter": False, "name_filter": "cuda11"},
    "sdk_image":     {"label": "SDK 镜像",     "subdir": "SDK_product_images",        "arch_filter": True,  "os_filter": True},
    "pytorch_image": {"label": "Pytorch 镜像", "subdir": "Pytorch2.5_product_images", "arch_filter": True,  "os_filter": True},
    "container":     {"label": "登临容器组件", "subdir": "k8s",                      "arch_filter": True,  "os_filter": True, "name_filter": "container"},
    "vllm_image":    {"label": "vLLM 镜像",    "subdir": "Vllm0.13.0_product_images", "arch_filter": True,  "os_filter": True},
    "doc":           {"label": "文档",          "subdir": "doc",                      "arch_filter": False, "os_filter": False},
}

# 操作系统选项
OS_OPTIONS = [
    {"key": "linux",   "label": "Linux",   "desc": "Ubuntu / Debian 等"},
    {"key": "centos",  "label": "CentOS",  "desc": "CentOS / RHEL"},
    {"key": "windows", "label": "Windows", "desc": "Windows Server"},
]

# Windows 和 CentOS 下不可用的类别（容器/镜像类）
OS_DISABLED_CATEGORIES = ["container", "vllm_image", "sdk_image", "pytorch_image"]

# 预设模式：点击预设按钮自动勾选对应类别
PRESETS = {
    "vllm":  {"label": "测试 vLLM", "categories": ["driver", "container", "vllm_image"]},
    "cv":    {"label": "测试 CV",   "categories": ["driver", "sdk", "cuda11"]},
    "other": {"label": "其他",      "categories": []},
}

# 文件匹配模式
ARCH_PATTERNS = {
    "x86": {
        "driver": "*driver*manylinux*x86*.tar*",
        "container": "*container*x86*.tar*",
        "vllm": "*vllm*x86*.tar*",
    },
    "arm64": {
        "driver": ["*driver*manylinux*arm64*.tar*", "*driver*manylinux*aarch64*.tar*"],
        "container": ["*container*arm64*.tar*", "*container*aarch64*.tar*"],
        "vllm": ["*vllm*arm64*.tar*", "*vllm*aarch64*.tar*"],
    },
}
