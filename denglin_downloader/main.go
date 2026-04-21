package main

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"

	"github.com/pkg/sftp"
	"golang.org/x/crypto/ssh"
)

// ── 配置 ──────────────────────────────────────────────
const (
	host       = "cuftp.denglinai.com:22022"
	defaultUser = "lianyou"
	defaultPass = "S9PmMhCk"
	baseDir    = "/V2 General release"
)

var subDirs = []string{
	"", "Base_driver", "K8s", "Vllm", "Vllm0.13.0_product_images", "vllm",
	"driver", "container", "SDK", "SDK_product_images",
	"Pytorch2.5_product_images", "k8s", "Docs",
}

// subdir, archFilter, osFilter, nameFilter
type category struct {
	label      string
	subdir     string
	archFilter bool
	osFilter   bool
	nameFilter string
}

var categories = map[string]category{
	"driver":        {"Driver", "Base_driver", true, true, ""},
	"sdk":           {"SDK", "SDK", true, true, ""},
	"cuda11":        {"cuda11 头文件", "", false, false, "cuda11"},
	"sdk_image":     {"SDK 镜像", "SDK_product_images", true, true, ""},
	"pytorch_image": {"Pytorch 镜像", "Pytorch2.5_product_images", true, true, ""},
	"container":     {"登临容器组件", "k8s", true, true, "container"},
	"vllm_image":    {"vLLM 镜像", "Vllm0.13.0_product_images", true, true, ""},
	"doc":           {"文档", "Docs", false, false, ""},
}

var windowsDisabled = map[string]bool{
	"container": true, "vllm_image": true, "sdk_image": true, "pytorch_image": true,
}

// ── SFTP 连接 ────────────────────���────────────────────
func connect(user, pass string) (*ssh.Client, *sftp.Client, error) {
	config := &ssh.ClientConfig{
		User: user,
		Auth: []ssh.AuthMethod{ssh.Password(pass)},
		HostKeyCallback: ssh.InsecureIgnoreHostKey(),
		Timeout:         10 * time.Second,
	}
	sshClient, err := ssh.Dial("tcp", host, config)
	if err != nil {
		return nil, nil, err
	}
	sftpClient, err := sftp.NewClient(sshClient)
	if err != nil {
		sshClient.Close()
		return nil, nil, err
	}
	return sshClient, sftpClient, nil
}

// ── 版本列表 ──────────────────────────────────────────
var versionRe = regexp.MustCompile(`^V2-General_release-\d{8}$`)

func listVersions(c *sftp.Client) []string {
	entries, err := c.ReadDir(baseDir)
	if err != nil {
		return nil
	}
	var vs []string
	for _, e := range entries {
		if versionRe.MatchString(e.Name()) {
			vs = append(vs, e.Name())
		}
	}
	sort.Sort(sort.Reverse(sort.StringSlice(vs)))
	return vs
}

// ── 文件列表 ──────────────────────────────────────────
func listFiles(c *sftp.Client, version string) []string {
	root := baseDir + "/" + version
	var files []string
	for _, sub := range subDirs {
		target := root + "/" + sub
		if sub == "" {
			target = root
		}
		entries, err := c.ReadDir(target)
		if err != nil {
			continue
		}
		for _, e := range entries {
			if e.IsDir() {
				continue
			}
			name := e.Name()
			if strings.Contains(name, ".") || strings.HasSuffix(name, ".tar") || strings.Contains(name, ".tar.") {
				if sub != "" {
					files = append(files, sub+"/"+name)
				} else {
					files = append(files, name)
				}
			}
		}
	}
	return files
}

// ── 过滤 ──────────────────────────────────────────────
func matchArch(name, arch string) bool {
	n := strings.ToLower(filepath.Base(name))
	if arch == "x86" {
		return strings.Contains(n, "x86")
	}
	return strings.Contains(n, "arm64") || strings.Contains(n, "aarch64")
}

func matchOS(name, osName string) bool {
	n := strings.ToLower(filepath.Base(name))
	switch osName {
	case "linux":
		return strings.Contains(n, "linux") || strings.Contains(n, "ubuntu")
	case "windows":
		return strings.Contains(n, "win")
	case "centos":
		return strings.Contains(n, "centos")
	}
	return true
}

func filterFiles(files []string, arch, osName string, cats []string) map[string][]string {
	result := map[string][]string{}
	for _, catKey := range cats {
		cat := categories[catKey]
		var matched []string
		for _, f := range files {
			if cat.subdir != "" && !strings.HasPrefix(f, cat.subdir+"/") {
				continue
			}
			if cat.nameFilter != "" && !strings.Contains(strings.ToLower(filepath.Base(f)), cat.nameFilter) {
				continue
			}
			if cat.archFilter && osName != "windows" && !matchArch(f, arch) {
				continue
			}
			if cat.osFilter && osName != "" && !matchOS(f, osName) {
				continue
			}
			matched = append(matched, f)
		}
		result[catKey] = matched
	}
	return result
}

