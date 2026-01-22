import os
import re
import subprocess
import urllib.parse
import argparse
from pathlib import Path

try:
    from PIL import Image  # type: ignore
except Exception:
    Image = None


class ConvertMD:
    def __init__(self, target_folder, css_path=None, keep_html_on_success=False):
        self.target_folder = target_folder
        self.css_path = css_path or r"assets\whitey_plus.css"  # 示例 CSS 文件路径
        self.keep_html_on_success = keep_html_on_success

        # wkhtmltopdf 参数（尽量向 Typora 导出风格靠拢）
        # 说明：Typora 基于 Chromium，而 wkhtmltopdf 基于 QtWebKit；完全一致做不到，但可以尽量接近。
        self.wkhtmltopdf_style_args = [
            "--page-size",
            "A4",
            "--margin-top",
            "15mm",
            "--margin-right",
            "15mm",
            "--margin-bottom",
            "15mm",
            "--margin-left",
            "15mm",
            "--print-media-type",
            "--disable-smart-shrinking",
            "--dpi",
            "96",
            "--zoom",
            "1.0",
        ]

        # Pandoc HTML 结构与 Typora 导出的 HTML 结构不一致：
        # - Typora 会带很多 .md-fences/.md-image 等类名；
        # - Pandoc 输出通常是 <pre><code>、<img>、div.sourceCode 等。
        # 因此补一份“兼容 Pandoc HTML”的 CSS，让图片/代码块样式更接近 Typora。
        self.compat_css_path = r"assets\typora_compat_pandoc.css"

    """ 检测是否安装 pandoc """
    def is_pandoc_installed(self):
        try:
            subprocess.run(["pandoc", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            print("Pandoc is not installed, OR not found in PATH. Please install it from https://pandoc.org/installing.html, OR ensure it's added to your system PATH.")
            return False

    """ 检测是否安装 wkhtmltopdf 引擎 """
    def is_wkhtmltopdf_installed(self):
        try:
            subprocess.run(["wkhtmltopdf", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            print("wkhtmltopdf is not installed, OR not found in PATH. Please install it from https://wkhtmltopdf.org/downloads.html, OR ensure it's added to your system PATH.")
            return False

    """ 检测 CSS 文件是否存在 """
    def is_css_file_exists(self, css_path):
        # 获取当前脚本所在目录
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
        if not self.is_wkhtmltopdf_installed():
            print("Conversion aborted due to missing wkhtmltopdf.")
            return False
        if not self.is_target_folder_exists():
            print(f"Target folder '{self.target_folder}' does not exist.")
            return False
        if not self.is_css_file_exists(self.css_path):
            print(f"Warning: CSS file '{self.css_path}' does not exist. Conversion will proceed without CSS.")
        return True

    """ 获取 CSS 文件绝对路径（允许传入绝对路径或相对脚本目录的相对路径）"""
    def get_css_abs_path(self):
        # 允许用户直接传入绝对路径
        if os.path.isabs(self.css_path):
            return self.css_path
        # 否则，按脚本所在目录解析相对路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, self.css_path)

    """ 将本地路径转换为 file:/// URL，便于 HTML/CSS 被 wkhtmltopdf 读取 """
    def to_file_uri(self, file_path: str) -> str:
        return Path(file_path).resolve().as_uri()

    """ 将 HTML 中的本地链接/图片路径重写为 file:/// URL（wkhtmltopdf 更稳定）"""
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
            # 去掉 query/fragment，并对 %xx 做反解码（常见于含空格/中文的路径）
            u = url.strip()
            try:
                parsed = urllib.parse.urlsplit(u)
                u = parsed.path
            except Exception:
                # 如果不是一个合法 URL，就按原样处理
                pass
            u = urllib.parse.unquote(u)
            return u.replace("\\", "/")

        def to_uri_if_exists(url: str) -> str:
            # 注意：should_keep 必须基于原始 URL 判断（否则 file:/// 会被当成本地路径误改）
            if should_keep(url):
                return url

            u = normalize_local_path(url)

            # 绝对 Windows 路径：C:/... 或 C:\...
            if re.match(r"^[a-zA-Z]:/", u):
                return Path(u).resolve().as_uri()

            # 相对路径：按 HTML 所在目录解析
            candidate = (base_dir / u).resolve()
            if candidate.is_file():
                return candidate.as_uri()

            # 有些 Markdown 会写成 /assets/xxx.png（类 Unix 的“根相对”写法）
            # 在 Windows 下通常并不代表真正的绝对路径，这里尝试按相对路径再解析一次。
            if u.startswith("/"):
                candidate2 = (base_dir / u.lstrip("/")).resolve()
                if candidate2.is_file():
                    return candidate2.as_uri()
            return url

        def replace_attr(match):
            prefix = match.group(1)
            quote = match.group(2)
            url = match.group(3)
            # match.group(4) 本身就是闭合引号（与 group(2) 相同），不要重复拼接，否则会得到 src="...""。
            return f"{prefix}{quote}{to_uri_if_exists(url)}{quote}"

        # src/href
        pattern = re.compile(r"(\b(?:src|href)=)(\"|')(.*?)(\2)", re.IGNORECASE)
        html = pattern.sub(replace_attr, html)

        # srcset（可能包含多个候选：url 1x, url 2x ...）
        def replace_srcset(match):
            prefix = match.group(1)
            quote = match.group(2)
            value = match.group(3)

            parts = []
            for item in value.split(","):
                item = item.strip()
                if not item:
                    continue
                # item 形如 "path 2x" 或 "path 300w"
                tokens = item.split()
                url = tokens[0]
                rest = " ".join(tokens[1:])
                new_url = to_uri_if_exists(url)
                parts.append((new_url + (" " + rest if rest else "")).strip())
            new_value = ", ".join(parts)
            return f"{prefix}{quote}{new_value}{quote}"

        srcset_pattern = re.compile(r"(\bsrcset=)(\"|')(.*?)(\2)", re.IGNORECASE)
        return srcset_pattern.sub(replace_srcset, html)

    """ 将 HTML 里的 file:///...webp 转成 png（wkhtmltopdf 对 webp 支持不稳定）"""
    def convert_webp_images_in_html(self, html: str, html_dir: Path, temp_artifacts: list[Path]):
        if Image is None:
            return html

        # 仅处理 file:///... 的本地 webp
        pattern = re.compile(r"file:///[^\"'\s>]+?\.webp", re.IGNORECASE)
        matches = list(dict.fromkeys(pattern.findall(html)))
        if not matches:
            return html

        out_dir = html_dir / ".__wkhtml_img_tmp__"
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

        # 标记输出目录，便于统一清理
        temp_artifacts.append(out_dir)
        return html

    """ 清理 Pandoc 生成的 HTML，避免 wkhtmltopdf 因 about:blank/空链接/路径解析问题而退出 """
    def sanitize_html_for_wkhtmltopdf(self, html_path: Path, temp_artifacts: list[Path] | None = None):
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError:
            return

        # 常见触发点：Markdown 里出现 []() 这类空链接，会生成 href=""，wkhtmltopdf 可能将其当作 about:blank 去加载并报错。
        html = html.replace('href=""', 'href="#"')
        html = html.replace("href=''", "href='#'")
        html = html.replace('src=""', 'src="#"')
        html = html.replace("src=''", "src='#'")

        # 另一个触发点：部分内容/模板会直接出现 about:blank（iframe、链接占位等）
        # wkhtmltopdf 会报 Protocol "about" is unknown 并直接退出
        html = html.replace("about:blank", "#")

        # 让 wkhtmltopdf 更稳定地加载本地图片/链接：统一重写为 file:/// URL
        html = self.rewrite_local_urls_to_file_uri(html, html_path.parent)

        # wkhtmltopdf 对 webp 支持因版本而异；浏览器能显示但 PDF 可能丢图。
        # 这里可选把本地 webp 转成 png 再引用。
        if temp_artifacts is not None:
            html = self.convert_webp_images_in_html(html, html_path.parent, temp_artifacts)

        # Debug：统计仍然找不到的本地图片（仅在 keep_html_on_success 打开时输出，避免刷屏）
        if self.keep_html_on_success:
            missing = []
            for m in re.finditer(r"<img\b[^>]*\bsrc=(\"|')([^\"']+)(\1)", html, re.IGNORECASE):
                src = m.group(2)
                # 只关注本地路径（非 http/https/data/file）
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

    """ 获取 CSS 的 file:/// URL（不存在则返回 None）"""
    def get_css_uri(self):
        css_abs_path = self.get_css_abs_path()
        if os.path.isfile(css_abs_path):
            return self.to_file_uri(css_abs_path)
        print(f"Warning: CSS file not found: {css_abs_path}. Will convert without CSS.")
        return None

    """ 获取兼容 Pandoc HTML 的 CSS（不存在则返回 None）"""
    def get_compat_css_uri(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        compat_abs_path = os.path.join(base_dir, self.compat_css_path)
        if os.path.isfile(compat_abs_path):
            return self.to_file_uri(compat_abs_path)
        return None

    """ 遍历目标目录下所有 Markdown 文件 """
    def iter_markdown_files(self):
        # root: 当前遍历的目录路径
        # _: 忽略子目录名列表，即 dirs，这里不需要，用 _ 表示“不关心”
        # files: 当前 root 目录下的文件名列表
        for root, _, files in os.walk(self.target_folder):
            for file in files:
                if file.endswith(".md"):
                    yield Path(root) / file  # 拼接路径, 比 os.path.join 更现代、可读性更强。返回

    """ Windows 下兜底：若输入不是 UTF-8，则转码成临时 UTF-8 Markdown，返回 Pandoc 实际输入路径 """
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

        # 尝试常见编码：utf-8-sig / gb18030
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("gb18030")

        md_tmp_path.write_text(text, encoding="utf-8", newline="\n")
        return md_tmp_path

    """ 运行外部命令（捕获输出，避免控制台编码导致崩溃）"""
    def run_command(self, cmd):
        return subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    """ 组装 Pandoc 命令：md -> html """
    def build_pandoc_cmd(self, input_md: Path, html_path: Path, title: str, css_uris):
        # 说明：
        # - --standalone：输出完整 HTML（包含 <head> 等）
        # - --metadata pagetitle=...：避免标题为空导致的某些警告
        # - --css：如果提供 CSS，则以 file:/// URL 引用，方便 wkhtmltopdf 读取本地资源
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

    """ 组装 wkhtmltopdf 命令：html -> pdf """
    def build_wkhtmltopdf_cmd(self, html_path: Path, output_pdf: Path):
        # 说明：
        # - --enable-local-file-access：允许加载本地图片/CSS/字体（Windows 下非常关键）
        # - --encoding utf-8：避免中文在部分环境下出现乱码
        # - --print-media-type：更接近 Typora/浏览器“打印”的排版
        # - --disable-smart-shrinking：避免字号/布局被自动缩放导致和 Typora 差异过大
        return [
            "wkhtmltopdf",
            "--enable-local-file-access",
            # CSS 里引用的本地字体/图片缺失时，默认会导致 wkhtmltopdf 直接失败退出
            # 这里改为忽略加载错误，让转换尽可能产出 PDF（样式缺失会在控制台警告）
            "--load-error-handling",
            "ignore",
            "--load-media-error-handling",
            "ignore",
            "--encoding",
            "utf-8",
            *self.wkhtmltopdf_style_args,
            str(html_path),
            str(output_pdf),
        ]

    """ 将异常 stderr 解码成人类可读文本 """
    def decode_stderr(self, err_bytes) -> str:
        if not err_bytes:
            return ""
        # 先尝试 UTF-8，失败则回退到 Windows 常见编码
        try:
            return err_bytes.decode("utf-8", errors="replace").strip()
        except Exception:
            try:
                return err_bytes.decode("gb18030", errors="replace").strip()
            except Exception:
                return str(err_bytes)

    """ 转换单个 Markdown 文件，成功返回 True """
    def convert_one_file(self, md_path: Path, css_uris) -> bool:
        file_name_no_ext = md_path.stem
        output_pdf = md_path.with_suffix(".pdf")

        # 生成临时文件（放在 Markdown 同目录，保证相对图片/资源路径可用）
        # html_path = md_path.with_name(file_name_no_ext + ".__pandoc_tmp__.html")
        html_path = md_path.with_name(file_name_no_ext + ".html")
        md_tmp_path = md_path.with_name(file_name_no_ext + ".__pandoc_tmp__.md")

        # Windows 下经常会遇到 Markdown 文件不是 UTF-8（例如 GBK/GB18030）
        # Pandoc 默认按 UTF-8 读取，遇到非 UTF-8 会直接报错。
        # 这里做一个温和的兜底：如果检测到不是 UTF-8，则先转码到临时 UTF-8 文件再喂给 Pandoc。
        pandoc_input = self.ensure_utf8_markdown(md_path, md_tmp_path)

        # 折中方案：
        # 1) 先用 Pandoc 把 Markdown 转为 HTML
        # 2) 再用 wkhtmltopdf 把 HTML 转为 PDF
        # 这样一般比“Pandoc 直接调用 PDF 引擎”更可控，也更接近浏览器渲染效果。
        pandoc_cmd = self.build_pandoc_cmd(pandoc_input, html_path, file_name_no_ext, css_uris)
        wkhtml_cmd = self.build_wkhtmltopdf_cmd(html_path, output_pdf)

        print(f"正在转换: {md_path.name} -> {output_pdf} ...")

        success = False
        temp_artifacts: list[Path] = []
        try:
            # 1. Markdown -> HTML
            self.run_command(pandoc_cmd)
            # wkhtmltopdf 对 about:blank 等非常敏感，先对 HTML 做一次清理
            self.sanitize_html_for_wkhtmltopdf(html_path, temp_artifacts)

            # 2. HTML -> PDF
            try:
                self.run_command(wkhtml_cmd)
                success = True
            except subprocess.CalledProcessError as wk_err:
                # 经验：wkhtmltopdf 在某些 CSS/字体场景下会失败。
                # 这里做一个兜底：失败后尝试不带 CSS 再跑一次（保证尽量产出 PDF）。
                if css_uris:
                    print("wkhtmltopdf failed with CSS; retrying once without CSS...")
                    pandoc_cmd_no_css = self.build_pandoc_cmd(pandoc_input, html_path, file_name_no_ext, [])
                    self.run_command(pandoc_cmd_no_css)
                    self.sanitize_html_for_wkhtmltopdf(html_path, temp_artifacts)
                    self.run_command(wkhtml_cmd)
                    success = True
                else:
                    raise wk_err
        except subprocess.CalledProcessError as e:
            details = self.decode_stderr(getattr(e, "stderr", b""))
            if details:
                print(f"转换失败: {md_path.name}, 错误: {e}\n{details}")
            else:
                print(f"转换失败: {md_path.name}, 错误: {e}")
        finally:
            # 仅在成功时清理临时文件；失败时保留，便于你排查（比如打开 HTML 看看哪里触发了 wkhtmltopdf 报错）
            try:
                if success:
                    if html_path.is_file():
                        if self.keep_html_on_success:
                            print(f"已保留临时 HTML（keep_html_on_success=True）: {html_path}")
                        else:
                            html_path.unlink()
                    if md_tmp_path.is_file():
                        md_tmp_path.unlink()

                    # 清理由 webp->png 转换产生的临时资源（除非用户要求保留 HTML）
                    if not self.keep_html_on_success:
                        for p in sorted(set(temp_artifacts), key=lambda x: len(str(x)), reverse=True):
                            try:
                                if p.is_file():
                                    p.unlink()
                                elif p.is_dir():
                                    # 目录只在空时删除
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

        css_uri = self.get_css_uri()
        compat_css_uri = self.get_compat_css_uri()
        css_uris = [u for u in [css_uri, compat_css_uri] if u]
        print(f"Converting markdown files in folder: {self.target_folder}")

        count = 0
        for md_path in self.iter_markdown_files():
            if self.convert_one_file(md_path, css_uris):
                count += 1

        print(f"\n处理完成！共转换了 {count} 个文件。")


if __name__ == "__main__":
    # 命令行参数：让脚本更易用、更可复现
    # 示例：
    # python .\Convert-md\convert-md.py --target-folder "D:\notes" --keep-html-on-success
    parser = argparse.ArgumentParser(description="Convert Markdown files to PDF via Pandoc->HTML->wkhtmltopdf")
    parser.add_argument(
        "--target-folder",
        required=True,
        default=r"C:\Users\28016\Documents\WPSDrive\1126954793\WPS云盘\「Repositories」\「操作系统」", # required = True，实际运行时必须提供此参数
        help="包含 Markdown 文件的目标文件夹路径",
    )
    parser.add_argument(
        "--css",
        required=False,
        default=r"assets\whitey_plus.css",
        help="CSS 文件路径（可用绝对路径或相对 Convert-md 目录）",
    )
    parser.add_argument(
        "--keep-html-on-success",
        action="store_true", # 指定此参数即为 True。不使用上面的参数，因为上面是字符串参数。
        help="转换成功也保留临时 HTML（用于排查图片/样式问题）",
    )

    args = parser.parse_args()

    converter = ConvertMD(
        target_folder=args.target_folder,
        css_path=args.css,
        keep_html_on_success=args.keep_html_on_success,
    )
    converter.convert()
