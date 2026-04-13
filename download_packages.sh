#!/bin/bash
set -eu

# SFTP 服务器配置
SFTP_HOST="cuftp.denglinai.com"
SFTP_PORT="22022"
SFTP_USER="lianyou"
SFTP_PASS="S9PmMhCk"
REMOTE_DIR="/V2 General release/V2-General_release-20260401/"

# 默认配置
DRY_RUN=false

usage() {
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --dry-run, -d    测试模式，只打印将要下载的文件，不实际下载"
    echo "  -h, --help       显示帮助信息"
    echo ""
    exit 1
}

# 解析命令行参数
while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --dry-run|-d)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "错误: 未知参数 $1"
            usage
            ;;
    esac
done

# 获取远程文件列表 (递归)
get_remote_file_list() {
    if $USE_LFTP; then
        local file_list
        file_list=$(lftp -u "$SFTP_USER,$SFTP_PASS" -p "$SFTP_PORT" "$SFTP_HOST" << EOF
cd "$REMOTE_DIR"
cls -R -1
bye
EOF
        )
        if [ -z "$file_list" ]; then
            echo "错误: 获取文件列表为空，请检查网络连接和服务器地址" >&2
            exit 1
        fi
        echo "$file_list"
    else
        # SFTP 服务器不支持 find 和 ls -R，所以直接检查已知的子目录
        # 根据用户提供的信息，安装包分布在这些子目录中
        # 包含大小写变体 Vllm/vllm 因为服务器上可能两种都存在
        local -a SUB_DIRS=("." "Base_driver" "K8s" "Vllm" "Vllm0.13.0_product_images" "vllm" "driver" "container")

        local clean_list=""

        # 遍历已知子目录，收集文件
        for subdir in "${SUB_DIRS[@]}"; do
            output=$(expect <<EOF
spawn sftp -o Port=$SFTP_PORT "$SFTP_USER@$SFTP_HOST"
expect {
    "Are you sure you want to continue connecting" {
        send "yes\r"
        expect "password:"
        send "$SFTP_PASS\r"
    }
    "password:" {
        send "$SFTP_PASS\r"
    }
}
expect "sftp>"
send "cd \"$REMOTE_DIR/$subdir\"\r"
expect {
    "sftp>" {
        send "ls\r"
        expect "sftp>"
        send "bye\r"
        expect eof
    }
    "No such file or directory" {
        send "bye\r"
        expect eof
    }
}
EOF
            )

            # 提取文件名，过滤掉提示信息 - 合并多个 grep -v 为一次调用
            files=$(echo "$output" | grep -vE "^spawn|password:|sftp>|connected to|Changing|The authenticity of host|RSA key fingerprint|Are you sure you want to continue connecting|Warning: Permanently added|This key is not known by any other names|No such file or directory|^\s*$")

            # 添加到列表，加上目录前缀
            if [ -n "$files" ] && [ "$subdir" != "." ]; then
                for file in $files; do
                    clean_list="$clean_list"$'\n'"$subdir/$file"
                done
            elif [ -n "$files" ]; then
                clean_list="$clean_list"$'\n'"$files"
            fi
        done

        # 清理空行
        clean_list=$(echo "$clean_list" | grep -v "^\s*$")

        if [ -z "$clean_list" ]; then
            echo "错误: 获取文件列表为空，请检查网络连接和服务器地址" >&2
            exit 1
        fi

        echo "$clean_list"
    fi
}

# 根据模式过滤文件
filter_matches() {
    local file_list="$1"
    local driver_matches container_matches vllm_matches
    driver_matches=$(echo "$file_list" | grep -E "$DRIVER_REGEX" || true)
    container_matches=$(echo "$file_list" | grep -E "$CONTAINER_REGEX" || true)
    vllm_matches=$(echo "$file_list" | grep -E "$VLLM_REGEX" || true)
    echo -e "$driver_matches\n$container_matches\n$vllm_matches" | grep -v "^\s*$"
}

