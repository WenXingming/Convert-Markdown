"""
批量将 Markdown 文件转换为 PDF。

使用示例：
    python main.py "C:\\path\\to\\folder"
    python main.py "C:\\path\\to\\file.md"
    python main.py "C:\\path\\to\\folder" --method typora

参数说明：
    target          .md 文件或包含 .md 文件的文件夹路径（自动识别）
    --method        导出方式：pandoc（默认）或 typora
    --wait-load     Typora 加载等待秒数（仅 typora 模式，默认 3）
    --wait-export   导出完成等待秒数（仅 typora 模式，默认 3）

导出方式：
    pandoc  - Pandoc + XeLaTeX 直接转换（默认，无需 GUI，需安装 Pandoc 和 TeX Live）
    typora  - Typora GUI 自动化导出（效果与 Typora 原生一致，需安装 pyautogui）
"""

import argparse
import logging

from pandoc_exporter import PandocExporter
from typora_exporter import TyporaExporter


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(message)s")
    fh = logging.FileHandler("export.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("[%(asctime)s]  %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)


def main():
    setup_logging()
    parser = argparse.ArgumentParser(
        description="批量将 Markdown 文件转换为 PDF"
    )
    parser.add_argument(
        "target",
        help=".md 文件或包含 .md 文件的文件夹路径",
    )
    parser.add_argument(
        "--method",
        choices=["pandoc", "typora"],
        default="pandoc",
        help="导出方式：pandoc（默认）或 typora",
    )
    parser.add_argument(
        "--wait-load",
        type=float,
        default=3,
        help="Typora 加载等待秒数（仅 typora 模式，默认 3）",
    )
    parser.add_argument(
        "--wait-export",
        type=float,
        default=3,
        help="导出完成等待秒数（仅 typora 模式，默认 3）",
    )

    args = parser.parse_args()

    if args.method == "typora":
        exporter = TyporaExporter(
            target=args.target,
            wait_load=args.wait_load,
            wait_export=args.wait_export,
        )
    else:
        exporter = PandocExporter(target=args.target)

    exporter.convert()


if __name__ == "__main__":
    main()
