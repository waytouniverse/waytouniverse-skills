#!/usr/bin/env python3
"""调用 APIMart gpt-image-2 API 生成图片，支持文生图和图生图。"""

import base64
import json
import os
import subprocess
import sys
import tempfile
import time

API_BASE = "https://api.apimart.ai/v1"
API_KEY = os.environ.get("APIMART_API_KEY", "")  # 填入 APIMart 平台的 API Key
PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "http://127.0.0.1:7890"

VALID_SIZES = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9", "9:21", "1:3", "3:1", "4:5", "5:4"]
VALID_RESOLUTIONS = ["1k", "2k", "4k"]
POLL_INTERVAL = 5
MAX_POLL = 60
MAX_RETRY = 3

STYLE_HINTS = [
    # 中文风格词
    "水彩", "油画", "素描", "国画", "水墨", "漫画", "插画", "写实", "抽象", "极简",
    "赛博朋克", "像素风", "扁平化", "3D", "卡通风", "动漫风", "复古", "怀旧",
    "波普", "哥特", "蒸汽朋克", "赛博", "浮世绘", "工笔画", "写意", "留白",
    "工笔", "版画", "速写", "涂鸦", "霓虹", "低多边形", "LowPoly", "赛璐璐",
    "印象派", "超现实", "立体派", "野兽派", "洛可可", "巴洛克", "极简主义",
    "包豪斯", "装饰艺术", "ArtDeco", "新艺术", "蒙德里安", "达达主义",
    "吉卜力", "宫崎骏", "新海诚", "日系", "日漫", "美漫", "韩系",
    "写实风", "照片级", "超写实", "电影感", "电影级", "胶片感",
    "手绘风", "铅笔画", "马克笔", "彩铅", "蜡笔", "粉彩", "水粉",
    "剪影", "光影", "逆光", "侧光", "柔光", "强光", "明暗",
    "暖色调", "冷色调", "高饱和", "低饱和", "黑白", "单色",
    "风格", "画风", "特效", "渲染", "质感", "纹理",
    # 英文风格词
    "watercolor", "oil painting", "sketch", "realistic", "abstract", "minimalist",
    "cyberpunk", "pixel art", "flat", "cartoon", "anime", "vintage", "retro",
    "pop art", "gothic", "steampunk", "impressionist", "surreal", "low poly",
    "ghibli", "cel shading", "cinematic", "photorealistic", "hand-drawn",
    "ink wash", "ukiyo-e", "art nouveau", "art deco", "bauhaus",
    "style", "aesthetic", "render", "mood", "vibe", "tone",
    "neon", "glitch", "vaporwave", "lofi", "noir",
]


def _has_style_hint(prompt: str) -> bool:
    """检查提示词是否包含风格/画风相关描述。"""
    lower = prompt.lower()
    return any(hint.lower() in lower for hint in STYLE_HINTS)


