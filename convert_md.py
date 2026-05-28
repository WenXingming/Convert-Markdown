import os
import subprocess
from pathlib import Path


class ConvertMD:
    def __init__(self, target_folder):
        self.target_folder = target_folder

    """ 检测是否安装 pandoc """
    def is_pandoc_installed(self):
        try:
            subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            print("Pandoc is not installed. Please install it from https://pandoc.org/installing.html")
            return False

    """ 检测输入文件夹是否存在 """
    def is_target_folder_exists(self):
        return os.path.isdir(self.target_folder)

    """ 前置检查 """
    def check_prerequisites(self) -> bool:
        if not self.is_pandoc_installed():
            return False
        if not self.is_target_folder_exists():
            print(f"Target folder '{self.target_folder}' does not exist.")
            return False
        return True

    """ 遍历目标目录下所有 Markdown 文件 """
    def iter_markdown_files(self):
        for root, _, files in os.walk(self.target_folder):
            for file in files:
                if file.endswith(".md"):
                    yield Path(root) / file

    """ 转换单个 Markdown 文件，成功返回 True """
    def convert_one_file(self, md_path: Path) -> bool:
        output_pdf = md_path.with_suffix(".pdf")
        print(f"正在转换: {md_path.name} -> {output_pdf.name} ...")

        cmd = [
            "pandoc",
            str(md_path),
            "-o", str(output_pdf),
            "--pdf-engine=xelatex",
            "-V", "CJKmainfont=SimSun",
            "-V", "geometry:margin=2.5cm",
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"  转换成功")
            return True
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else ""
            if stderr:
                print(f"  转换失败: {stderr[:200]}")
            else:
                print(f"  转换失败: {e}")
            return False

    """ 执行转换 """
    def convert(self):
        if not self.check_prerequisites():
            return

        print(f"Converting markdown files in: {self.target_folder}")

        count = 0
        for md_path in self.iter_markdown_files():
            if self.convert_one_file(md_path):
                count += 1

        print(f"\n处理完成！共转换了 {count} 个文件。")
