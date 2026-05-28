import os
import subprocess
from pathlib import Path


class PandocExporter:
    """Pandoc + XeLaTeX 直接将 Markdown 转换为 PDF，无需中间 HTML。"""

    def __init__(self, target):
        self.target = Path(target)

    def is_pandoc_installed(self):
        try:
            subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            print("Pandoc is not installed. Please install it from https://pandoc.org/installing.html")
            return False

    def check_prerequisites(self) -> bool:
        if not self.is_pandoc_installed():
            return False
        if self.target.is_file() and self.target.suffix == ".md":
            return True
        if self.target.is_dir():
            return True
        print(f"目标不存在或不是 .md 文件/文件夹: {self.target}")
        return False

    def iter_markdown_files(self):
        if self.target.is_file():
            yield self.target
        else:
            for root, _, files in os.walk(self.target):
                for file in files:
                    if file.endswith(".md"):
                        yield Path(root) / file

    def convert_one_file(self, md_path: Path) -> bool:
        output_pdf = md_path.with_suffix(".pdf")
        print(f"正在转换: {md_path.name} -> {output_pdf.name} ...")

        cmd = [
            "pandoc",
            str(md_path),
            "-o", str(output_pdf),
            "--pdf-engine=xelatex",
            "--wrap=none",
            "-V", "CJKmainfont=SimSun",
            "-V", "fontsize=12pt",
            "-V", "geometry:margin=2.5cm",
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("  转换成功")
            return True
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else ""
            print(f"  转换失败: {stderr[:200]}" if stderr else f"  转换失败: {e}")
            return False

    def convert(self):
        if not self.check_prerequisites():
            return

        print(f"转换目标: {self.target}")

        count = 0
        for md_path in self.iter_markdown_files():
            if self.convert_one_file(md_path):
                count += 1

        print(f"\n处理完成！共转换了 {count} 个文件。")