def _infer_style(prompt: str) -> str | None:
    """通过 GPT-5.5 推断适合的图片风格，返回增强后的提示词。"""
    system_msg = (
        "你是一位专业的艺术风格顾问。用户会给你一段图片描述，请你根据描述内容，"
        "判断最适合的视觉风格、艺术表现手法和氛围，然后用一段简洁的英文风格提示词来补充。"
        "只输出风格提示词（英文），不要解释，不要输出其他内容。"
        "格式示例：cinematic lighting, watercolor style, warm tones, soft edges, dreamy atmosphere"
    )
    body = {
        "model": "gpt-5.5",
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": system_msg}]},
            {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
        ],
    }

    print("未检测到风格提示，正在通过 GPT-5.5 推断适合的风格...")
    result = _curl_request(f"{API_BASE}/responses", data=body, method="POST")
    if result is None:
        print("风格推断请求失败，将使用原始提示词", file=sys.stderr)
        return None

    if result.get("code") != 200:
        print(f"风格推断失败: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        return None

    choices = result.get("data", {}).get("choices", [])
    if not choices:
        print("风格推断返回为空，将使用原始提示词", file=sys.stderr)
        return None

    style_hint = choices[0].get("message", {}).get("content", "").strip()
    if not style_hint:
        return None

    print(f"推断风格: {style_hint}")
    return style_hint


def _curl_request(url: str, data: dict = None, method: str = "GET", retry: int = MAX_RETRY) -> dict | None:
    """通过 curl 发送 HTTP 请求，失败自动重试。大数据写入临时文件避免命令行长度限制。"""
    tmp_path = None
    if data:
        payload = json.dumps(data, ensure_ascii=False)
        tmp_path = os.path.join(tempfile.gettempdir(), f"curl_data_{int(time.time()*1000)}.json")
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(payload)
    try:
        for attempt in range(retry):
            cmd = [
                "curl", "-s",
                "--connect-timeout", "15",
                "--max-time", "120",
                "-x", PROXY,
                "-H", f"Authorization: Bearer {API_KEY}",
                "-H", "Content-Type: application/json",
                "-X", method,
            ]
            if tmp_path:
                cmd.extend(["-d", f"@{tmp_path}"])
            cmd.append(url)

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
            except subprocess.TimeoutExpired:
                if attempt < retry - 1:
                    print(f"请求超时，第 {attempt + 1}/{retry} 次重试...", file=sys.stderr)
                    time.sleep(2)
                    continue
                return None

            if result.returncode != 0:
                if attempt < retry - 1:
                    print(f"请求失败 (exit {result.returncode})，第 {attempt + 1}/{retry} 次重试...", file=sys.stderr)
                    time.sleep(2)
                    continue
                return None

            if not result.stdout.strip():
                if attempt < retry - 1:
                    print(f"响应为空，第 {attempt + 1}/{retry} 次重试...", file=sys.stderr)
                    time.sleep(2)
                    continue
                return None

            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                if attempt < retry - 1:
                    print(f"响应解析失败，第 {attempt + 1}/{retry} 次重试...", file=sys.stderr)
                    time.sleep(2)
                    continue
                print(f"响应解析失败: {result.stdout[:500]}", file=sys.stderr)
                return None

        return None
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _curl_download(url: str, filepath: str) -> bool:
    """通过 curl 下载文件，失败自动重试。"""
    for attempt in range(MAX_RETRY):
        cmd = [
            "curl", "-s", "-o", filepath,
            "--connect-timeout", "15",
            "--max-time", "120",
            "-x", PROXY,
            url,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=150)
            if result.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return True
        except subprocess.TimeoutExpired:
            pass
        if attempt < MAX_RETRY - 1:
            print(f"下载失败，第 {attempt + 1}/{MAX_RETRY} 次重试...", file=sys.stderr)
            time.sleep(2)
    return False


def generate(
    prompt: str,
    size: str = "1:1",
    resolution: str = "1k",
    reference_images: list[str] | None = None,
    output_dir: str = ".",
) -> None:
    """提交生图任务并轮询结果，下载图片到本地。"""
    if size not in VALID_SIZES:
        print(f"无效尺寸 {size}，可选: {', '.join(VALID_SIZES)}", file=sys.stderr)
        sys.exit(1)
    if resolution not in VALID_RESOLUTIONS:
        print(f"无效分辨率 {resolution}，可选: {', '.join(VALID_RESOLUTIONS)}", file=sys.stderr)
        sys.exit(1)

    # 检测是否包含风格提示，若无则通过 GPT-5.5 推断
    if not _has_style_hint(prompt):
        style_hint = _infer_style(prompt)
        if style_hint:
            prompt = f"{prompt}, {style_hint}"
            print(f"增强后的提示词: \"{prompt}\"")

    body = {
        "model": "gpt-image-2",
        "prompt": prompt,
        "n": 1,
        "size": size,
        "resolution": resolution,
    }

    if reference_images:
        refs = []
        for img in reference_images:
            if os.path.isfile(img):
                ext = os.path.splitext(img)[1].lower().lstrip(".")
                mime_map = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp"}
                mime = f"image/{mime_map.get(ext, 'png')}"
                with open(img, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                refs.append(f"data:{mime};base64,{b64}")
            elif img.startswith("http"):
                refs.append(img)
            else:
                refs.append(img)
        body["reference_images"] = refs

    print(f'提交生图任务: "{prompt}"')
    print(f"尺寸: {size} | 分辨率: {resolution}")

    result = _curl_request(f"{API_BASE}/images/generations", data=body, method="POST")
    if result is None:
        print("提交任务失败，请检查网络连接", file=sys.stderr)
        sys.exit(1)

    if result.get("code") != 200:
        print(f"提交失败: {json.dumps(result, ensure_ascii=False)}", file=sys.stderr)
        sys.exit(1)

    task_data = result["data"][0] if isinstance(result["data"], list) else result["data"]
    task_id = task_data["task_id"]
    print(f"任务已提交，task_id: {task_id}，等待生成...")

    # 轮询任务状态
    poll_errors = 0
    for i in range(MAX_POLL):
        time.sleep(POLL_INTERVAL)
        task_result = _curl_request(f"{API_BASE}/tasks/{task_id}", retry=2)

        if task_result is None:
            poll_errors += 1
            if poll_errors >= 5:
                print("轮询连续失败次数过多，请检查网络", file=sys.stderr)
                sys.exit(1)
            print(f"轮询请求失败，跳过本轮 (连续失败 {poll_errors}/5)", file=sys.stderr)
            continue

        poll_errors = 0  # 成功时重置计数
        task_status = task_result.get("data", {}).get("status", "")

        if task_status in ("completed", "succeeded"):
            break
        elif task_status == "failed":
            print(f"任务失败: {json.dumps(task_result, ensure_ascii=False)}", file=sys.stderr)
            sys.exit(1)
        elif i % 3 == 0:
            progress = task_result.get("data", {}).get("progress", "?")
            print(f"生成中... 进度: {progress}%")
    else:
        print("轮询超时，任务未完成", file=sys.stderr)
        sys.exit(1)

    # 提取图片 URL 并下载
    images = task_result.get("data", {}).get("result", {}).get("images", [])
    if not images:
        print("未返回图片", file=sys.stderr)
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    saved = []

    for idx, img_info in enumerate(images):
        urls = img_info.get("url", [])
        for url in urls:
            if url.startswith("data:"):
                _, b64data = url.split(",", 1)
                img_bytes = base64.b64decode(b64data)
                filename = f"gpt_image_{int(time.time())}_{idx}.png"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                saved.append(filepath)
            else:
                filename = f"gpt_image_{int(time.time())}_{idx}.png"
                filepath = os.path.join(output_dir, filename)
                if _curl_download(url, filepath):
                    saved.append(filepath)
                else:
                    print(f"下载图片失败: {url}", file=sys.stderr)

    cost = task_result.get("data", {}).get("cost", 0)
    print(f"\n生成完成！花费: ${cost}")
    for p in saved:
        print(f"已保存: {p}")


def main():
    if len(sys.argv) < 2:
        print("用法: python generate.py <提示词> [尺寸] [分辨率] [输出目录] [参考图1] [参考图2] ...")
        print(f"  尺寸: {', '.join(VALID_SIZES)} (默认 1:1)")
        print(f"  分辨率: {', '.join(VALID_RESOLUTIONS)} (默认 1k)")
        print("  输出目录: 默认当前目录")
        print("  参考图: 可选，支持文件路径或 URL，最多 16 张")
        print()
        print("示例:")
        print('  python generate.py "一只可爱的橘猫" 1:1 1k')
        print('  python generate.py "赛博朋克城市" 16:9 2k ./output')
        print('  python generate.py "把猫变成赛博风格" 1:1 1k . ref.jpg')
        sys.exit(1)

    raw = sys.argv[1]
    # 支持从文件读取提示词：以 @ 开头的参数视为文件路径
    if raw.startswith("@") and os.path.isfile(raw[1:]):
        with open(raw[1:], "r", encoding="utf-8") as f:
            prompt = f.read().strip()
        print(f"从文件读取提示词: {raw[1:]}")
    else:
        prompt = raw
    size = sys.argv[2] if len(sys.argv) > 2 else "1:1"
    resolution = sys.argv[3] if len(sys.argv) > 3 else "1k"
    output_dir = sys.argv[4] if len(sys.argv) > 4 else "."
    ref_images = sys.argv[5:] if len(sys.argv) > 5 else None

    generate(prompt, size, resolution, ref_images, output_dir)


if __name__ == "__main__":
    main()