// ── 下载 + 进度条 ─────────────────────────────────────
func downloadFile(c *sftp.Client, remote, local string) error {
	if err := os.MkdirAll(filepath.Dir(local), 0o755); err != nil {
		return err
	}

	remoteFile, err := c.Open(remote)
	if err != nil {
		return err
	}
	defer remoteFile.Close()

	stat, err := remoteFile.Stat()
	if err != nil {
		return err
	}
	totalSize := stat.Size()

	// 跳过已存在且大小一致的文件
	if info, err := os.Stat(local); err == nil && info.Size() == totalSize {
		fmt.Printf("  跳过（已存在）%s\n", filepath.Base(local))
		return nil
	}

	localFile, err := os.Create(local)
	if err != nil {
		return err
	}
	defer localFile.Close()

	fmt.Printf("  下载中 %s (%dMB)\n", filepath.Base(local), totalSize/1024/1024)

	buf := make([]byte, 32*1024)
	var done int64
	width := 40
	lastPct := -1

	for {
		n, readErr := remoteFile.Read(buf)
		if n > 0 {
			if _, err := localFile.Write(buf[:n]); err != nil {
				return err
			}
			done += int64(n)
			pct := int(float64(done) / float64(totalSize) * 100)
			if pct != lastPct {
				filled := int(float64(width) * float64(done) / float64(totalSize))
				bar := strings.Repeat("█", filled) + strings.Repeat("░", width-filled)
				fmt.Printf("\r    [%s] %5.1f%%  %d/%dMB", bar,
					float64(done)*100/float64(totalSize),
					done/1024/1024, totalSize/1024/1024)
				lastPct = pct
			}
		}
		if readErr == io.EOF {
			break
		}
		if readErr != nil {
			return readErr
		}
	}
	fmt.Println()
	return nil
}

// ── 交互工具 ──────────────────────────────────────────
func readLine(prompt string) string {
	fmt.Print(prompt)
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Scan()
	return strings.TrimSpace(scanner.Text())
}

func choose(prompt string, options []string) int {
	for i, o := range options {
		fmt.Printf("  %d. %s\n", i+1, o)
	}
	for {
		s := readLine(prompt + ": ")
		var idx int
		if _, err := fmt.Sscanf(s, "%d", &idx); err == nil && idx >= 1 && idx <= len(options) {
			return idx - 1
		}
		fmt.Println("  无效选择，请重试")
	}
}

// ── 主流程 ────────────────────────────────────────────
func main() {
	fmt.Println("=== 登临部署包下载工具 ===\n")

	user := readLine(fmt.Sprintf("用户名 [%s]: ", defaultUser))
	if user == "" {
		user = defaultUser
	}
	pass := readLine(fmt.Sprintf("密码 [%s]: ", defaultPass))
	if pass == "" {
		pass = defaultPass
	}

	fmt.Println("连接中...")
	sshClient, sftpClient, err := connect(user, pass)
	if err != nil {
		fmt.Fprintf(os.Stderr, "连接失败: %v\n", err)
		os.Exit(1)
	}
	defer sshClient.Close()
	defer sftpClient.Close()
	fmt.Println("已连接！\n")

	// 版本
	versions := listVersions(sftpClient)
	if len(versions) == 0 {
		fmt.Println("没有可用版本")
		return
	}
	fmt.Println("可用版本：")
	version := versions[choose("选择版本", versions)]

	// 架构
	fmt.Println("\n架构：")
	arch := []string{"x86", "arm64"}[choose("选择架构", []string{"x86", "arm64"})]

	// 系统
	fmt.Println("\n操作系统：")
	osName := []string{"linux", "windows", "centos"}[
		choose("选择系统", []string{"linux", "windows", "centos"})]

	// 类别
	var avail []string
	var availLabels []string
	for _, k := range []string{"driver", "sdk", "cuda11", "sdk_image", "pytorch_image", "container", "vllm_image", "doc"} {
		if osName == "windows" && windowsDisabled[k] {
			continue
		}
		avail = append(avail, k)
		availLabels = append(availLabels, categories[k].label+" ("+k+")")
	}
	fmt.Println("\n下载类别：")
	for i, l := range availLabels {
		fmt.Printf("  %d. %s\n", i+1, l)
	}
	fmt.Println("  0 = 全部")

	raw := readLine("选择类别（逗号分隔，如 1,2,3）: ")
	var cats []string
	if raw == "0" {
		cats = avail
	} else {
		for _, s := range strings.Split(raw, ",") {
			s = strings.TrimSpace(s)
			var idx int
			if _, err := fmt.Sscanf(s, "%d", &idx); err == nil && idx >= 1 && idx <= len(avail) {
				cats = append(cats, avail[idx-1])
			}
		}
	}
	if len(cats) == 0 {
		fmt.Println("未选择任何类别")
		return
	}

	// 扫描并过滤
	fmt.Println("\n扫描远程文件...")
	files := listFiles(sftpClient, version)
	matched := filterFiles(files, arch, osName, cats)

	var allFiles []string
	for _, cat := range cats {
		flist := matched[cat]
		fmt.Printf("\n[%s] 匹配 %d 个文件：\n", cat, len(flist))
		for _, f := range flist {
			fmt.Printf("    %s\n", f)
		}
		allFiles = append(allFiles, flist...)
	}

	if len(allFiles) == 0 {
		fmt.Println("\n没有匹配的文件")
		return
	}

	fmt.Printf("\n共 %d 个文件待下载\n", len(allFiles))
	saveDir := readLine(fmt.Sprintf("保存目录 [./downloads/%s]: ", version))
	if saveDir == "" {
		saveDir = "./downloads/" + version
	}

	// 下载
	for i, rpath := range allFiles {
		remote := baseDir + "/" + version + "/" + rpath
		local := filepath.Join(saveDir, filepath.Base(rpath))
		fmt.Printf("\n[%d/%d]", i+1, len(allFiles))
		if err := downloadFile(sftpClient, remote, local); err != nil {
			fmt.Fprintf(os.Stderr, "  下载失败: %v\n", err)
		}
	}

	fmt.Println("\n全部完成！")
}
