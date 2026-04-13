"""SFTP 服务器配置常量"""

SFTP_HOST = "cuftp.denglinai.com"
SFTP_PORT = 22022
SFTP_USER = "lianyou"
SFTP_PASS = "S9PmMhCk"
REMOTE_BASE_DIR = "/V2 General release"

# 远程目录中已知的子目录
SUB_DIRS = ["", "Base_driver", "K8s", "Vllm", "Vllm0.13.0_product_images", "vllm", "driver", "container"]

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
