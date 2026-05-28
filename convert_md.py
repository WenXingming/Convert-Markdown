import os
import re
import subprocess
import urllib.parse
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None


class ConvertMD:
    def __init__(self, target_folder, css_path=None, keep_html_on_success=False):
        self.target_folder = target_folder
        self.css_path = css_path or r"assets\whitey_plus.css"
        self.keep_html_on_success = keep_html_on_success

        # Playwright PDF 导出参数（向 Typora 导出风格靠拢）
        # Typora 基于 Chromium，Playwright 同样驱动 Chromium，渲染效果基本一致。
        self.pdf_options = {
            "format": "A4",
            "margin": {
                "top": "15mm",
                "right": "15mm",
                "bottom": "15mm",
                "left": "15mm",
            },
            "print_background": True,
        }

        # 兼容 Pandoc HTML 的 CSS
        self.compat_css_path = r"assets\typora_compat_pandoc.css"

    """ 检测是否安装 pandoc """
    def is_pandoc_installed(self):
        try:
            subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            print("Pandoc is not installed, OR not found in PATH. Please install it from https://pandoc.org/installing.html, OR ensure it's added to your system PATH.")
            return False

    """ 检测是否安装 playwright """
    def is_playwright_installed(self):
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
            return True
        except ImportError:
            print("playwright is not installed. Please run:\n  pip install playwright\n  playwright install chromium")
            return False

    """ 检测 CSS 文件是否存在 """
    def is_css_file_exists(self, css_path):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        css_abs_path = os.path.join(base_dir, css_path)
        return os.path.isfile(css_abs_path)

    """ 检测输入文件夹是否存在 """
    def is_target_folder_exists(self):
        return os.path.isdir(self.target_folder)

    """ 前置检查（工具/路径）"""
    def check_prerequisites(self) -> bool:
        if not self.is_pandoc_installed():
            print("Conversion aborted due to missing pandoc.")
            return False
        if not self.is_playwright_installed():
            print("Conversion aborted due to missing playwright.")
            return False
        if not self.is_target_folder_exists():
            print(f"Target folder '{self.target_folder}' does not exist.")
            return False
        if not self.is_css_file_exists(self.css_path):
            print(f"Warning: CSS file '{self.css_path}' does not exist. Conversion will proceed without CSS.")
        return True

    """ 获取 CSS 文件绝对路径 """
    def get_css_abs_path(self):
        if os.path.isabs(self.css_path):
            return self.css_path
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, self.css_path)

    """ 将本地路径转换为 file:/// URL """
    def to_file_uri(self, file_path: str) -> str:
        return Path(file_path).resolve().as_uri()

    """ 将 HTML 中的本地链接/图片路径重写为 file:/// URL """
    def rewrite_local_urls_to_file_uri(self, html: str, base_dir: Path) -> str:
        def should_keep(url: str) -> bool:
            u = url.strip()
            return (
                u == ""
                or u.startswith("#")
                or u.startswith("http://")
                or u.startswith("https://")
                or u.startswith("data:")
                or u.startswith("mailto:")
                or u.startswith("file://")
            )

        def normalize_local_path(url: str) -> str:
            u = url.strip()
            try:
                parsed = urllib.parse.urlsplit(u)
                u = parsed.path
            except Exception:
                pass
            u = urllib.parse.unquote(u)
            return u.replace("\\", "/")

        def to_uri_if_exists(url: str) -> str:
            if should_keep(url):
                return url

            u = normalize_local_path(url)

            if re.match(r"^[a-zA-Z]:/", u):
                return Path(u).resolve().as_uri()

            candidate = (base_dir / u).resolve()
            if candidate.is_file():
                return candidate.as_uri()

            if u.startswith("/"):
                candidate2 = (base_dir / u.lstrip("/")).resolve()
                if candidate2.is_file():
                    return candidate2.as_uri()
            return url

        def replace_attr(match):
            prefix = match.group(1)
            quote = match.group(2)
            url = match.group(3)
            return f"{prefix}{quote}{to_uri_if_exists(url)}{quote}"

        pattern = re.compile(r"(\b(?:src|href)=)(\"|')(.*?)(\2)", re.IGNORECASE)
        html = pattern.sub(replace_attr, html)

        def replace_srcset(match):
            prefix = match.group(1)
            quote = match.group(2)
            value = match.group(3)

            parts = []
            for item in value.split(","):
                item = item.strip()
                if not item:
                    continue
                tokens = item.split()
                url = tokens[0]
                rest = " ".join(tokens[1:])
                new_url = to_uri_if_exists(url)
                parts.append((new_url + (" " + rest if rest else "")).strip())
            new_value = ", ".join(parts)
            return f"{prefix}{quote}{new_value}{quote}"

        srcset_pattern = re.compile(r"(\bsrcset=)(\"|')(.*?)(\2)", re.IGNORECASE)
        return srcset_pattern.sub(replace_srcset, html)

    """ 将 HTML 里的 webp 转成 png（兼容性兜底）"""
    def convert_webp_images_in_html(self, html: str, html_dir: Path, temp_artifacts: list[Path]):
        if Image is None:
            return html

        pattern = re.compile(r"file:///[^\"'\s>]+?\.webp", re.IGNORECASE)
        matches = list(dict.fromkeys(pattern.findall(html)))
        if not matches:
            return html

        out_dir = html_dir / ".__chromium_img_tmp__"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return html

        for uri in matches:
            try:
                parsed = urllib.parse.urlsplit(uri)
                webp_path = Path(urllib.parse.unquote(parsed.path.lstrip("/")))
                if not webp_path.is_file():
                    continue

                png_name = webp_path.stem + ".png"
                png_path = out_dir / png_name
                if not png_path.is_file():
                    with Image.open(webp_path) as im:
                        im.save(png_path, format="PNG")
                temp_artifacts.append(png_path)

                html = html.replace(uri, png_path.resolve().as_uri())
            except Exception:
                continue

        temp_artifacts.append(out_dir)
        return html

    """ 清理 Pandoc 生成的 HTML """
    def sanitize_html(self, html_path: Path, temp_artifacts: list[Path] | None = None):
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError:
            return

        # 修复空链接（避免渲染异常）
        html = html.replace('href=""', 'href="#"')
        html = html.replace("href=''", "href='#'")
        html = html.replace('src=""', 'src="#"')
        html = html.replace("src=''", "src='#'")
        html = html.replace("about:blank", "#")

        # 统一重写本地路径为 file:/// URL
        html = self.rewrite_local_urls_to_file_uri(html, html_path.parent)

        if temp_artifacts is not None:
            html = self.convert_webp_images_in_html(html, html_path.parent, temp_artifacts)

        if self.keep_html_on_success:
            missing = []
            for m in re.finditer(r"<img\b[^>]*\bsrc=(\"|')([^\"']+)(\1)", html, re.IGNORECASE):
                src = m.group(2)
                if src.startswith(("http://", "https://", "data:", "file://")):
                    continue
                u = src.strip()
                try:
                    parsed = urllib.parse.urlsplit(u)
                    u = parsed.path
                except Exception:
                    pass
                u = urllib.parse.unquote(u).replace("\\", "/")
                if not u:
                    continue
                p = (html_path.parent / u).resolve()
                if not p.is_file() and u.startswith("/"):
                    p = (html_path.parent / u.lstrip("/")).resolve()
                if not p.is_file():
                    missing.append(src)

            if missing:
                print(f"Warning: {html_path.name} still has {len(missing)} missing <img src=...> after rewrite.")
                for item in missing[:10]:
                    print(f"  - {item}")

        try:
            html_path.write_text(html, encoding="utf-8", newline="\n")
        except OSError:
            return

    """ 获取 CSS 的 file:/// URL """
    def get_css_uri(self):
        css_abs_path = self.get_css_abs_path()
        if os.path.isfile(css_abs_path):
            return self.to_file_uri(css_abs_path)
        print(f"Warning: CSS file not found: {css_abs_path}. Will convert without CSS.")
        return None

    """ 获取兼容 Pandoc HTML 的 CSS """
    def get_compat_css_uri(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        compat_abs_path = os.path.join(base_dir, self.compat_css_path)
        if os.path.isfile(compat_abs_path):
            return self.to_file_uri(compat_abs_path)
        return None

    """ 遍历目标目录下所有 Markdown 文件 """
    def iter_markdown_files(self):
        for root, _, files in os.walk(self.target_folder):
            for file in files:
                if file.endswith(".md"):
                    yield Path(root) / file

    """ Windows 下兜底：若输入不是 UTF-8，则转码成临时 UTF-8 Markdown """
    def ensure_utf8_markdown(self, input_path: Path, md_tmp_path: Path) -> Path:
        try:
            raw = input_path.read_bytes()
        except OSError:
            return input_path

        try:
            raw.decode("utf-8")
            return input_path
        except UnicodeDecodeError:
            pass

        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("gb18030")

        md_tmp_path.write_text(text, encoding="utf-8", newline="\n")
        return md_tmp_path

    """ 运行外部命令 """
    def run_command(self, cmd):
        return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    """ 组装 Pandoc 命令：md -> html """
    def build_pandoc_cmd(self, input_md: Path, html_path: Path, title: str, css_uris):
        cmd = [
            "pandoc",
            str(input_md),
            "-o",
            str(html_path),
            "--standalone",
            "--metadata",
            "pagetitle=" + title,
        ]
        for uri in (css_uris or []):
            if uri:
                cmd.append(f"--css={uri}")
        return cmd

    """ 用 Playwright/Chromium 将 HTML 转为 PDF """
    def html_to_pdf_playwright(self, html_path: Path, output_pdf: Path, browser):
        from playwright.sync_api import sync_playwright  # noqa: F811

        page = browser.new_page()
        try:
            file_uri = html_path.resolve().as_uri()
            page.goto(file_uri, wait_until="networkidle")
            page.pdf(path=str(output_pdf), **self.pdf_options)
        finally:
            page.close()

    """ 将异常 stderr 解码成人类可读文本 """
    def decode_stderr(self, err_bytes) -> str:
        if not err_bytes:
            return ""
        try:
            return err_bytes.decode("utf-8", errors="replace").strip()
        except Exception:
            try:
                return err_bytes.decode("gb18030", errors="replace").strip()
            except Exception:
                return str(err_bytes)

    """ 转换单个 Markdown 文件，成功返回 True """
    def convert_one_file(self, md_path: Path, css_uris, browser) -> bool:
        file_name_no_ext = md_path.stem
        output_pdf = md_path.with_suffix(".pdf")

        html_path = md_path.with_name(file_name_no_ext + ".html")
        md_tmp_path = md_path.with_name(file_name_no_ext + ".__pandoc_tmp__.md")

        pandoc_input = self.ensure_utf8_markdown(md_path, md_tmp_path)

        pandoc_cmd = self.build_pandoc_cmd(pandoc_input, html_path, file_name_no_ext, css_uris)

        print(f"正在转换: {md_path.name} -> {output_pdf} ...")

        success = False
        temp_artifacts: list[Path] = []
        try:
            # 1. Markdown -> HTML
            self.run_command(pandoc_cmd)
            self.sanitize_html(html_path, temp_artifacts)

            # 2. HTML -> PDF (Playwright/Chromium)
            self.html_to_pdf_playwright(html_path, output_pdf, browser)
            success = True
        except subprocess.CalledProcessError as e:
            details = self.decode_stderr(getattr(e, "stderr", b""))
            if details:
                print(f"转换失败: {md_path.name}, 错误: {e}\n{details}")
            else:
                print(f"转换失败: {md_path.name}, 错误: {e}")
        except Exception as e:
            print(f"转换失败: {md_path.name}, 错误: {e}")
        finally:
            try:
                if success:
                    if html_path.is_file():
                        if self.keep_html_on_success:
                            print(f"已保留临时 HTML（keep_html_on_success=True）: {html_path}")
                        else:
                            html_path.unlink()
                    if md_tmp_path.is_file():
                        md_tmp_path.unlink()

                    if not self.keep_html_on_success:
                        for p in sorted(set(temp_artifacts), key=lambda x: len(str(x)), reverse=True):
                            try:
                                if p.is_file():
                                    p.unlink()
                                elif p.is_dir():
                                    p.rmdir()
                            except OSError:
                                pass
                else:
                    if html_path.is_file():
                        print(f"已保留临时 HTML 以便排查: {html_path}")
                    if md_tmp_path.is_file():
                        print(f"已保留临时 Markdown 以便排查: {md_tmp_path}")
            except OSError:
                pass

        return success

    """ 执行转换 """
    def convert(self):
        if not self.check_prerequisites():
            return

        from playwright.sync_api import sync_playwright

        css_uri = self.get_css_uri()
        compat_css_uri = self.get_compat_css_uri()
        css_uris = [u for u in [css_uri, compat_css_uri] if u]
        print(f"Converting markdown files in folder: {self.target_folder}")

        count = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                for md_path in self.iter_markdown_files():
                    if self.convert_one_file(md_path, css_uris, browser):
                        count += 1
            finally:
                browser.close()

        print(f"\n处理完成！共转换了 {count} 个文件。")
