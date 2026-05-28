# Convert-Markdown

批量将 Markdown 文件转换为 PDF，支持两种导出方式。

## 功能

- 自动识别目标是单个 `.md` 文件还是文件夹
- 递归遍历目录，批量转换所有 `.md`
- 两种导出方式可选：
  - **pandoc**（默认）：Pandoc + XeLaTeX 直接转换，无需 GUI
  - **typora**：Typora GUI 自动化导出，效果与 Typora 原生一致

## 依赖

### pandoc 模式（默认）

| 依赖 | 安装方式 |
|------|----------|
| Python 3.10+ | - |
| Pandoc | https://pandoc.org/installing.html |
| TeX Live（提供 xelatex） | https://tug.org/texlive/ |

### typora 模式

| 依赖 | 安装方式 |
|------|----------|
| Python 3.10+ | - |
| Typora | https://typora.io/ |
| pyautogui | `pip install pyautogui` |

## 使用方法

```bash
# 转换单个文件（pandoc 模式）
python main.py "D:\notes\hello.md"

# 转换整个文件夹（pandoc 模式）
python main.py "D:\notes"

# 使用 Typora 原生导出
python main.py "D:\notes" --method typora
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `target` | `.md` 文件或包含 `.md` 文件的文件夹路径（必需） |
| `--method` | 导出方式：`pandoc`（默认）或 `typora` |
| `--wait-load` | Typora 加载等待秒数（仅 typora 模式，默认 3） |
| `--wait-export` | 导出完成等待秒数（仅 typora 模式，默认 3） |

### 输出

- 对每个 `xxx.md`：在同目录下生成 `xxx.pdf`

## 项目结构

```
Convert-Markdown/
├── main.py              # 入口脚本
├── pandoc_exporter.py   # PandocExporter 类（Pandoc + XeLaTeX）
├── typora_exporter.py   # TyporaExporter 类（Typora GUI 自动化）
├── assets/              # 字体文件（仓耳玄三）
└── requirements.txt
```

## 常见问题

1. **提示找不到 pandoc**：确认已安装并加入系统 PATH，终端运行 `pandoc --version` 验证
2. **xelatex 中文字体问题**：默认使用 SimSun（宋体），如需更换修改 `pandoc_exporter.py` 中的 `CJKmainfont` 参数
3. **typora 模式菜单导航失败**：Typora 版本不同菜单项位置可能不同，调整 `typora_exporter.py` 中的 `EXPORT_MENU_INDEX` 和 `PDF_SUBMENU_INDEX`

## License
