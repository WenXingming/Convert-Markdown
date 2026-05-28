"""
此为脚本入口点。使用示例：

python main.py --target-folder "你的文件夹路径"

功能：
    将指定文件夹中的所有 Markdown 文件批量转换为 PDF。
    使用 Pandoc + XeLaTeX 直接转换，无需中间 HTML，无需额外 CSS。
    需要预先安装：
        Pandoc：https://pandoc.org/installing.html
        TeX Live 或 MiKTeX（提供 xelatex）
"""

import argparse
from convert_md import ConvertMD


def argument_parser():
    parser = argparse.ArgumentParser(
        description="批量将 Markdown 文件转换为 PDF（Pandoc + XeLaTeX）"
    )
    parser.add_argument(
        "--target-folder",
        required=True,
        help="包含 Markdown 文件的目标文件夹路径",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = argument_parser()
    converter = ConvertMD(target_folder=args.target_folder)
    converter.convert()
