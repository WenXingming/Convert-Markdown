import logging
import os
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)


class PandocExporter:
    """Pandoc + XeLaTeX 直接将 Markdown 转换为 PDF，无需中间 HTML。"""

    def __init__(self, target):
        self.target = Path(target)

    def is_pandoc_installed(self):
        try:
            subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            log.error("[FAIL] Pandoc 未安装，请从 https://pandoc.org/installing.html 安装")
            return False

    def check_prerequisites(self) -> bool:
        if not self.is_pandoc_installed():
            return False
        if self.target.is_file() and self.target.suffix == ".md":
            return True
        if self.target.is_dir():
            return True
        log.error("[FAIL] 目标不存在或不是 .md 文件/文件夹: %s", self.target)
        return False

    def iter_markdown_files(self):
        if self.target.is_file():
            yield self.target
        else:
            # 递归遍历所有子目录
            # for root, _, files in os.walk(self.target):
            #     for file in files:
            #         if file.endswith(".md"):
            #             yield Path(root) / file
            for file in self.target.iterdir():
                if file.suffix == ".md":
                    yield file

    def convert_one_file(self, md_path: Path) -> bool:
        output_pdf = md_path.with_suffix(".pdf")
        log.info("[>>] 正在转换: %s", md_path.name)

        cmd = [
            "pandoc",
            str(md_path),
            "-o", str(output_pdf),
            "--resource-path", str(md_path.parent),
            "--pdf-engine=xelatex",
            "--wrap=none",
            "-V", "CJKmainfont=SimSun",
            "-V", "fontsize=12pt",
            "-V", "geometry:margin=2.5cm",
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            log.info("[OK]  转换成功: %s", output_pdf)
            return True
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace").strip() if e.stderr else ""
            log.error("[FAIL] 转换失败: %s", stderr[:200] if stderr else str(e))
            return False

    def convert(self):
        if not self.check_prerequisites():
            return

        files = list(self.iter_markdown_files())
        log.info("=" * 100)
        log.info("目标: %s", self.target)
        log.info("找到 %d 个 Markdown 文件", len(files))
        log.info("=" * 100)
        
        log.info("")

        success = 0
        for i, md_path in enumerate(files, 1):
            log.info("[%d/%d]", i, len(files))
            if self.convert_one_file(md_path):
                success += 1
            log.info("")

        log.info("=" * 100)
        log.info("转换完成: %d/%d 个文件成功转换", success, len(files))
        log.info("=" * 100)