# 显示匹配结果 (用于 dry-run)
display_matches() {
    local driver_count container_count vllm_count total_matched
    local ALL_MATCHES

    echo "【测试模式】列出匹配的文件，不实际下载"
    echo ""
    echo "正在获取远程文件列表..."
    FILE_LIST=$(get_remote_file_list)

    TOTAL_FILES=$(echo "$FILE_LIST" | wc -l | tr -d '[:space:]')
    echo "远程目录中共找到 $TOTAL_FILES 个文件"
    echo ""

    # 过滤出匹配的文件 (复用 filter_matches，避免重复三次 grep)
    ALL_MATCHES=$(filter_matches "$FILE_LIST")

    # 分离三类匹配结果
    DRIVER_MATCHES=$(echo "$ALL_MATCHES" | grep -E "$DRIVER_REGEX" || true)
    CONTAINER_MATCHES=$(echo "$ALL_MATCHES" | grep -E "$CONTAINER_REGEX" || true)
    VLLM_MATCHES=$(echo "$ALL_MATCHES" | grep -E "$VLLM_REGEX" || true)

    echo "匹配到的驱动包 ($DRIVER_PATTERN):"
    if [ -n "$DRIVER_MATCHES" ]; then
        echo "$DRIVER_MATCHES" | sed 's/^/  /'
    else
        echo "  (无匹配)"
    fi
    echo ""

    echo "匹配到的容器包 ($CONTAINER_PATTERN):"
    if [ -n "$CONTAINER_MATCHES" ]; then
        echo "$CONTAINER_MATCHES" | sed 's/^/  /'
    else
        echo "  (无匹配)"
    fi
    echo ""

    echo "匹配到的vLLM镜像 ($VLLM_PATTERN):"
    if [ -n "$VLLM_MATCHES" ]; then
        echo "$VLLM_MATCHES" | sed 's/^/  /'
    else
        echo "  (无匹配)"
    fi
    echo ""

    # 如果全部都没匹配到，显示所有文件名供检查
    driver_count=$(echo "$DRIVER_MATCHES" | grep -v "^$" | wc -l)
    container_count=$(echo "$CONTAINER_MATCHES" | grep -v "^$" | wc -l)
    vllm_count=$(echo "$VLLM_MATCHES" | grep -v "^$" | wc -l)
    total_matched=$((driver_count + container_count + vllm_count))

    if [ $total_matched -eq 0 ]; then
        echo ""
        echo "警告: 没有匹配到任何文件！远程目录中的所有文件:"
        echo "----------------------------------------"
        echo "$FILE_LIST" | sed 's/^/  /'
        echo "----------------------------------------"
    fi

    echo ""
    echo "确认无误后，请运行: ./download_packages.sh"
    exit 0
}

# 下载所有匹配的文件
download_files() {
    echo "正在获取远程文件列表..."
    FULL_FILE_LIST=$(get_remote_file_list)

    ALL_MATCHES=$(filter_matches "$FULL_FILE_LIST")

    if [ -z "$ALL_MATCHES" ]; then
        echo "错误: 没有找到匹配的文件可下载" >&2
        exit 1
    fi

    echo "找到以下匹配文件将被下载:"
    echo "$ALL_MATCHES" | sed 's/^/  /'
    echo ""
    echo "开始下载..."
    echo ""

    if $USE_LFTP; then
        # 单次连接下载所有文件 (比多次连接高效很多)
        {
            echo "cd \"$REMOTE_DIR\""
            while IFS= read -r file; do
                if [ -n "$file" ]; then
                    echo "echo 正在下载: $file"
                    echo "get \"$file\""
                fi
            done <<< "$ALL_MATCHES"
            echo "bye"
        } | lftp -u "$SFTP_USER,$SFTP_PASS" -p "$SFTP_PORT" "$SFTP_HOST"
    else
        # 使用 expect 单次连接下载所有文件 - 单个 expect 脚本处理所有文件
        {
            echo "spawn sftp -o Port=$SFTP_PORT $SFTP_USER@$SFTP_HOST"
            echo "expect {"
            echo "    \"Are you sure you want to continue connecting\" {"
            echo "        send \"yes\\r\""
            echo "        expect \"password:\""
            echo "        send \"$SFTP_PASS\\r\""
            echo "    }"
            echo "    \"password:\" {"
            echo "        send \"$SFTP_PASS\\r\""
            echo "    }"
            echo "}"
            echo "expect \"sftp>\""
            echo "send \"cd \\\"$REMOTE_DIR\\\"\\r\""
            echo "expect \"sftp>\""
            while IFS= read -r file; do
                if [ -n "$file" ]; then
                    echo "send \"get \\\"$file\\\"\\r\""
                    echo "expect \"sftp>\""
                fi
            done <<< "$ALL_MATCHES"
            echo "send \"bye\\r\""
            echo "expect eof"
        } | expect
    fi
}

# ========== 主程序 ==========

# 显示欢迎信息
echo "============================================================"
echo "       DengLin vLLM 部署包下载工具"
echo "============================================================"
echo ""
echo "SFTP 服务器: $SFTP_HOST:$SFTP_PORT"
echo "远程目录: $REMOTE_DIR"
if $DRY_RUN; then
    echo "模式: 测试模式 (仅打印，不实际下载)"
