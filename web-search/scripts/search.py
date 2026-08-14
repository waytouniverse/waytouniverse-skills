#!/usr/bin/env python3
"""调用豆包 AI Search API 进行联网搜索，输出搜索结果和引用来源。"""

import json
import os
import sys
import urllib.request
import urllib.error

API_URL = "https://ark.cn-beijing.volces.com/api/v3/responses"
API_KEY = os.environ.get("ARK_API_KEY", "")  # 填入火山引擎豆包 API Key
MODEL = "doubao-seed-1-6-251015"


def search(query: str, role_description: str = "你是智能助手，专业解答用户问题") -> dict:
    body = {
        "model": MODEL,
        "stream": False,
        "tools": [
            {
                "type": "doubao_app",
                "feature": {
                    "ai_search": {
                        "type": "enabled",
                        "role_description": role_description,
                    },
                    "chat": {"type": "disabled"},
                    "deep_chat": {"type": "disabled"},
                    "reasoning_search": {"type": "disabled"},
                },
                "user_location": {
                    "type": "approximate",
                    "country": "中国",
                    "region": "浙江",
                    "city": "杭州",
                },
            }
        ],
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": query}],
            }
        ],
    }

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "ark-beta-doubao-app": "true",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"API 请求失败 (HTTP {e.code}): {error_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"网络错误: {e.reason}", file=sys.stderr)
        sys.exit(1)


def format_result(result: dict) -> str:
    """将 API 返回结果格式化为可读文本。"""
    output = result.get("output", [])
    if not output:
        return "未找到搜索结果。"

    parts = []
    for item in output:
        if item.get("type") != "doubao_app_call":
            continue

        blocks = item.get("blocks", [])

        # 提取搜索来源
        for block in blocks:
            if block.get("type") == "search":
                results = block.get("results", [])
                if results:
                    parts.append("## 搜索来源\n")
                    for i, r in enumerate(results, 1):
                        card = r.get("text_card", {})
                        title = card.get("title", "无标题")
                        site = card.get("sitename", "")
                        url = card.get("url", "")
                        parts.append(f"{i}. [{title}]({url}) — {site}")
                    parts.append("")

        # 提取回答文本
        for block in blocks:
            if block.get("type") == "output_text":
                text = block.get("text", "")
                if text:
                    parts.append(text)

    return "\n".join(parts) if parts else "未找到搜索结果。"


def main():
    if len(sys.argv) < 2:
        print("用法: python search.py <搜索查询> [角色描述]", file=sys.stderr)
        sys.exit(1)

    query = sys.argv[1]
    role = sys.argv[2] if len(sys.argv) > 2 else "你是智能助手，专业解答用户问题"

    result = search(query, role)
    formatted = format_result(result)
    print(formatted)


if __name__ == "__main__":
    main()
