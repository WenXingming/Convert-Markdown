import os
import subprocess
import time
from pathlib import Path

import pyautogui

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.2


class TyporaExporter:
    """通过 Typora GUI 自动化批量导出 Markdown 为 PDF，效果与 Typora 原生一致。"""

    TYPERA_EXE = r"C:\Program Files\Typora\Typora.exe"

    # 文件菜单中"导出"的位置
    EXPORT_MENU_INDEX = 16
    # "导出"子菜单中 PDF 的位置
    PDF_SUBMENU_INDEX = 0

    def __init__(self, target, wait_load=8, wait_export=12):
        self.target = Path(target)
        self.wait_load = wait_load
        self.wait_export = wait_export

    def check_prerequisites(self) -> bool:
        if not os.path.isfile(self.TYPERA_EXE):
            print(f"Typora 未安装: {self.TYPERA_EXE}")
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

    @staticmethod
    def navigate_to_pdf_export(wait=1):
        """从 File 菜单已打开的状态，导航到 导出 -> PDF。"""
        pyautogui.press("home")
        time.sleep(wait)
        for _ in range(TyporaExporter.EXPORT_MENU_INDEX):
            pyautogui.press("down")
            time.sleep(0.15)
        pyautogui.press("right")
        time.sleep(wait)
        for _ in range(TyporaExporter.PDF_SUBMENU_INDEX):
            pyautogui.press("down")
            time.sleep(0.15)
        pyautogui.press("enter")

    @staticmethod
    def kill_typora():
        subprocess.run(["taskkill", "/f", "/im", "Typora.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def convert_one_file(self, md_path: Path) -> bool:
        print(f"正在导出: {md_path.name} ...")

        try:
            subprocess.Popen([self.TYPERA_EXE, str(md_path)])
            time.sleep(self.wait_load)

            pyautogui.hotkey("alt", "f")
            time.sleep(1)

            self.navigate_to_pdf_export(wait=0.5)

            # 等待"另存为"对话框完全加载
            time.sleep(8)
            pyautogui.press("enter")
            # 仅在 PDF 已存在时，覆盖确认框才会弹出
            expected_pdf = md_path.with_suffix(".pdf")
            if expected_pdf.is_file():
                time.sleep(1)
                pyautogui.press("left")
                time.sleep(0.3)
                pyautogui.press("enter")

            # 等待导出完成
            time.sleep(self.wait_export)
            time.sleep(2)

            if expected_pdf.is_file():
                print(f"  导出成功: {expected_pdf}")
                self.kill_typora()
                time.sleep(3)
                return True
            else:
                print(f"  未找到 PDF: {expected_pdf}")
                self.kill_typora()
                time.sleep(3)
                return False

        except Exception as e:
            print(f"  导出失败: {e}")
            self.kill_typora()
            return False

    def convert(self):
        if not self.check_prerequisites():
            return

        subprocess.run(["taskkill", "/f", "/im", "Typora.exe"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)

        files = list(self.iter_markdown_files())
        print(f"找到 {len(files)} 个 Markdown 文件")
        print("开始批量导出（期间请勿操作鼠标键盘）...\n")

        success = 0
        for i, md_path in enumerate(files, 1):
            print(f"[{i}/{len(files)}]", end=" ")
            if self.convert_one_file(md_path):
                success += 1

        print(f"\n导出完成！成功 {success}/{len(files)} 个文件。")
