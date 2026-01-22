"""
此为脚本入口点。使用示例：

python main.py --target-folder ${Your Folder} --keep-html-on-success
参数说明：
    - --target-folder：后接包含 Markdown 文件的目标文件夹路径（必需参数）
    - --css：后接 CSS 文件路径（可选参数，默认值为 assets\whitey_plus.css）
    - --keep-html-on-success：指定此参数即为 True，表示转换成功后也保留临时 HTML 文件（可选参数，默认值为 False）

功能：
    将指定文件夹中的所有 Markdown 文件转换为 PDF。
    使用 Pandoc 将 Markdown 转换为 HTML，然后使用 wkhtmltopdf 将 HTML 转换为 PDF。所以需要预先安装：
        Pandoc：https://pandoc.org/installing.html
        wkhtmltopdf：https://wkhtmltopdf.org/downloads.html
"""

import argparse
from convert_md import ConvertMD

""" 参数解析器 """
def argument_parser():
    parser = argparse.ArgumentParser(
        description="Convert Markdown files to PDF via Pandoc->HTML->wkhtmltopdf"
    )
    parser.add_argument(
        "--target-folder",
        required=True,
        action="store", # 隐式默认行为，将参数值存储在 args 对象中（类型为 string）
        default=r"C:\Users\28016\Documents\WPSDrive\1126954793\WPS云盘\「Repositories」\「操作系统」",  # required = True，实际运行时必须提供此参数
        help="包含 Markdown 文件的目标文件夹路径",
    )
    parser.add_argument(
        "--css",
        required=False,
        action="store",
        default=r"assets\whitey_plus.css",
        help="CSS 文件路径（可用绝对路径或相对 Convert-md 目录）",
    )
    parser.add_argument(
        "--keep-html-on-success",
        required=False,
        action="store_true",  # 命令行中出现此参数（--keep-html-on-success）即为 True，否则为 False。类型为 bool
        default=False,
        help="转换成功也保留临时 HTML（用于排查图片/样式问题）",
    )

    args = parser.parse_args()

    return args

if __name__ == "__main__":
    args = argument_parser()
    converter = ConvertMD(
        target_folder=args.target_folder,
        css_path=args.css,
        keep_html_on_success=args.keep_html_on_success,
    )
    converter.convert()