fi
echo ""

# 询问用户 CPU 架构
echo "请选择您的主控 CPU 架构:"
echo "  1) X86 (x86_64)"
echo "  2) arm64 (aarch64)"
read -p "请输入选项 (1 或 2): " ARCH_CHOICE

case "$ARCH_CHOICE" in
    1)
        ARCH="x86"
        ;;
    2)
        ARCH="arm64"
        ;;
    *)
        echo "错误: 无效选项，请输入 1 或 2"
        exit 1
        ;;
esac

echo "已选择: $ARCH 架构"
echo ""

# 检查是否安装了 lftp
if ! command -v lftp &> /dev/null; then
    echo "警告: 未找到 lftp 命令，尝试使用 sftp..."
    if ! command -v sftp &> /dev/null; then
        echo "错误: 需要安装 lftp 或 openssh (sftp) 才能继续"
        echo "请安装: sudo apt install lftp 或 sudo yum install lftp"
        exit 1
    fi
    if ! command -v expect &> /dev/null; then
        echo "错误: 使用 sftp 需要 expect，请安装: sudo apt install expect" >&2
        exit 1
    fi
    USE_LFTP=false
else
    USE_LFTP=true
fi

# 选择 SDK 版本
select_sdk_version() {
    local PARENT_DIR="/V2 General release"
    local -a versions
    local version_list

    echo "正在获取可用 SDK 版本列表..."

    version_list=$(get_available_versions "$PARENT_DIR")
    if [ $? -ne 0 ] || [ -z "$version_list" ]; then
        echo ""
        echo "警告: 无法获取远程版本列表，将使用默认目录: $REMOTE_DIR"
        read -p "是否继续? (Y/n): " CONTINUE
        if [[ ! "$CONTINUE" =~ ^[Nn]$ ]]; then
            return 0
        else
            exit 1
        fi
    fi

    # 将版本列表转换为数组
    versions=($(echo "$version_list" | tr '\n' ' '))

    if [ ${#versions[@]} -eq 0 ]; then
        echo ""
        echo "错误: 未找到任何可用版本，请检查服务器连接" >&2
        exit 1
    fi

    echo "找到 ${#versions[@]} 个可用版本:"
    echo "  最新版本: ${versions[0]}"
    echo ""
    read -p "是否使用最新版本? [Y/n]: " USE_LATEST

    if [[ -z "$USE_LATEST" || "$USE_LATEST" =~ ^[Yy]$ ]]; then
        SELECTED_VERSION="${versions[0]}"
    else
        echo ""
        echo "请选择版本 (输入编号):"
        local i=1
        for ver in "${versions[@]}"; do
            echo "  $i) $ver"
            i=$((i + 1))
        done
        read -p "请输入编号: " VERSION_CHOICE
        if ! [[ "$VERSION_CHOICE" =~ ^[0-9]+$ ]] || [ "$VERSION_CHOICE" -lt 1 ] || [ "$VERSION_CHOICE" -gt "${#versions[@]}" ]; then
            echo "错误: 无效选择" >&2
            exit 1
        fi
        SELECTED_VERSION="${versions[$((VERSION_CHOICE - 1))]}"
    fi

    # 更新 REMOTE_DIR
    REMOTE_DIR="$PARENT_DIR/$SELECTED_VERSION/"
    echo ""
    echo "已选择 SDK 版本: $SELECTED_VERSION"
    echo "远程目录更新为: $REMOTE_DIR"
}

# 获取所有可用版本 (按日期降序排序)
get_available_versions() {
    local parent_dir="$1"
    local output dir_list
    local temp_file="/tmp/dl_get_versions_$$.txt"

    # 确保临时文件会被清理
    trap "rm -f $temp_file" EXIT

    if $USE_LFTP; then
        # 临时关闭 -e，让我们自己处理错误
        set +e
        lftp -u "$SFTP_USER,$SFTP_PASS" -p "$SFTP_PORT" "$SFTP_HOST" << EOF > "$temp_file"
cd "$parent_dir"
cls -1
bye
EOF
        local exit_code=$?
        output=$(cat "$temp_file")
        rm -f "$temp_file"
        set -e
        if [ $exit_code -ne 0 ]; then
            return 1
        fi
    else
        # 使用临时文件输出而不是命令替换，避免 expect 死锁
        # 临时关闭 -e，让我们自己处理 expect 错误
        set +e
        expect > "$temp_file" <<EOF
set timeout 20
spawn sftp -o Port=$SFTP_PORT "$SFTP_USER@$SFTP_HOST"
expect {
    timeout { puts "TIMEOUT connecting"; exit 1 }
    "Are you sure you want to continue connecting" {
        send "yes\r"
        expect {
            timeout { puts "TIMEOUT waiting for password"; exit 1 }
            "password:" {
                send "$SFTP_PASS\r"
            }
            "Permission denied" {
                puts "Password authentication failed"; exit 1
            }
        }
    }
    "password:" {
        send "$SFTP_PASS\r"
    }
    "Permission denied" {
        puts "Password authentication failed"; exit 1
    }
}
expect {
    timeout { puts "TIMEOUT waiting for sftp prompt"; exit 1 }
    "sftp>" {
        send "cd \"$parent_dir\"\r"
    }
}
expect {
    timeout { puts "TIMEOUT after cd"; exit 1 }
    "sftp>" {
        send "ls\r"
        expect {
            timeout { puts "TIMEOUT waiting for ls output"; exit 1 }
            "sftp>"
        }
        send "bye\r"
        expect {
            timeout { puts "TIMEOUT waiting for eof"; exit 1 }
            eof
        }
    }
    "No such file or directory" {
        puts "cd failed: No such file or directory"
        send "bye\r"
        expect eof
        exit 1
    }
}
EOF
        local exit_code=$?
        output=$(cat "$temp_file")
        rm -f "$temp_file"
        set -e
        # 调试输出，帮助排查问题
        echo "DEBUG: expect exit code: $exit_code" >> /tmp/debug.log
        echo "DEBUG: output:" >> /tmp/debug.log
        echo "$output" >> /tmp/debug.log
        echo "--- END ---" >> /tmp/debug.log
        if [ $exit_code -ne 0 ]; then
            return 1
        fi
        # 过滤掉提示信息，提取匹配的版本名称
        output=$(echo "$output" | grep -vE "^spawn|password:|sftp>|connected to|Changing|The authenticity of host|RSA key fingerprint|Are you sure you want to continue connecting|Warning: Permanently added|This key is not known by any other names|No such file or directory|^\s*$")
        # 只保留 V2-General_release-YYYYMMDD 格式的版本文件夹
        output=$(echo "$output" | grep -Eo "V2-General_release-[0-9]{8}")
    fi

    # 过滤匹配 V2-General_release-YYYYMMDD
    dir_list=$(echo "$output" | grep -E "^V2-General_release-[0-9]{8}$")

    if [ -z "$dir_list" ]; then
        return 1
    fi

    # 按日期降序排序 (YYYYMMDD 格式天然可按字符串排序)
    echo "$dir_list" | sort -r
    return 0
}

# 执行版本选择
select_sdk_version
echo ""

# 根据架构设置匹配模式
case "$ARCH" in
    x86)
        DRIVER_PATTERN="*driver*manylinux*x86*.tar*"
        CONTAINER_PATTERN="*container*x86*.tar*"
        VLLM_PATTERN="*vllm*x86*.tar*"
        ;;
    arm64)
        # 同时匹配 arm64 和 aarch64 两种写法
        DRIVER_PATTERN="*driver*manylinux*(arm64|aarch64)*.tar*"
        CONTAINER_PATTERN="*container*(arm64|aarch64)*.tar*"
        VLLM_PATTERN="*vllm*(arm64|aarch64)*.tar*"
        ;;
esac

# 预先转换一次正则表达式 (只做一次，不再重复)
for pat_var in DRIVER_PATTERN CONTAINER_PATTERN VLLM_PATTERN; do
    regex_var="${pat_var%_PATTERN}_REGEX"
    eval "$regex_var=\$(echo "\${$pat_var}" | sed -e 's/\*/\.\*/g')"
done

echo "匹配模式:"
echo "  驱动包: $DRIVER_PATTERN"
echo "  容器包: $CONTAINER_PATTERN"
echo "  vLLM镜像: $VLLM_PATTERN"
echo ""

# 确认开始下载
read -p "确认开始下载吗? (y/N): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "已取消下载"
    exit 0
fi

echo ""
echo "开始连接服务器..."
echo ""

# 测试模式或正常下载
if $DRY_RUN; then
    display_matches
else
    download_files
fi

echo ""
echo "============================================================"
echo "下载完成!"
echo "============================================================"
echo ""

# 列出下载的文件
echo "已下载的文件:"
ls -lh *driver* *container* *vllm* 2>/dev/null || echo "未找到下载的文件，请检查匹配条件"
echo ""
echo "接下来可以运行: sudo bash deploy.sh"
