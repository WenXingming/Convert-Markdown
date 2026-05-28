"""
Typora GUI 自动化批量导出 PDF。

原理：逐个用 Typora 打开 .md 文件，通过键盘快捷键触发 文件 -> 导出 -> PDF，
等待导出完成后关闭 Typora，处理下一个文件。

使用方法：
    python typora_batch_export.py --target-folder "你的Markdown文件夹"

注意事项：
    1. 运行期间不要动鼠标键盘，脚本通过模拟按键控制 Typora
    2. 请先在 Typora 中手动导出一次 PDF，确认导出设置（主题、页边距等）
    3. PDF 会保存到与 .md 文件相同的目录
    4. Typora 是 Electron 应用，菜单用方向键导航，不支持字母快捷键
"""

import argparse
import os
import subprocess
import time
from pathlib import Path

import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

TYPERA_EXE = r"C:\Program Files\Typora\Typora.exe"

# Typora 文件菜单中"导出"的位置（从 0 开始数，分隔线也算一项）
# 典型顺序：新建窗口(0), 打开文件(1), 最近打开(2), ──(3),
#           保存(4), 另存为(5), ──(6), 导出(7)
EXPORT_MENU_INDEX = 7

# "导出"子菜单中 PDF 的位置
# 典型顺序：Word(0), PDF(1), HTML(2), ...
PDF_SUBMENU_INDEX = 1


def iter_markdown_files(target_folder: str):
    for root, _, files in os.walk(target_folder):
        for f in files:
            if f.endswith(".md"):
                yield Path(root) / f


def navigate_to_pdf_export(wait: float = 0.3):
    """
    从 File 菜单已打开的状态，导航到 导出 -> PDF。
    使用方向键，因为 Typora (Electron) 不响应字母加速键。
    """
    # 先按 Home 到菜单顶部
    pyautogui.press("home")
    time.sleep(wait)

    # 按 Down 到"导出"
    for _ in range(EXPORT_MENU_INDEX):
        pyautogui.press("down")
        time.sleep(0.08)

    # Right 打开子菜单
    pyautogui.press("right")
    time.sleep(wait)

    # 在子菜单中按 Down 到 PDF
    for _ in range(PDF_SUBMENU_INDEX):
        pyautogui.press("down")
        time.sleep(0.08)

    # Enter 选择 PDF
    pyautogui.press("enter")


def export_single_file(md_path: Path, wait_load: float, wait_export: float) -> bool:
    print(f"正在导出: {md_path.name} ...")

    try:
        # 1. 启动 Typora 打开文件
        subprocess.Popen([TYPERA_EXE, str(md_path)])
        time.sleep(wait_load)

        # 2. Alt+F 打开文件菜单
        pyautogui.hotkey("alt", "f")
        time.sleep(0.5)

        # 3. 方向键导航到 导出 -> PDF 并确认
        navigate_to_pdf_export(wait=0.3)

        # 4. 等待导出对话框弹出，Enter 确认保存
        time.sleep(1.5)
        pyautogui.press("enter")
        time.sleep(wait_export)

        # 5. 关闭 Typora
        pyautogui.hotkey("ctrl", "w")
        time.sleep(1)

        # 检查 PDF
        expected_pdf = md_path.with_suffix(".pdf")
        if expected_pdf.is_file():
            print(f"  导出成功: {expected_pdf}")
            return True
        else:
            print(f"  未找到 PDF: {expected_pdf}")
            return False

    except Exception as e:
        print(f"  导出失败: {e}")
        try:
            subprocess.run(["taskkill", "/f", "/im", "Typora.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        return False


def main():
    parser = argparse.ArgumentParser(
        description="使用 Typora GUI 自动化批量导出 Markdown 为 PDF"
    )
    parser.add_argument("--target-folder", required=True, help="包含 Markdown 文件的目标文件夹路径")
    parser.add_argument("--wait-load", type=float, default=3, help="Typora 加载等待秒数（默认 3）")
    parser.add_argument("--wait-export", type=float, default=3, help="导出完成等待秒数（默认 3）")

    args = parser.parse_args()

    target = Path(args.target_folder)
    if not target.is_dir():
        print(f"目标文件夹不存在: {target}")
        return

    # 先关闭已有的 Typora
    subprocess.run(["taskkill", "/f", "/im", "Typora.exe"],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    files = list(iter_markdown_files(str(target)))
    print(f"找到 {len(files)} 个 Markdown 文件")
    print(f"开始批量导出（期间请勿操作鼠标键盘）...\n")

    success = 0
    for i, md_path in enumerate(files, 1):
        print(f"[{i}/{len(files)}]", end=" ")
        if export_single_file(md_path, args.wait_load, args.wait_export):
            success += 1

    print(f"\n导出完成！成功 {success}/{len(files)} 个文件。")


if __name__ == "__main__":
    main()
