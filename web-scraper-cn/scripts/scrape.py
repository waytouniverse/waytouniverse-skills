#!/usr/bin/env python3
"""
国内网站内容抓取脚本
用于抓取SPA单页应用的内容

用法:
    python scrape.py <URL> [--wait <秒数>] [--output <文件路径>]

示例:
    python scrape.py "https://zsai.zszwfw.cn/subsidiesDetail?id=17"
    python scrape.py "https://zsai.zszwfw.cn/subsidiesDetail?id=17" --wait 5 --output result.txt
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from playwright.async_api import async_playwright


def find_chrome():
    """查找系统中已安装的Chrome浏览器"""
    possible_paths = [
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        # Linux
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        # Windows (通过WSL或Git Bash)
        "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe",
        "/mnt/c/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


async def scrape_page(url: str, wait_seconds: int = 3, output_file: str = None):
    """
    抓取网页内容

    Args:
        url: 要抓取的URL
        wait_seconds: 等待页面加载的秒数
        output_file: 输出文件路径（可选）

    Returns:
        包含页面信息的字典
    """
    chrome_path = find_chrome()

    if not chrome_path:
        print("错误: 未找到Chrome浏览器。请确保Chrome已安装。", file=sys.stderr)
        print("支持的系统:", file=sys.stderr)
        print("  - macOS: Google Chrome.app 或 Chromium.app", file=sys.stderr)
        print("  - Linux: google-chrome 或 chromium-browser", file=sys.stderr)
        sys.exit(1)

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=True,
            executable_path=chrome_path
        )

        try:
            # 创建页面
            page = await browser.new_page()

            # 设置默认超时
            page.set_default_timeout(30000)

            # 访问页面并等待加载
            print(f"正在访问: {url}", file=sys.stderr)
            await page.goto(url, wait_until="networkidle")

            # 额外等待，让JavaScript渲染完成
            print(f"等待页面渲染 ({wait_seconds}秒)...", file=sys.stderr)
            await page.wait_for_timeout(wait_seconds * 1000)

            # 获取页面信息
            title = await page.title()
            final_url = page.url

            # 获取页面内容（innerText比textContent更友好）
            content = await page.evaluate("() => document.body.innerText")

            # 获取HTML（可选）
            html = await page.content()

            # 关闭浏览器
            await browser.close()

            result = {
                "url": final_url,
                "title": title,
                "content": content,
                "html": html
            }

            # 输出到文件或控制台
            output_text = f"""=== 页面抓取结果 ===

URL: {final_url}
标题: {title}

=== 页面内容 ===
{content}
"""

            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(output_text)
                print(f"内容已保存到: {output_file}", file=sys.stderr)
            else:
                print(output_text)

            return result

        except Exception as e:
            await browser.close()
            print(f"抓取失败: {str(e)}", file=sys.stderr)
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="抓取国内网站（SPA）内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scrape.py "https://example.com"
  python scrape.py "https://example.com" --wait 5
  python scrape.py "https://example.com" --output result.txt
        """
    )

    parser.add_argument(
        "url",
        help="要抓取的网页URL"
    )

    parser.add_argument(
        "--wait",
        type=int,
        default=3,
        help="等待页面渲染的秒数（默认3秒）"
    )

    parser.add_argument(
        "--output",
        "-o",
        help="输出文件路径（默认输出到控制台）"
    )

    args = parser.parse_args()

    # 运行异步任务
    try:
        result = asyncio.run(scrape_page(args.url, args.wait, args.output))
        return 0
    except KeyboardInterrupt:
        print("\n操作已取消", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\n错误: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
