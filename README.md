# Convert-Markdown

## Introduction ✅

这个项目用于**批量将一个文件夹里的 Markdown（`.md`）转换为 PDF**。

**动机**：Typora 的导出功能很方便，但它不支持“对某个目录下的 Markdown 批量导出”，只能一个一个文件地将 Markdown 导出为 HTML、PDF，比较麻烦，所以写了这个脚本来一键批量转换。

实现思路是两步：

1. 用 **Pandoc** 将 Markdown 转成完整 HTML。
2. 用 **wkhtmltopdf** 将 HTML 渲染成 PDF（尽量贴近“浏览器/Typora 打印”的效果）。

转换完成后，PDF 会生成在**每个 `.md` 文件同目录**下，文件名保持一致（仅扩展名变为 `.pdf`）。

## Features ✨

- 递归遍历目标目录，批量转换所有 `.md`
- 自动处理 Windows 下常见的非 UTF-8 编码（例如 GB18030/GBK），避免 Pandoc 读取失败
- 为 wkhtmltopdf 做 HTML 清理与本地资源路径修正（将图片/链接改写为 `file:///`，更稳定）
- 可选保留中间 HTML 产物，便于排查“图片丢失 / 样式不生效”等问题
- 内置两份 CSS：默认主题 + Pandoc HTML 结构兼容层，使输出更接近 Typora 观感

## Prerequisites 🛠

必须依赖：

- Operating System: Windows 10/11（其他系统理论可行，但未测试）
- Python 3.10+
- 已安装并加入 PATH：
  - Pandoc: https://pandoc.org/installing.html
  - wkhtmltopdf: https://wkhtmltopdf.org/downloads.html

可选依赖：

- Pillow（仅在你需要将 HTML 中引用的本地 `.webp` 图片自动转成 `.png` 时才需要；未安装也能运行，只是不会做 webp 转换）

## Installation 🚀

1. **Clone the repository**

	```bash
	git clone https://github.com/WenXingming/Convert-Markdown.git
	cd Convert-Markdown
	```

2. **(Optional) Create a virtual environment**

	```bash
	# conda create -n convert_markdown python=3.10
	# conda activate convert_markdown
	```

3. **Install Python dependencies (optional)**

	如果你希望自动处理 webp 图片：

	```bash
	# conda activate convert_markdown
	pip install Pillow
	```

## Usage 📄

脚本入口是 [main.py](main.py)，使用示例命令：

```bash
python main.py --target-folder ${Your Folder} --keep-html-on-success
```

参数说明：

- `--target-folder`（必需）：包含 Markdown 文件的目标文件夹路径（脚本会遍历）
- `--css`（可选）：CSS 文件路径（默认使用 `assets\\whitey_plus.css`；可传绝对路径或相对本项目目录的相对路径）
- `--keep-html-on-success`（可选 flag）：转换成功后也保留中间 HTML（用于排查样式/资源问题）

Output：

- 对每个 `xxx.md`：生成 `xxx.pdf`
- 中间文件：默认会清理 `xxx.html`；若指定 `--keep-html-on-success` 则会保留 html 文件

## Problems & Solutions ❓

1. 提示找不到 pandoc / wkhtmltopdf

	- 确认安装了 pandoc / wkhtmltopdf，安装后在终端运行：`pandoc --version`、`wkhtmltopdf --version` 验证。
	- 若安装了但检测不到 pandoc 或 wkhtmltopdf，通常是系统 PATH 环境变量未配置（或者重启终端）

2. PDF 没有图片 / 图片路径含中文或空格

	- 先加上 `--keep-html-on-success`，打开同目录下生成的 `.html` 看图片是否能加载
	- 本项目会尽量把图片/链接改写为 `file:///`，但极端路径仍建议把资源放在 Markdown 同目录或相对路径可达的位置

3. wkhtmltopdf 报错退出

	- 脚本内已做了一些兜底（例如忽略资源加载错误；CSS 导致失败时会尝试不带 CSS 重试一次）
	- 仍失败的话，保留 HTML 并查看错误输出最有效

## License 📜

